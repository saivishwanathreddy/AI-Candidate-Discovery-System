"""
semantic_engine.py
==================
Semantic Engine — generates sentence embeddings for candidates and the job
profile, then computes cosine similarity as a semantic matching score.

Design
------
* Wraps ``sentence-transformers`` model (default: ``all-MiniLM-L6-v2``).
* Loads model lazily on first use and caches it as a module-level singleton.
* Computes embeddings in configurable batches to stay within memory limits.
* Job profile embedding is computed once and reused for all candidates.
* All similarity scores are normalised to [0, 1].

Public API
----------
    SemanticEngine.embed_job(job_profile)                  -> np.ndarray
    SemanticEngine.embed_candidates(features_list)         -> np.ndarray
    SemanticEngine.score_candidates(features_list)         -> List[float]
    SemanticEngine.attach_scores(features_list)            -> List[CandidateFeatures]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).resolve().parent))

from candidate_models import CandidateFeatures, EngineConfig
from job_models import JobProfile
from logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton cache for the SentenceTransformer model
# ---------------------------------------------------------------------------
_MODEL_CACHE: dict = {}


def _get_model(model_name: str):
    """Load and cache a SentenceTransformer model (singleton per model name)."""
    if model_name not in _MODEL_CACHE:
        log.info("Loading SentenceTransformer model: %s", model_name)
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
            log.info("Model loaded successfully: %s", model_name)
        except Exception as exc:
            log.error("Failed to load SentenceTransformer model '%s': %s", model_name, exc)
            raise
    return _MODEL_CACHE[model_name]


def _build_job_text(job: JobProfile) -> str:
    """
    Build an embedding-ready text string from a JobProfile.

    Mirrors the style of build_embedding_text() for candidates so that
    job and candidate embeddings live in the same semantic space.
    """
    parts = [
        f"{job.job_title} at {job.company}.",
        f"Looking for {job.experience.min_years}-{job.experience.max_years} years of experience.",
        f"Work mode: {job.work_mode}.",
    ]

    req_skills = ", ".join(s.original for s in job.required_skills)
    if req_skills:
        parts.append(f"Required skills: {req_skills}.")

    pref_skills = ", ".join(s.original for s in job.preferred_skills[:8])
    if pref_skills:
        parts.append(f"Preferred skills: {pref_skills}.")

    if job.ai_technologies:
        parts.append(f"Technologies: {', '.join(job.ai_technologies[:15])}.")

    if job.evaluation_metrics:
        parts.append(f"Evaluation: {', '.join(job.evaluation_metrics[:6])}.")

    if job.responsibilities:
        # Top 3 responsibilities
        resp_text = ". ".join(job.responsibilities[:3])
        parts.append(resp_text)

    text = " ".join(parts)
    return text[:1500]


class SemanticEngine:
    """
    Generates sentence embeddings and computes semantic similarity scores.

    Parameters
    ----------
    config:
        EngineConfig specifying the embedding model name and batch size.
    """

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self.config = config or EngineConfig()
        self._model = None          # loaded on first embed call
        self._job_embedding: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Model access
    # ------------------------------------------------------------------

    @property
    def model(self):
        if self._model is None:
            self._model = _get_model(self.config.embedding_model)
        return self._model

    # ------------------------------------------------------------------
    # Job profile embedding
    # ------------------------------------------------------------------

    def embed_job(self, job: JobProfile) -> np.ndarray:
        """
        Compute and cache the embedding for the job profile.

        Parameters
        ----------
        job:
            Parsed JobProfile from the Job Intelligence Engine.

        Returns
        -------
        np.ndarray of shape (1, embedding_dim)
        """
        job_text = _build_job_text(job)
        log.info("Embedding job profile (%d chars) …", len(job_text))
        embedding = self.model.encode(
            [job_text],
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        self._job_embedding = embedding  # shape (1, dim)
        log.info("Job embedding computed. Shape: %s", embedding.shape)
        return embedding

    # ------------------------------------------------------------------
    # Candidate embeddings
    # ------------------------------------------------------------------

    def embed_candidates(
        self,
        features_list: List[CandidateFeatures],
    ) -> np.ndarray:
        """
        Compute embeddings for a list of CandidateFeatures.

        Uses the ``embedding_text`` field already built by FeatureEngine.

        Parameters
        ----------
        features_list:
            Output of FeatureEngine.batch_extract().

        Returns
        -------
        np.ndarray of shape (N, embedding_dim)
        """
        texts = [f.embedding_text for f in features_list]
        batch_size = self.config.embedding_batch_size

        log.info(
            "Embedding %d candidates in batches of %d …",
            len(texts), batch_size,
        )

        all_embeddings: List[np.ndarray] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start: start + batch_size]
            batch_emb = self.model.encode(
                batch,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            all_embeddings.append(batch_emb)

            processed = min(start + batch_size, len(texts))
            if processed % 1000 == 0 or processed == len(texts):
                log.info("  … %d / %d embedded", processed, len(texts))

        embeddings = np.vstack(all_embeddings)  # (N, dim)
        log.info("Candidate embeddings computed. Shape: %s", embeddings.shape)
        return embeddings

    # ------------------------------------------------------------------
    # Similarity scoring
    # ------------------------------------------------------------------

    def score_candidates(
        self,
        features_list: List[CandidateFeatures],
        job_embedding: Optional[np.ndarray] = None,
    ) -> List[float]:
        """
        Compute cosine similarity between each candidate and the job profile.

        Parameters
        ----------
        features_list:
            List of CandidateFeatures (embedding_text must be populated).
        job_embedding:
            Pre-computed job embedding.  If None, uses the cached embedding
            from the last call to ``embed_job()``.

        Returns
        -------
        List[float] of cosine similarity scores in [0, 1], one per candidate.
        """
        if job_embedding is None:
            job_embedding = self._job_embedding
        if job_embedding is None:
            raise RuntimeError(
                "Job embedding not available. Call embed_job(job_profile) first."
            )

        candidate_embeddings = self.embed_candidates(features_list)

        # cosine_similarity returns shape (N, 1)
        sims = cosine_similarity(candidate_embeddings, job_embedding)  # (N, 1)
        scores = sims[:, 0].tolist()

        # Clip to [0, 1] — cosine similarity can be slightly negative
        scores = [max(0.0, min(1.0, float(s))) for s in scores]
        log.info(
            "Semantic scores computed. Mean=%.4f  Max=%.4f  Min=%.4f",
            np.mean(scores), np.max(scores), np.min(scores),
        )
        return scores

    # ------------------------------------------------------------------
    # Convenience: embed job + score candidates in one call
    # ------------------------------------------------------------------

    def attach_scores(
        self,
        features_list: List[CandidateFeatures],
        job: JobProfile,
    ) -> List[CandidateFeatures]:
        """
        Embed the job profile, embed all candidates, compute cosine similarity,
        and attach the semantic_score to each CandidateFeatures object.

        Parameters
        ----------
        features_list:
            Mutable list of CandidateFeatures.
        job:
            The JobProfile to compare against.

        Returns
        -------
        The same list with ``semantic_score`` populated on each element.
        """
        job_emb = self.embed_job(job)
        scores = self.score_candidates(features_list, job_emb)

        for features, score in zip(features_list, scores):
            features.semantic_score = score

        return features_list


__all__ = ["SemanticEngine"]
