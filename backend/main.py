"""
main.py
=======
FastAPI entry point for the AI Candidate Discovery System.

Run with:
    uvicorn backend.main:app --reload

All business logic lives in the existing modules.  This file is a thin
integration layer that:
  1. Exposes HTTP endpoints matching the required contract.
  2. Manages lightweight in-process state (job profile, loaded candidates,
     ranked results) so each pipeline stage can be called independently.
  3. Handles file uploads, validation errors, and propagates rich HTTP errors.

Workflow
--------
    POST /upload-job        → parse .docx → store JobProfile in app.state
    POST /upload-candidates → load JSONL/JSON → store CandidateRecords
    POST /analyze           → Feature Engineering
                              → Semantic Matching
                              → Hybrid Ranking + Explainability
                              → store ShortlistResult
    GET  /results           → return stored ShortlistResult
    GET  /candidate/{id}    → return single RankedCandidate with full features
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# sys.path fix — ensures bare imports in sibling modules resolve correctly
# whether the app is launched as:
#   uvicorn backend.main:app          (cwd = project root)
#   python backend/main.py            (cwd = project root)
# ---------------------------------------------------------------------------
import sys
import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import io
import json
import logging
import platform
import socket
import tempfile
import pickle
import time
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# FastAPI / Starlette
# ---------------------------------------------------------------------------
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Project modules  (all use bare imports; sys.path fix above makes them work)
# ---------------------------------------------------------------------------
from logger import get_logger                   # centralised logging factory
from config import (
    CANDIDATES_JSONL,
    SAMPLE_CANDIDATES_JSON,
    PROJECT_ROOT,
)
from job_models import JobProfile
from candidate_models import (
    CandidateFeatures,
    EngineConfig,
    RankedCandidate,
    ShortlistResult,
)

# Engines and loaders — imported lazily inside handlers to avoid triggering
# heavy model downloads at import time (sentence-transformers, etc.)

log = get_logger(__name__)

# ---------------------------------------------------------
# Persistent Runtime Storage
# ---------------------------------------------------------

RUNTIME_DIR = PROJECT_ROOT / "backend" / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

JOB_FILE = RUNTIME_DIR / "job.pkl"
CAND_FILE = RUNTIME_DIR / "candidates.pkl"
FEATURE_FILE = RUNTIME_DIR / "features.pkl"
RESULT_FILE = RUNTIME_DIR / "results.pkl"


def save_pickle(path, obj) -> None:
    """
    Atomically persist *obj* to *path* using pickle.

    Writes to a sibling ``.tmp`` file first, then renames to the final
    destination.  This guarantees that a process crash mid-write never
    leaves a partially-written (corrupt) pickle file behind.
    """
    tmp_path = path.with_suffix(".tmp")
    log.debug("[pickle] Writing to tmp: %s", tmp_path)
    try:
        with open(tmp_path, "wb") as f:
            pickle.dump(obj, f)
            f.flush()
            os.fsync(f.fileno())  # ensure OS buffers flushed before rename
        os.replace(tmp_path, path)  # atomic on POSIX; best-effort on Windows
        log.debug("[pickle] Saved OK: %s", path)
    except Exception as exc:
        log.error("[pickle] SAVE FAILED for %s: %s", path, exc, exc_info=True)
        # Clean up orphaned tmp file if it exists
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def load_pickle(path):
    """
    Load a pickle file from *path*.

    Returns ``None`` if the file does not exist or is corrupt.  A corrupt
    file is deleted so the next successful save can replace it cleanly.
    """
    if not path.exists():
        log.debug("[pickle] File not found (returning None): %s", path)
        return None
    log.debug("[pickle] Loading: %s", path)
    try:
        with open(path, "rb") as f:
            obj = pickle.load(f)
        log.debug("[pickle] Loaded OK: %s", path)
        return obj
    except Exception as exc:
        log.error(
            "[pickle] CORRUPT FILE — deleting %s and returning None. Error: %s",
            path, exc, exc_info=True,
        )
        try:
            path.unlink(missing_ok=True)
        except Exception as del_exc:
            log.warning("[pickle] Could not delete corrupt file %s: %s", path, del_exc)
        return None

# ===========================================================================
# Application factory
# ===========================================================================

app = FastAPI(
    title="AI Candidate Discovery System",
    description=(
        "End-to-end pipeline that parses a job description, scores a candidate "
        "pool using semantic embeddings + multi-dimensional features, and returns "
        "a ranked shortlist with human-readable explanations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS (permissive for local development; tighten for production)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-process state  (single-instance; replace with Redis/DB for scale-out)
# ---------------------------------------------------------------------------
app.state.job_profile: Optional[JobProfile] = None
app.state.candidates: List[Any] = []          # List[CandidateRecord]
app.state.features: List[CandidateFeatures] = []
app.state.shortlist: Optional[ShortlistResult] = None
app.state.engine_config: EngineConfig = EngineConfig()


# ===========================================================================
# Startup / shutdown hooks
# ===========================================================================

@app.on_event("startup")
async def _startup() -> None:
    """
    Startup hook: log a banner, ensure directories exist, and eagerly restore
    any previously-persisted pipeline state from the runtime pickle files.

    Eager restoration prevents the race condition where two concurrent
    requests both see ``app.state.job_profile = None`` and both race to
    call ``load_pickle()`` before either has stored the result.
    """
    # Ensure logs directory exists (logger.py creates it, but be defensive)
    (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("  AI Candidate Discovery System — starting up")
    log.info("  PID          : %d", os.getpid())
    log.info("  Hostname     : %s", socket.gethostname())
    log.info("  Platform     : %s", platform.platform())
    log.info("  Project root : %s", PROJECT_ROOT)
    log.info("  Runtime dir  : %s", RUNTIME_DIR)
    log.info("=" * 60)

    # ── Eagerly restore persisted state ─────────────────────────────────────
    log.info("[startup] Restoring pipeline state from disk …")

    # Job profile
    loaded_job = load_pickle(JOB_FILE)
    if loaded_job is not None:
        app.state.job_profile = loaded_job
        log.info(
            "[startup] job_profile restored: %s @ %s",
            getattr(loaded_job, 'job_title', '?'),
            getattr(loaded_job, 'company', '?'),
        )
    else:
        log.info("[startup] No job_profile on disk (clean slate)")

    # Candidates
    loaded_cands = load_pickle(CAND_FILE)
    if loaded_cands:
        app.state.candidates = loaded_cands
        log.info("[startup] candidates restored: %d records", len(loaded_cands))
    else:
        log.info("[startup] No candidates on disk (clean slate)")

    # Features
    loaded_features = load_pickle(FEATURE_FILE)
    if loaded_features:
        app.state.features = loaded_features
        log.info("[startup] features restored: %d vectors", len(loaded_features))
    else:
        log.info("[startup] No features on disk")

    # Shortlist / results
    loaded_shortlist = load_pickle(RESULT_FILE)
    if loaded_shortlist is not None:
        app.state.shortlist = loaded_shortlist
        log.info(
            "[startup] shortlist restored: %d ranked candidates",
            len(getattr(loaded_shortlist, 'ranked_candidates', [])),
        )
    else:
        log.info("[startup] No shortlist on disk")

    log.info("[startup] State restoration complete")
    log.info("=" * 60)


@app.on_event("shutdown")
async def _shutdown() -> None:
    log.info("AI Candidate Discovery System — shutting down (PID=%d)", os.getpid())


# ===========================================================================
# Pydantic request / response models (API-layer only)
# ===========================================================================

class StatusResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    job_loaded: bool
    candidates_loaded: int
    results_available: bool
    engine_version: str = "1.0.0"


class AnalyzeRequest(BaseModel):
    """Optional tuning knobs the caller can pass to /analyze."""
    weight_semantic: float = Field(default=0.35, ge=0)
    weight_technical: float = Field(default=0.30, ge=0)
    weight_experience: float = Field(default=0.15, ge=0)
    weight_behavior: float = Field(default=0.12, ge=0)
    weight_trust: float = Field(default=0.08, ge=0)
    top_k: int = Field(default=100, ge=1, le=100)
    embedding_model: str = Field(default="all-MiniLM-L6-v2")


class UploadJobResponse(BaseModel):
    status: str
    job_title: str
    company: str
    required_skills: int
    preferred_skills: int
    message: str


class UploadCandidatesResponse(BaseModel):
    status: str
    total_loaded: int
    valid_candidates: int
    invalid_candidates: int
    source: str
    message: str


# ===========================================================================
# Helper utilities
# ===========================================================================

def _require_job() -> JobProfile:
    """
    Return the current JobProfile from in-process state or, on a fresh
    restart, from the persisted pickle file.

    Raises HTTP 400 if neither source has a valid profile.
    """
    if app.state.job_profile is None:
        log.info("[_require_job] In-memory job_profile is None — attempting disk restore from %s", JOB_FILE)
        app.state.job_profile = load_pickle(JOB_FILE)
        if app.state.job_profile is not None:
            log.info(
                "[_require_job] Restored job_profile from disk: %s @ %s",
                getattr(app.state.job_profile, 'job_title', '?'),
                getattr(app.state.job_profile, 'company', '?'),
            )
        else:
            log.warning(
                "[_require_job] No job_profile found on disk (%s). "
                "Raising HTTP 400.", JOB_FILE
            )

    if app.state.job_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No job profile loaded. Call POST /upload-job first.",
        )
    return app.state.job_profile


def _require_candidates() -> List[Any]:
    """
    Return the current candidate list from in-process state or, on a fresh
    restart, from the persisted pickle file.

    Raises HTTP 400 if neither source has candidates.
    """
    if not app.state.candidates:
        log.info("[_require_candidates] In-memory candidates empty — attempting disk restore from %s", CAND_FILE)
        app.state.candidates = load_pickle(CAND_FILE) or []
        if app.state.candidates:
            log.info(
                "[_require_candidates] Restored %d candidates from disk",
                len(app.state.candidates),
            )
        else:
            log.warning(
                "[_require_candidates] No candidates found on disk (%s). "
                "Raising HTTP 400.", CAND_FILE
            )

    if not app.state.candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidates loaded. Call POST /upload-candidates first.",
        )

    return app.state.candidates


def _require_results() -> ShortlistResult:
    """
    Return the current ShortlistResult from in-process state or, on a fresh
    restart, from the persisted pickle file.

    Raises HTTP 400 if neither source has results.
    """
    if app.state.shortlist is None:
        log.info("[_require_results] In-memory shortlist is None — attempting disk restore from %s", RESULT_FILE)
        app.state.shortlist = load_pickle(RESULT_FILE)
        if app.state.shortlist is not None:
            log.info(
                "[_require_results] Restored shortlist from disk: %d candidates",
                len(getattr(app.state.shortlist, 'ranked_candidates', [])),
            )
        else:
            log.warning(
                "[_require_results] No shortlist found on disk (%s). "
                "Raising HTTP 400.", RESULT_FILE
            )

    if app.state.shortlist is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No results available. Call POST /analyze first.",
        )
    return app.state.shortlist


# ===========================================================================
# Routes
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@app.get("/", tags=["Info"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint — returns a quick-start guide as JSON.
    """
    return {
        "service": "AI Candidate Discovery System",
        "version": "1.0.0",
        "workflow": [
            "1. POST /upload-job        → upload the .docx job description",
            "2. POST /upload-candidates → upload candidates (.jsonl or .json)",
            "3. POST /analyze           → run the full pipeline",
            "4. GET  /results           → retrieve ranked shortlist",
            "5. GET  /candidate/{id}    → retrieve a single candidate's details",
        ],
        "docs": "/docs",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health() -> HealthResponse:
    """
    Liveness + readiness check.

    Reports whether each pipeline stage has data ready.
    """
    return HealthResponse(
        status="ok",
        job_loaded=app.state.job_profile is not None,
        candidates_loaded=len(app.state.candidates),
        results_available=app.state.shortlist is not None,
    )


# ---------------------------------------------------------------------------
# POST /upload-job
# ---------------------------------------------------------------------------

@app.post(
    "/upload-job",
    response_model=UploadJobResponse,
    status_code=status.HTTP_200_OK,
    tags=["Pipeline"],
)
async def upload_job(
    file: Optional[UploadFile] = File(default=None),
) -> UploadJobResponse:
    """
    Upload a job description (.docx) and parse it into a structured JobProfile.

    - If **file** is omitted, the default ``dataset/job_description.docx`` is used.
    - Accepts only ``.docx`` files.

    The parsed ``JobProfile`` is stored in memory and used by all subsequent
    pipeline steps.
    """
    from job_parser import parse_job_description  # import here to avoid heavy startup

    default_jd: Path = PROJECT_ROOT / "dataset" / "job_description.docx"

    try:
        if file is not None:
            # Validate file extension
            filename = file.filename or ""
            if not filename.lower().endswith(".docx"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Only .docx files are accepted. Got: '{filename}'",
                )

            log.info("Received JD upload: %s (%d bytes)", filename, file.size or 0)

            # Write to a temporary file that parse_job_description can read
            contents = await file.read()
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(contents)
                tmp_path = Path(tmp.name)

            try:
                profile = parse_job_description(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)

        else:
            if not default_jd.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Default JD not found at {default_jd}. "
                        "Upload a .docx file via the 'file' form field."
                    ),
                )
            log.info("Parsing default JD: %s", default_jd)
            profile = parse_job_description(default_jd)

    except HTTPException as exc:
        log.warning(
            "[upload_job] HTTPException during JD parse — re-raising. "
            "status=%s", getattr(exc, 'status_code', '?')
        )
        raise
    except Exception as exc:
        log.exception("[upload_job] Job description parsing failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse job description: {exc}",
        ) from exc

    # ── Persist and update in-process state ─────────────────────────────────
    log.info(
        "[upload_job] Storing job_profile in memory: title=%s company=%s req_skills=%d",
        profile.job_title, profile.company, profile.required_skill_count(),
    )
    app.state.job_profile = profile

    log.info("[upload_job] Persisting job_profile to disk: %s", JOB_FILE)
    save_pickle(JOB_FILE, profile)
    log.info("[upload_job] job_profile persisted OK")

    # Clear downstream state so stale results don't linger
    app.state.features = []
    app.state.shortlist = None
    log.info("[upload_job] Cleared downstream features + shortlist state")

    return UploadJobResponse(
        status="ok",
        job_title=profile.job_title,
        company=profile.company,
        required_skills=profile.required_skill_count(),
        preferred_skills=len(profile.preferred_skills),
        message=f"Job profile parsed successfully for '{profile.job_title}' at {profile.company}.",
    )


