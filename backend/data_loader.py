"""
data_loader.py
==============
Dataset Loader for the AI Candidate Discovery System.

Responsibilities
----------------
* Stream ``candidates.jsonl`` line-by-line (O(1) memory usage).
* Parse each JSON line safely, skipping and logging any corrupted records.
* Validate every parsed record against ``candidate_schema.json`` (Draft-07).
* Materialise valid records as typed Pydantic models (``CandidateRecord``).
* Expose a streaming iterator *and* a convenience function that returns a list.
* Print a formatted Dataset Summary after a full-file load.

Public surface
--------------
    stream_candidates(path, validate, max_records)  -> Generator
    load_candidates(path, validate, max_records)    -> LoadResult
    load_sample_candidates()                        -> LoadResult

All other names are private implementation details.

Example usage
-------------
::

    from data_loader import load_candidates, load_sample_candidates

    # Full 100 000-candidate pool
    result = load_candidates()
    print(result.summary())

    # Quick smoke-test on the 50-candidate sample
    result = load_sample_candidates()
    for cand in result.candidates:
        print(cand.candidate_id, cand.profile.current_title)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

import jsonschema
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError
from tqdm import tqdm

from config import (
    CANDIDATES_JSONL,
    CANDIDATE_SCHEMA_JSON,
    FILE_ENCODING,
    LOADER_MAX_ERRORS_PER_RECORD,
    LOADER_PROGRESS_UPDATE_INTERVAL,
    LOADER_SCHEMA_VALIDATION_ENABLED,
    SAMPLE_CANDIDATES_JSON,
)
from logger import get_logger
from utils import Timer, bytes_to_human, count_file_lines, load_json_file

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Regex for fast candidate_id format check (CAND_XXXXXXX)
# ---------------------------------------------------------------------------
_CAND_ID_RE = re.compile(r"^CAND_[0-9]{7}$")

# ---------------------------------------------------------------------------
# Enumerations (string literals kept as plain str for Python 3.7 compat)
# ---------------------------------------------------------------------------
COMPANY_SIZE_VALUES = frozenset(
    ["1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000", "10001+"]
)
PROFICIENCY_VALUES = frozenset(["beginner", "intermediate", "advanced", "expert"])
LANGUAGE_PROFICIENCY_VALUES = frozenset(["basic", "conversational", "professional", "native"])
EDUCATION_TIER_VALUES = frozenset(["tier_1", "tier_2", "tier_3", "tier_4", "unknown"])
WORK_MODE_VALUES = frozenset(["remote", "hybrid", "onsite", "flexible"])


# ===========================================================================
# Pydantic models  (typed Python objects returned to callers)
# ===========================================================================

class CandidateProfile(BaseModel):
    """Core biographical and professional summary."""

    model_config = ConfigDict(extra="allow")

    anonymized_name: str
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: float = Field(..., ge=0, le=50)
    current_title: str
    current_company: str
    current_company_size: str
    current_industry: str

    @field_validator("current_company_size")
    @classmethod
    def _company_size_enum(cls, v: str) -> str:
        if v not in COMPANY_SIZE_VALUES:
            raise ValueError(f"Invalid current_company_size: '{v}'")
        return v


class CareerHistoryEntry(BaseModel):
    """A single role in a candidate's work history."""

    model_config = ConfigDict(extra="allow")

    company: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    duration_months: int = Field(..., ge=0)
    is_current: bool
    industry: str
    company_size: str
    description: str

    @field_validator("company_size")
    @classmethod
    def _company_size_enum(cls, v: str) -> str:
        if v not in COMPANY_SIZE_VALUES:
            raise ValueError(f"Invalid company_size: '{v}'")
        return v