# ---------------------------------------------------------------------------
# POST /upload-candidates
# ---------------------------------------------------------------------------

@app.post(
    "/upload-candidates",
    response_model=UploadCandidatesResponse,
    status_code=status.HTTP_200_OK,
    tags=["Pipeline"],
)   
async def upload_candidates(
    file: Optional[UploadFile] = File(default=None),
    max_records: Optional[int] = Query(
        default=None,
        ge=1,
        description="Limit the number of candidates loaded (useful for testing).",
    ),
    use_sample: bool = Query(
        default=False,
        description="Load the built-in 50-candidate sample instead of uploading.",
    ),
    validate: bool = Query(
        default=True,
        description="Run JSON Schema + Pydantic validation on every record.",
    ),
) -> UploadCandidatesResponse:
    """
    Load the candidate pool.

    **Priority order:**
    1. Uploaded ``.jsonl`` or ``.json`` file (if provided).
    2. `use_sample=true`  → loads the built-in 50-candidate sample.
    3. Default            → loads ``dataset/candidates.jsonl`` (100 K records).

    Use ``max_records`` to limit the load for quick tests.
    """
    from data_loader import load_candidates, load_sample_candidates  # lazy import

    try:
        if file is not None:
            filename = file.filename or ""
            ext = Path(filename).suffix.lower()
            if ext not in (".jsonl", ".json"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Only .jsonl or .json files accepted. Got: '{filename}'",
                )

            log.info("Receiving candidate file: %s", filename)
            contents = await file.read()

            # Write to temp file and load via the existing pipeline
            with tempfile.NamedTemporaryFile(
                suffix=ext, delete=False, mode="wb"
            ) as tmp:
                tmp.write(contents)
                tmp_path = Path(tmp.name)

            try:
                if ext == ".json":
                    # Wrap JSON array as JSONL in another temp file
                    raw_list = json.loads(contents.decode("utf-8"))
                    if not isinstance(raw_list, list):
                        raise ValueError("Top-level JSON must be an array.")
                    jsonl_tmp = tempfile.NamedTemporaryFile(
                        suffix=".jsonl", delete=False, mode="w", encoding="utf-8"
                    )
                    for rec in raw_list:
                        jsonl_tmp.write(json.dumps(rec) + "\n")
                    jsonl_tmp.close()
                    load_path = Path(jsonl_tmp.name)
                else:
                    load_path = tmp_path

                result = load_candidates(
                    path=load_path,
                    validate=validate,
                    max_records=max_records,
                    show_progress=False,
                )
            finally:
                tmp_path.unlink(missing_ok=True)
                if ext == ".json":
                    Path(jsonl_tmp.name).unlink(missing_ok=True)

            source = filename

        elif use_sample:
            log.info("Loading built-in 50-candidate sample …")
            result = load_sample_candidates(validate=validate, show_progress=False)
            source = "sample_candidates.json (built-in)"

        else:
            if not CANDIDATES_JSONL.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Default candidate file not found: {CANDIDATES_JSONL}. "
                        "Upload a file or use ?use_sample=true."
                    ),
                )
            log.info(
                "Loading default candidate pool (max_records=%s) …",
                max_records or "all",
            )
            result = load_candidates(
                validate=validate,
                max_records=max_records,
                show_progress=False,
            )
            source = "candidates.jsonl (default)"

    except HTTPException as exc:
        log.warning(
            "[upload_candidates] HTTPException during candidate load — re-raising. "
            "status=%s", getattr(exc, 'status_code', '?')
        )
        raise
    except Exception as exc:
        log.exception("[upload_candidates] Candidate loading failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load candidates: {exc}",
        ) from exc

    # ── Persist and update in-process state ─────────────────────────────────
    log.info(
        "[upload_candidates] Storing %d candidates in memory (source=%s)",
        len(result.candidates), source,
    )
    app.state.candidates = result.candidates

    log.info("[upload_candidates] Persisting candidates to disk: %s", CAND_FILE)
    save_pickle(CAND_FILE, result.candidates)
    log.info("[upload_candidates] Candidates persisted OK")

    # Clear downstream state
    app.state.features = []
    app.state.shortlist = None
    log.info("[upload_candidates] Cleared downstream features + shortlist state")

    log.info(
        "[upload_candidates] Complete | valid=%d | invalid=%d | source=%s",
        result.valid_count, result.invalid_count, source,
    )

    return UploadCandidatesResponse(
        status="ok",
        total_loaded=result.total_candidates,
        valid_candidates=result.valid_count,
        invalid_candidates=result.invalid_count,
        source=source,
        message=(
            f"Loaded {result.valid_count:,} valid candidates from '{source}'. "
            f"{result.invalid_count:,} records skipped due to validation errors."
        ),
    )


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------