class EducationEntry(BaseModel):
    """A single educational qualification."""

    model_config = ConfigDict(extra="allow")

    institution: str
    degree: str
    field_of_study: str
    start_year: int = Field(..., ge=1970, le=2030)
    end_year: int = Field(..., ge=1970, le=2035)
    grade: Optional[str] = None
    tier: Optional[str] = None

    @field_validator("tier")
    @classmethod
    def _tier_enum(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in EDUCATION_TIER_VALUES:
            raise ValueError(f"Invalid education tier: '{v}'")
        return v


class SkillEntry(BaseModel):
    """A single skill tag with proficiency and usage metadata."""

    model_config = ConfigDict(extra="allow")

    name: str
    proficiency: str
    endorsements: int = Field(..., ge=0)
    duration_months: Optional[int] = Field(None, ge=0)

    @field_validator("proficiency")
    @classmethod
    def _proficiency_enum(cls, v: str) -> str:
        if v not in PROFICIENCY_VALUES:
            raise ValueError(f"Invalid proficiency level: '{v}'")
        return v


class CertificationEntry(BaseModel):
    """A professional certification."""

    model_config = ConfigDict(extra="allow")

    name: str
    issuer: str
    year: int


class LanguageEntry(BaseModel):
    """A spoken / written language with proficiency level."""

    model_config = ConfigDict(extra="allow")

    language: str
    proficiency: str

    @field_validator("proficiency")
    @classmethod
    def _proficiency_enum(cls, v: str) -> str:
        if v not in LANGUAGE_PROFICIENCY_VALUES:
            raise ValueError(f"Invalid language proficiency: '{v}'")
        return v


class SalaryRange(BaseModel):
    """Expected salary range in INR Lakhs Per Annum."""

    model_config = ConfigDict(extra="allow")

    min: float = Field(..., ge=0)
    max: float = Field(..., ge=0)


class RedrobSignals(BaseModel):
    """23 platform behavioural and engagement signals."""

    model_config = ConfigDict(extra="allow")

    profile_completeness_score: float = Field(..., ge=0, le=100)
    signup_date: str
    last_active_date: str
    open_to_work_flag: bool
    profile_views_received_30d: int = Field(..., ge=0)
    applications_submitted_30d: int = Field(..., ge=0)
    recruiter_response_rate: float = Field(..., ge=0, le=1)
    avg_response_time_hours: float = Field(..., ge=0)
    skill_assessment_scores: Dict[str, float] = Field(default_factory=dict)
    connection_count: int = Field(..., ge=0)
    endorsements_received: int = Field(..., ge=0)
    notice_period_days: int = Field(..., ge=0, le=180)
    expected_salary_range_inr_lpa: SalaryRange
    preferred_work_mode: str
    willing_to_relocate: bool
    github_activity_score: float = Field(..., ge=-1, le=100)
    search_appearance_30d: int = Field(..., ge=0)
    saved_by_recruiters_30d: int = Field(..., ge=0)
    interview_completion_rate: float = Field(..., ge=0, le=1)
    offer_acceptance_rate: float = Field(..., ge=-1, le=1)
    verified_email: bool
    verified_phone: bool
    linkedin_connected: bool

    @field_validator("preferred_work_mode")
    @classmethod
    def _work_mode_enum(cls, v: str) -> str:
        if v not in WORK_MODE_VALUES:
            raise ValueError(f"Invalid preferred_work_mode: '{v}'")
        return v


class CandidateRecord(BaseModel):
    """
    A fully-typed Python representation of a single candidate record.

    Instances of this class are what callers receive from the loader.
    All fields map 1-to-1 to the JSON schema in ``candidate_schema.json``.
    """

    model_config = ConfigDict(extra="allow")

    candidate_id: str
    profile: CandidateProfile
    career_history: List[CareerHistoryEntry] = Field(..., min_length=1, max_length=10)
    education: List[EducationEntry] = Field(default_factory=list)
    skills: List[SkillEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    languages: List[LanguageEntry] = Field(default_factory=list)
    redrob_signals: RedrobSignals

    @field_validator("candidate_id")
    @classmethod
    def _id_pattern(cls, v: str) -> str:
        if not _CAND_ID_RE.match(v):
            raise ValueError(
                f"candidate_id '{v}' does not match pattern CAND_XXXXXXX"
            )
        return v


# ===========================================================================
# Error record  –  one instance per invalid line
# ===========================================================================

@dataclass
class ParseError:
    """Details about a single record that failed to parse or validate."""

    line_number: int
    candidate_id: Optional[str]      # may be None if JSON itself is broken
    error_type: str                  # "JSONDecodeError" | "PydanticValidation" | "SchemaValidation" | "Unknown"
    messages: List[str]              # up to LOADER_MAX_ERRORS_PER_RECORD messages

    def __str__(self) -> str:
        msg_summary = "; ".join(self.messages[:3])
        more = len(self.messages) - 3
        suffix = f" … (+{more} more)" if more > 0 else ""
        return (
            f"Line {self.line_number} "
            f"[{self.candidate_id or 'unknown_id'}] "
            f"{self.error_type}: {msg_summary}{suffix}"
        )


# ===========================================================================
# Load result container
# ===========================================================================

@dataclass
class LoadResult:
    """
    Encapsulates the outcome of a full dataset load.

    Attributes
    ----------
    candidates:
        All successfully parsed and validated ``CandidateRecord`` objects.
    errors:
        One ``ParseError`` per line that could not be loaded.
    total_lines:
        Raw line count including empty/corrupted lines.
    elapsed_seconds:
        Wall-clock time taken to complete the load.
    source_path:
        The file that was loaded.
    """

    candidates: List[CandidateRecord]
    errors: List[ParseError]
    total_lines: int
    elapsed_seconds: float
    source_path: Path

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def total_candidates(self) -> int:
        """Total non-empty lines seen."""
        return self.total_lines

    @property
    def valid_count(self) -> int:
        """Number of successfully loaded candidate records."""
        return len(self.candidates)

    @property
    def invalid_count(self) -> int:
        """Number of records that failed parsing or validation."""
        return len(self.errors)

    @property
    def success_rate(self) -> float:
        """Fraction of records that loaded cleanly (0.0 – 1.0)."""
        if self.total_lines == 0:
            return 0.0
        return self.valid_count / self.total_lines

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a formatted multi-line summary string."""
        file_size = bytes_to_human(self.source_path.stat().st_size) if self.source_path.exists() else "N/A"
        from utils import format_duration
        lines = [
            "",
            "=" * 52,
            "  ## Dataset Summary",
            "=" * 52,
            f"  Source File       : {self.source_path.name}",
            f"  File Size         : {file_size}",
            f"  Total Candidates  : {self.total_candidates:,}",
            f"  Valid Candidates  : {self.valid_count:,}",
            f"  Invalid Candidates: {self.invalid_count:,}",
            f"  Success Rate      : {self.success_rate:.2%}",
            f"  Processing Time   : {format_duration(self.elapsed_seconds)}",
            "=" * 52,
        ]
        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print the formatted summary to stdout."""
        print(self.summary())

    def print_errors(self, limit: int = 20) -> None:
        """Print the first *limit* parse errors to stdout."""
        if not self.errors:
            print("No errors recorded.")
            return
        print(f"\nFirst {min(limit, len(self.errors))} parse errors:")
        for err in self.errors[:limit]:
            print(f"  {err}")
        if len(self.errors) > limit:
            print(f"  … and {len(self.errors) - limit} more (see log file for full list)")


# ===========================================================================
# Schema loader  (cached singleton)
# ===========================================================================

_CACHED_SCHEMA: Optional[Dict[str, Any]] = None
_CACHED_VALIDATOR: Optional[jsonschema.Draft7Validator] = None


def _get_schema_validator() -> Optional[jsonschema.Draft7Validator]:
    """
    Load and cache the JSON Schema validator.

    Returns *None* if schema validation is disabled in config or if the
    schema file cannot be found.
    """
    global _CACHED_SCHEMA, _CACHED_VALIDATOR

    if not LOADER_SCHEMA_VALIDATION_ENABLED:
        return None

    if _CACHED_VALIDATOR is not None:
        return _CACHED_VALIDATOR

    if not CANDIDATE_SCHEMA_JSON.exists():
        log.warning(
            "candidate_schema.json not found at %s. "
            "Schema validation will be skipped.",
            CANDIDATE_SCHEMA_JSON,
        )
        return None

    try:
        _CACHED_SCHEMA = load_json_file(CANDIDATE_SCHEMA_JSON)
        _CACHED_VALIDATOR = jsonschema.Draft7Validator(_CACHED_SCHEMA)
        log.info("JSON Schema validator loaded from: %s", CANDIDATE_SCHEMA_JSON)
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to load JSON Schema: %s", exc)
        return None

    return _CACHED_VALIDATOR


# ===========================================================================
# Core parsing pipeline
# ===========================================================================

def _parse_raw_line(
    raw_line: str,
    line_number: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[ParseError]]:
    """
    Parse a single raw string into a Python dict.

    Returns
    -------
    (dict, None)  on success
    (None, ParseError) on failure
    """
    try:
        data = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        err = ParseError(
            line_number=line_number,
            candidate_id=None,
            error_type="JSONDecodeError",
            messages=[str(exc)],
        )
        return None, err

    if not isinstance(data, dict):
        err = ParseError(
            line_number=line_number,
            candidate_id=None,
            error_type="StructureError",
            messages=[f"Expected JSON object, got {type(data).__name__}"],
        )
        return None, err

    return data, None


def _validate_against_schema(
    data: Dict[str, Any],
    line_number: int,
    validator: jsonschema.Draft7Validator,
) -> Optional[ParseError]:
    """
    Validate a dict against the JSON Schema.

    Returns *None* if the record is valid, otherwise a ``ParseError``
    containing up to ``LOADER_MAX_ERRORS_PER_RECORD`` error messages.
    """
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if not errors:
        return None

    messages = [
        f"[{'.'.join(str(p) for p in e.path) or 'root'}] {e.message}"
        for e in errors[:LOADER_MAX_ERRORS_PER_RECORD]
    ]

    return ParseError(
        line_number=line_number,
        candidate_id=data.get("candidate_id"),
        error_type="SchemaValidation",
        messages=messages,
    )


def _build_candidate_record(
    data: Dict[str, Any],
    line_number: int,
) -> Tuple[Optional[CandidateRecord], Optional[ParseError]]:
    """
    Attempt to construct a ``CandidateRecord`` Pydantic model from a dict.

    Returns
    -------
    (CandidateRecord, None)  on success
    (None, ParseError)       on Pydantic validation failure
    """
    try:
        record = CandidateRecord(**data)
        return record, None
    except ValidationError as exc:
        messages = [
            f"[{'.'.join(str(loc) for loc in e['loc'])}] {e['msg']}"
            for e in exc.errors()[:LOADER_MAX_ERRORS_PER_RECORD]
        ]
        return None, ParseError(
            line_number=line_number,
            candidate_id=data.get("candidate_id"),
            error_type="PydanticValidation",
            messages=messages,
        )
    except Exception as exc:  # noqa: BLE001
        return None, ParseError(
            line_number=line_number,
            candidate_id=data.get("candidate_id"),
            error_type="Unknown",
            messages=[str(exc)],
        )


# ===========================================================================
# Public streaming interface
# ===========================================================================

def stream_candidates(
    path: Union[str, Path, None] = None,
    validate: bool = True,
    max_records: Optional[int] = None,
) -> Generator[CandidateRecord, None, None]:
    """
    Stream candidate records from a JSONL file one at a time.

    This is the **memory-efficient** entry point.  Only one
    ``CandidateRecord`` object is live in memory at any given moment;
    the rest of the file is still on disk.

    Parameters
    ----------
    path:
        Path to a ``.jsonl`` file.  Defaults to ``CANDIDATES_JSONL``
        from ``config.py``.
    validate:
        When *True* (default) each record is validated against the JSON
        Schema *and* via Pydantic field constraints before being yielded.
        When *False* only Pydantic model construction is attempted.
    max_records:
        Stop after yielding this many valid records.  *None* means
        yield all records in the file.

    Yields
    ------
    CandidateRecord
        One fully-typed record per valid line.

    Notes
    -----
    * Corrupted lines are logged at WARNING level and skipped.
    * This generator does **not** collect errors; use ``load_candidates()``
      when you need the full error list.
    """
    target_path = Path(path) if path else CANDIDATES_JSONL

    if not target_path.exists():
        raise FileNotFoundError(
            f"Candidates file not found: {target_path}\n"
            "Check CANDIDATES_JSONL in config.py."
        )

    schema_validator = _get_schema_validator() if validate else None
    yielded = 0

    log.info("Streaming candidates from: %s", target_path)

    with target_path.open("r", encoding=FILE_ENCODING, errors="replace") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue  # skip blank separators

            # --- Step 1: JSON parse ---
            data, err = _parse_raw_line(raw_line, line_number)
            if err:
                log.warning("Stream – %s", err)
                continue

            # --- Step 2: JSON Schema validation ---
            if schema_validator is not None:
                schema_err = _validate_against_schema(data, line_number, schema_validator)
                if schema_err:
                    log.warning("Stream – %s", schema_err)
                    continue

            # --- Step 3: Pydantic model construction ---
            record, model_err = _build_candidate_record(data, line_number)
            if model_err:
                log.warning("Stream – %s", model_err)
                continue

            yield record  # type: ignore[misc]
            yielded += 1

            if max_records is not None and yielded >= max_records:
                log.info("Reached max_records limit (%d). Stopping stream.", max_records)
                return

    log.info("Stream complete. Yielded %d valid records.", yielded)


# ===========================================================================
# Public batch-load interface
# ===========================================================================

def load_candidates(
    path: Union[str, Path, None] = None,
    validate: bool = True,
    max_records: Optional[int] = None,
    show_progress: bool = True,
) -> LoadResult:
    """
    Load the full candidate dataset into memory as a ``LoadResult``.

    This function wraps the streaming pipeline with:
    * a tqdm progress bar
    * error collection
    * timing
    * a printed summary

    Parameters
    ----------
    path:
        Path to a ``.jsonl`` file.  Defaults to ``CANDIDATES_JSONL``.
    validate:
        Validate every record against the JSON Schema + Pydantic constraints.
    max_records:
        Stop after this many valid records (useful for debugging).
    show_progress:
        Display a tqdm progress bar on stderr.

    Returns
    -------
    LoadResult
        Contains the list of ``CandidateRecord`` objects, error list, counts,
        timing, and a ``summary()`` method.
    """
    target_path = Path(path) if path else CANDIDATES_JSONL

    if not target_path.exists():
        raise FileNotFoundError(
            f"Candidates file not found: {target_path}\n"
            "Check CANDIDATES_JSONL in config.py."
        )

    log.info("=" * 60)
    log.info("Starting dataset load")
    log.info("  Source : %s", target_path)
    log.info("  Validate: %s", validate)
    log.info("  Max records: %s", max_records if max_records else "all")
    log.info("=" * 60)

    # Pre-count lines for an accurate progress bar
    # (one quick pass over the file; trivial cost vs validation)
    if show_progress:
        log.info("Pre-counting lines in %s …", target_path.name)
        total_lines = count_file_lines(target_path)
        log.info("File contains %d non-empty lines.", total_lines)
    else:
        total_lines = None  # tqdm will run without a total

    schema_validator = _get_schema_validator() if validate else None

    candidates: List[CandidateRecord] = []
    errors: List[ParseError] = []
    total_seen = 0          # non-empty lines processed

    progress_bar = tqdm(
        total=total_lines,
        desc="Loading candidates",
        unit="rec",
        unit_scale=True,
        dynamic_ncols=True,
        disable=not show_progress,
        mininterval=0.2,
        file=sys.stderr,
    )

    with Timer() as timer:
        try:
            with target_path.open("r", encoding=FILE_ENCODING, errors="replace") as fh:
                for line_number, raw_line in enumerate(fh, start=1):
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue  # skip blank lines / Windows CRLF artefacts

                    total_seen += 1

                    # ---- Step 1: JSON parse --------------------------------
                    data, err = _parse_raw_line(raw_line, line_number)
                    if err:
                        errors.append(err)
                        log.warning("%s", err)
                        progress_bar.update(1)
                        continue

                    # ---- Step 2: JSON Schema validation --------------------
                    if schema_validator is not None:
                        schema_err = _validate_against_schema(
                            data, line_number, schema_validator
                        )
                        if schema_err:
                            errors.append(schema_err)
                            log.debug("%s", schema_err)
                            progress_bar.update(1)
                            continue

                    # ---- Step 3: Pydantic model construction ---------------
                    record, model_err = _build_candidate_record(data, line_number)
                    if model_err:
                        errors.append(model_err)
                        log.debug("%s", model_err)
                        progress_bar.update(1)
                        continue

                    candidates.append(record)  # type: ignore[arg-type]
                    progress_bar.update(1)

                    # ---- Progress bar postfix (every N records) ------------
                    if total_seen % LOADER_PROGRESS_UPDATE_INTERVAL == 0:
                        progress_bar.set_postfix(
                            valid=len(candidates),
                            invalid=len(errors),
                            refresh=False,
                        )

                    # ---- Early stop ----------------------------------------
                    if max_records is not None and len(candidates) >= max_records:
                        log.info(
                            "Reached max_records limit (%d). Stopping load.",
                            max_records,
                        )
                        break

        finally:
            progress_bar.close()

    result = LoadResult(
        candidates=candidates,
        errors=errors,
        total_lines=total_seen,
        elapsed_seconds=timer.elapsed_seconds,
        source_path=target_path,
    )

    # Log summary at INFO level
    log.info(
        "Load complete | total=%d | valid=%d | invalid=%d | time=%.2fs",
        result.total_candidates,
        result.valid_count,
        result.invalid_count,
        result.elapsed_seconds,
    )

    # Print formatted summary to stdout
    result.print_summary()

    return result


# ===========================================================================
# Convenience function for the 50-candidate sample
# ===========================================================================

def load_sample_candidates(
    validate: bool = True,
    show_progress: bool = True,
) -> LoadResult:
    """
    Load the 50-candidate pretty-printed sample JSON.

    Converts the JSON array to a temporary in-memory JSONL format so the
    same pipeline handles both file types consistently.

    Parameters
    ----------
    validate:
        Validate every record against the JSON Schema + Pydantic constraints.
    show_progress:
        Display a tqdm progress bar.

    Returns
    -------
    LoadResult
    """
    if not SAMPLE_CANDIDATES_JSON.exists():
        raise FileNotFoundError(
            f"Sample file not found: {SAMPLE_CANDIDATES_JSON}\n"
            "Check SAMPLE_CANDIDATES_JSON in config.py."
        )

    log.info("Loading sample candidates from: %s", SAMPLE_CANDIDATES_JSON)

    raw_list: List[Dict[str, Any]]
    try:
        raw_list = load_json_file(SAMPLE_CANDIDATES_JSON)
    except Exception as exc:
        raise RuntimeError(f"Failed to load sample file: {exc}") from exc

    if not isinstance(raw_list, list):
        raise ValueError(
            "sample_candidates.json must be a JSON array at the top level."
        )

    schema_validator = _get_schema_validator() if validate else None

    candidates: List[CandidateRecord] = []
    errors: List[ParseError] = []

    progress_bar = tqdm(
        total=len(raw_list),
        desc="Loading sample",
        unit="rec",
        dynamic_ncols=True,
        disable=not show_progress,
        file=sys.stderr,
    )

    with Timer() as timer:
        for idx, data in enumerate(raw_list, start=1):
            if not isinstance(data, dict):
                errors.append(
                    ParseError(
                        line_number=idx,
                        candidate_id=None,
                        error_type="StructureError",
                        messages=[f"Array element {idx} is not a JSON object"],
                    )
                )
                progress_bar.update(1)
                continue

            # Schema validation
            if schema_validator is not None:
                schema_err = _validate_against_schema(data, idx, schema_validator)
                if schema_err:
                    errors.append(schema_err)
                    log.debug("%s", schema_err)
                    progress_bar.update(1)
                    continue

            # Pydantic model construction
            record, model_err = _build_candidate_record(data, idx)
            if model_err:
                errors.append(model_err)
                log.debug("%s", model_err)
                progress_bar.update(1)
                continue

            candidates.append(record)  # type: ignore[arg-type]
            progress_bar.update(1)

    progress_bar.close()

    result = LoadResult(
        candidates=candidates,
        errors=errors,
        total_lines=len(raw_list),
        elapsed_seconds=timer.elapsed_seconds,
        source_path=SAMPLE_CANDIDATES_JSON,
    )

    log.info(
        "Sample load complete | total=%d | valid=%d | invalid=%d | time=%.2fs",
        result.total_candidates,
        result.valid_count,
        result.invalid_count,
        result.elapsed_seconds,
    )

    result.print_summary()
    return result


# ===========================================================================
# CLI entry-point  –  run this file directly to load the full dataset
# ===========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Redrob AI Candidate Discovery – Dataset Loader"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Load the 50-candidate sample instead of the full 100K pool.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N valid records (useful for quick testing).",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip JSON Schema validation (faster, less strict).",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress the tqdm progress bar.",
    )
    parser.add_argument(
        "--show-errors",
        type=int,
        default=0,
        metavar="N",
        help="Print the first N parse errors after loading.",
    )

    args = parser.parse_args()

    if args.sample:
        result = load_sample_candidates(
            validate=not args.no_validate,
            show_progress=not args.no_progress,
        )
    else:
        result = load_candidates(
            validate=not args.no_validate,
            max_records=args.max_records,
            show_progress=not args.no_progress,
        )

    if args.show_errors > 0:
        result.print_errors(limit=args.show_errors)