@app.post(
    "/analyze",
    tags=["Pipeline"],
    status_code=status.HTTP_200_OK,
)
async def analyze(body: Optional[AnalyzeRequest] = None) -> Dict[str, Any]:
    """
    Run the full scoring pipeline and store results.

    **Stages executed (in order):**
    1. Feature Engineering  — extract 50+ normalised features per candidate
    2. Semantic Matching    — sentence-transformer cosine similarity
    3. Hybrid Ranking       — weighted multi-dimension score + risk penalty
    4. Explainability       — per-dimension human-readable notes

    Returns a summary; call ``GET /results`` for the full ranked list.

    Requires both ``POST /upload-job`` and ``POST /upload-candidates`` to have
    been called first.
    """
    from feature_engine import FeatureEngine
    from semantic_engine import SemanticEngine
    from ranking_engine import RankingEngine

    # ── Prerequisites ──────────────────────────────────────────────────────
    log.info("[analyze] Checking prerequisites …")
    job = _require_job()
    candidates = _require_candidates()
    log.info(
        "[analyze] Prerequisites OK — job='%s @ %s', candidates=%d",
        job.job_title, job.company, len(candidates),
    )

    # ── Build EngineConfig from request (or defaults) ──────────────────────
    req = body or AnalyzeRequest()
    config = EngineConfig(
        weight_semantic=req.weight_semantic,
        weight_technical=req.weight_technical,
        weight_experience=req.weight_experience,
        weight_behavior=req.weight_behavior,
        weight_trust=req.weight_trust,
        top_k=req.top_k,
        embedding_model=req.embedding_model,
    )
    app.state.engine_config = config
    log.info(
        "[analyze] EngineConfig — model=%s top_k=%d weights=(sem=%.2f tech=%.2f exp=%.2f beh=%.2f tru=%.2f)",
        config.embedding_model, config.top_k,
        config.weight_semantic, config.weight_technical,
        config.weight_experience, config.weight_behavior, config.weight_trust,
    )

    pipeline_start = time.perf_counter()
    log.info("=" * 60)
    log.info("[analyze] Starting analysis pipeline")
    log.info("[analyze]   PID        : %d", os.getpid())
    log.info("[analyze]   Hostname   : %s", socket.gethostname())
    log.info("[analyze]   Candidates : %d", len(candidates))
    log.info("[analyze]   Job        : %s @ %s", job.job_title, job.company)
    log.info("[analyze]   top_k      : %d", config.top_k)
    log.info("=" * 60)

    # =========================================================================
    # Stage 1: Feature Engineering
    # =========================================================================
    log.info("[analyze] [1/3] >>> BEGIN Feature Engineering — %d candidates", len(candidates))
    t0 = time.perf_counter()
    try:
        engine = FeatureEngine(job_profile=job, config=config)
        features: List[CandidateFeatures] = engine.batch_extract(
            candidates, log_interval=500
        )
        stage1_time = time.perf_counter() - t0
        log.info(
            "[analyze] [1/3] <<< END Feature Engineering — %d vectors in %.2fs",
            len(features), stage1_time,
        )
        if not features:
            log.error(
                "[analyze] [1/3] Feature Engineering returned ZERO vectors — "
                "all %d candidates failed extraction. Raising HTTP 500.",
                len(candidates),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Feature Engineering produced no output. All candidates "
                    "failed extraction. Check the feature_engine logs."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        stage1_time = time.perf_counter() - t0
        log.exception(
            "[analyze] [1/3] Feature Engineering FAILED after %.2fs: %s",
            stage1_time, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature Engineering failed: {exc}",
        ) from exc

    # =========================================================================
    # Stage 2: Semantic Matching
    # =========================================================================
    log.info(
        "[analyze] [2/3] >>> BEGIN Semantic Matching — model=%s, %d feature vectors",
        config.embedding_model, len(features),
    )
    t0 = time.perf_counter()
    try:
        sem_engine = SemanticEngine(config=config)
        log.info("[analyze] [2/3] Loading / verifying embedding model …")
        features = sem_engine.attach_scores(features, job)
        stage2_time = time.perf_counter() - t0
        log.info(
            "[analyze] [2/3] <<< END Semantic Matching — %.2fs",
            stage2_time,
        )
    except Exception as exc:
        stage2_time = time.perf_counter() - t0
        log.exception(
            "[analyze] [2/3] Semantic Matching FAILED after %.2fs: %s",
            stage2_time, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic Matching failed: {exc}",
        ) from exc

    # =========================================================================
    # Stage 3: Hybrid Ranking + Explainability
    # =========================================================================
    log.info(
        "[analyze] [3/3] >>> BEGIN Hybrid Ranking + Explainability — %d candidates",
        len(features),
    )
    t0 = time.perf_counter()
    try:
        ranker = RankingEngine(config=config, job_profile=job)
        ranked: List[RankedCandidate] = ranker.rank(features)
        stage3_time = time.perf_counter() - t0
        log.info(
            "[analyze] [3/3] <<< END Ranking + Explainability — top-%d in %.2fs",
            len(ranked), stage3_time,
        )
    except Exception as exc:
        stage3_time = time.perf_counter() - t0
        log.exception(
            "[analyze] [3/3] Ranking FAILED after %.2fs: %s",
            stage3_time, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ranking + Explainability failed: {exc}",
        ) from exc

    total_time = time.perf_counter() - pipeline_start

    # =========================================================================
    # Persist results (outside pipeline stages — errors here are storage errors)
    # =========================================================================
    log.info("[analyze] Persisting features (%d vectors) to disk …", len(features))
    try:
        app.state.features = features
        save_pickle(FEATURE_FILE, features)
        log.info("[analyze] Features persisted OK: %s", FEATURE_FILE)
    except Exception as exc:
        # Non-fatal: features may not be accessible via /candidate/{id} but
        # the analysis result is still valid.  Log and continue.
        log.error(
            "[analyze] WARNING: Could not persist features to disk: %s. "
            "GET /candidate/{id} may not return full feature vectors.",
            exc, exc_info=True,
        )
        app.state.features = features  # still keep in-memory

    # ── Build ShortlistResult ─────────────────────────────────────────────
    log.info("[analyze] Building ShortlistResult …")
    weights = config.normalised_weights()
    shortlist = ShortlistResult(
        job_title=job.job_title,
        company=job.company,
        total_candidates_evaluated=len(candidates),
        valid_candidates=len(features),
        invalid_candidates=len(candidates) - len(features),
        top_k=len(ranked),
        ranked_candidates=ranked,
        processing_time_seconds=round(total_time, 3),
        engine_version="1.0.0",
        weights_used=weights,
    )

    log.info("[analyze] Persisting shortlist to disk …")
    try:
        app.state.shortlist = shortlist
        save_pickle(RESULT_FILE, shortlist)
        log.info("[analyze] Shortlist persisted OK: %s", RESULT_FILE)
    except Exception as exc:
        log.error(
            "[analyze] WARNING: Could not persist shortlist to disk: %s. "
            "Results are available in-memory for this instance's lifetime only.",
            exc, exc_info=True,
        )
        app.state.shortlist = shortlist  # still keep in-memory

    top_score = ranked[0].score if ranked else 0.0
    top_candidate_id = ranked[0].candidate_id if ranked else "N/A"
    log.info(
        "[analyze] Pipeline COMPLETE | total_time=%.2fs | stage1=%.2fs | "
        "stage2=%.2fs | stage3=%.2fs | ranked=%d | top_score=%.4f | top_id=%s",
        total_time, stage1_time, stage2_time, stage3_time,
        len(ranked), top_score, top_candidate_id,
    )
    log.info("=" * 60)

    return {
        "status": "ok",
        "job_title": job.job_title,
        "company": job.company,
        "total_candidates_evaluated": len(candidates),
        "valid_candidates": len(features),
        "ranked_count": len(ranked),
        "processing_time_seconds": round(total_time, 3),
        "top_candidate": {
            "rank": ranked[0].rank,
            "candidate_id": ranked[0].candidate_id,
            "name": ranked[0].name,
            "score": ranked[0].score,
            "reasoning": ranked[0].reasoning,
        } if ranked else None,
        "message": (
            f"Analysis complete. {len(ranked)} candidates ranked in "
            f"{total_time:.2f}s. Call GET /results for the full list."
        ),
    }


# ---------------------------------------------------------------------------
# GET /results
# ---------------------------------------------------------------------------

@app.get(
    "/results",
    tags=["Results"],
    status_code=status.HTTP_200_OK,
)
async def get_results(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(default=25, ge=1, le=100, description="Candidates per page."),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum final score filter."),
) -> Dict[str, Any]:
    """
    Retrieve the ranked candidate shortlist.

    Supports pagination and score filtering.  Call ``POST /analyze`` first.
    """
    shortlist = _require_results()

    # ── Score filter ──────────────────────────────────────────────────────
    all_ranked = [c for c in shortlist.ranked_candidates if c.score >= min_score]

    # ── Pagination ────────────────────────────────────────────────────────
    total = len(all_ranked)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_ranked[start:end]

    return {
        "status": "ok",
        "job_title": shortlist.job_title,
        "company": shortlist.company,
        "total_candidates_evaluated": shortlist.total_candidates_evaluated,
        "valid_candidates": shortlist.valid_candidates,
        "total_ranked": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),  # ceil division
        "processing_time_seconds": shortlist.processing_time_seconds,
        "engine_version": shortlist.engine_version,
        "weights_used": shortlist.weights_used,
        "candidates": [c.model_dump(exclude={"features"}) for c in page_items],
    }


# ---------------------------------------------------------------------------
# GET /candidate/{candidate_id}
# ---------------------------------------------------------------------------

@app.get(
    "/candidate/{candidate_id}",
    tags=["Results"],
    status_code=status.HTTP_200_OK,
)
async def get_candidate(candidate_id: str) -> Dict[str, Any]:
    """
    Retrieve the full details for a single ranked candidate, including the
    complete feature vector.

    Requires ``POST /analyze`` to have been run.
    """
    shortlist = _require_results()

    # ── Find in ranked list ───────────────────────────────────────────────
    ranked_entry: Optional[RankedCandidate] = None
    for cand in shortlist.ranked_candidates:
        if cand.candidate_id == candidate_id:
            ranked_entry = cand
            break

    if ranked_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found in the ranked results.",
        )

    # ── Attach full feature vector ────────────────────────────────────────
    feature_vec: Optional[CandidateFeatures] = None

    if not app.state.features:
        loaded = load_pickle(FEATURE_FILE)
        if loaded:
            app.state.features = loaded

    for feat in app.state.features:
        if feat.candidate_id == candidate_id:
            feature_vec = feat
            break

    result = ranked_entry.model_dump()
    result["features"] = feature_vec.model_dump() if feature_vec else None

    return {
        "status": "ok",
        **result,
    }


# ===========================================================================
# Global exception handler — pretty-print unexpected errors
# ===========================================================================

@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    log.exception(
        "[unhandled_exception] %s %s | PID=%d | %s: %s",
        request.method, request.url.path, os.getpid(),
        type(exc).__name__, exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "detail": str(exc), "type": type(exc).__name__},
    )


# ===========================================================================
# Direct-run entry-point  (python backend/main.py)
# ===========================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
