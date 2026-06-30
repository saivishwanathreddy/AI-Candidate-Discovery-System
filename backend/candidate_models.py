"""
candidate_models.py
===================
Pydantic v2 models for the Candidate Intelligence Engine.

Defines the complete data contracts for:
  - CandidateFeatures   : normalised feature vector per candidate
  - ScoreBreakdown      : per-dimension weighted scores
  - RankedCandidate     : a single entry in the ranked shortlist
  - ShortlistResult     : the complete API response for /rank
  - EngineConfig        : configurable scoring weights
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ===========================================================================
# Engine configuration (weights, thresholds)
# ===========================================================================

class EngineConfig(BaseModel):
    """
    Scoring weights and operational thresholds for the Ranking Engine.

    All weights are automatically normalised to sum to 1.0 so callers can
    specify relative priorities without needing to balance them manually.
    """

    model_config = ConfigDict(extra="allow")

    # ---- Dimension weights (relative, auto-normalised) --------------------
    weight_semantic: float = Field(default=0.35, ge=0, description="Semantic similarity weight.")
    weight_technical: float = Field(default=0.30, ge=0, description="Technical skill match weight.")
    weight_experience: float = Field(default=0.15, ge=0, description="Experience quality weight.")
    weight_behavior: float = Field(default=0.12, ge=0, description="Behavioral signals weight.")
    weight_trust: float = Field(default=0.08, ge=0, description="Trust / profile quality weight.")

    # ---- Risk penalty (applied after normalised score) --------------------
    risk_penalty_scale: float = Field(
        default=0.40,
        ge=0, le=1.0,
        description="Maximum fractional penalty applied to confirmed honeypots (0=none, 1=full zero).",
    )

    # ---- Behavioral signal thresholds ------------------------------------
    inactivity_decay_halflife_days: float = Field(
        default=90.0, gt=0,
        description="Half-life (days) for exponential recency decay on last_active_date.",
    )
    notice_period_preferred_days: int = Field(
        default=30, ge=0,
        description="Notice period at or below this is full score.",
    )
    notice_period_max_days: int = Field(
        default=150, ge=0,
        description="Notice period at or above this receives minimum score.",
    )

    # ---- Semantic engine -------------------------------------------------
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformer model name for embedding generation.",
    )
    embedding_batch_size: int = Field(
        default=256, ge=1,
        description="Batch size for embedding inference.",
    )

    # ---- Ranking output --------------------------------------------------
    top_k: int = Field(default=100, ge=1, le=100, description="Number of candidates to return.")

    @model_validator(mode="after")
    def _weights_positive(self) -> "EngineConfig":
        total = (
            self.weight_semantic + self.weight_technical
            + self.weight_experience + self.weight_behavior + self.weight_trust
        )
        if total <= 0:
            raise ValueError("Sum of all scoring weights must be > 0.")
        return self

    def normalised_weights(self) -> Dict[str, float]:
        """Return weight dict normalised to sum to 1.0."""
        total = (
            self.weight_semantic + self.weight_technical
            + self.weight_experience + self.weight_behavior + self.weight_trust
        )
        return {
            "semantic": self.weight_semantic / total,
            "technical": self.weight_technical / total,
            "experience": self.weight_experience / total,
            "behavior": self.weight_behavior / total,
            "trust": self.weight_trust / total,
        }


# ===========================================================================
# Feature sub-models
# ===========================================================================

class TechnicalFeatures(BaseModel):
    """Normalised technical skill features (all values 0.0–1.0 unless noted)."""

    model_config = ConfigDict(extra="allow")

    # Skill match counts
    required_skills_matched: int = Field(default=0, ge=0)
    preferred_skills_matched: int = Field(default=0, ge=0)
    required_skill_match_ratio: float = Field(default=0.0, ge=0, le=1.0)
    preferred_skill_match_ratio: float = Field(default=0.0, ge=0, le=1.0)

    # Domain presence flags / scores (0.0 or 1.0)
    has_python: float = Field(default=0.0, ge=0, le=1.0)
    has_ai_ml: float = Field(default=0.0, ge=0, le=1.0)
    has_nlp: float = Field(default=0.0, ge=0, le=1.0)
    has_llm: float = Field(default=0.0, ge=0, le=1.0)
    has_embeddings: float = Field(default=0.0, ge=0, le=1.0)
    has_retrieval: float = Field(default=0.0, ge=0, le=1.0)
    has_vector_db: float = Field(default=0.0, ge=0, le=1.0)
    has_backend: float = Field(default=0.0, ge=0, le=1.0)
    has_mlops: float = Field(default=0.0, ge=0, le=1.0)
    has_evaluation_metrics: float = Field(default=0.0, ge=0, le=1.0)

    # Depth scores (weighted by duration and proficiency)
    ai_skill_depth_score: float = Field(default=0.0, ge=0, le=1.0)
    has_ai_certification: float = Field(default=0.0, ge=0, le=1.0)

    # Matched skill names (for explainability)
    matched_required_skill_names: List[str] = Field(default_factory=list)
    matched_preferred_skill_names: List[str] = Field(default_factory=list)
    unmatched_required_skill_names: List[str] = Field(default_factory=list)


class ExperienceFeatures(BaseModel):
    """Normalised career / experience features."""

    model_config = ConfigDict(extra="allow")

    total_years: float = Field(default=0.0, ge=0)
    ai_years: float = Field(default=0.0, ge=0)
    ai_year_ratio: float = Field(default=0.0, ge=0, le=1.0)

    # Company quality signals
    product_company_months: float = Field(default=0.0, ge=0)
    consulting_only: bool = Field(default=False)
    has_startup_experience: bool = Field(default=False)
    has_leadership_role: bool = Field(default=False)

    # Derived scores (0.0–1.0)
    years_score: float = Field(default=0.0, ge=0, le=1.0, description="How well YoE matches JD target.")
    company_quality_score: float = Field(default=0.0, ge=0, le=1.0)
    career_progression_score: float = Field(default=0.0, ge=0, le=1.0)

    # For explainability
    current_title: str = Field(default="")
    current_company: str = Field(default="")
    current_industry: str = Field(default="")


class EducationFeatures(BaseModel):
    """Normalised education features."""

    model_config = ConfigDict(extra="allow")

    best_tier: int = Field(default=4, ge=1, le=4, description="1=tier_1 (best), 4=tier_4 (lowest).")
    has_stem_degree: bool = Field(default=False)
    has_advanced_degree: bool = Field(default=False)
    has_ai_certification: bool = Field(default=False)
    education_score: float = Field(default=0.0, ge=0, le=1.0)
    highest_degree: str = Field(default="")
    field_of_study: str = Field(default="")


class BehaviorFeatures(BaseModel):
    """Normalised behavioral / availability signals."""

    model_config = ConfigDict(extra="allow")

    open_to_work: bool = Field(default=False)
    recruiter_response_rate: float = Field(default=0.0, ge=0, le=1.0)
    interview_completion_rate: float = Field(default=0.0, ge=0, le=1.0)
    recency_score: float = Field(default=0.0, ge=0, le=1.0, description="Decay of last_active_date.")
    notice_period_days: int = Field(default=90, ge=0)
    notice_period_score: float = Field(default=0.0, ge=0, le=1.0)
    applications_submitted_30d: int = Field(default=0, ge=0)
    profile_views_30d: int = Field(default=0, ge=0)
    days_since_active: int = Field(default=999, ge=0)
    behavior_score: float = Field(default=0.0, ge=0, le=1.0)


class TrustFeatures(BaseModel):
    """Profile quality, verification, and external signals."""

    model_config = ConfigDict(extra="allow")

    profile_completeness: float = Field(default=0.0, ge=0, le=1.0)
    verified_email: bool = Field(default=False)
    verified_phone: bool = Field(default=False)
    linkedin_connected: bool = Field(default=False)
    github_score: float = Field(default=0.0, ge=0, le=1.0, description="Normalised github_activity_score (−1 → 0).")
    has_github: bool = Field(default=False)
    trust_score: float = Field(default=0.0, ge=0, le=1.0)


class RiskFeatures(BaseModel):
    """Risk signals: honeypot indicators, keyword stuffing, data anomalies."""

    model_config = ConfigDict(extra="allow")

    salary_inverted: bool = Field(
        default=False, description="salary_min > salary_max → honeypot signal."
    )
    date_inverted: bool = Field(
        default=False, description="signup_date > last_active_date → honeypot signal."
    )
    experience_anomaly: bool = Field(
        default=False, description="Sum of job durations >> declared YoE."
    )
    skill_stuffing_score: float = Field(
        default=0.0, ge=0, le=1.0,
        description="High AI skill count with non-AI career history.",
    )
    honeypot_probability: float = Field(
        default=0.0, ge=0, le=1.0,
        description="Aggregate probability of this being a honeypot record.",
    )
    risk_flags: List[str] = Field(default_factory=list)


# ===========================================================================
# Aggregate feature vector
# ===========================================================================

class CandidateFeatures(BaseModel):
    """
    Complete normalised feature vector for a single candidate.
    Output of FeatureEngine.extract(); input to RankingEngine.score().
    """

    model_config = ConfigDict(extra="allow")

    candidate_id: str
    name: str = Field(default="")
    location: str = Field(default="")
    country: str = Field(default="")

    technical: TechnicalFeatures = Field(default_factory=TechnicalFeatures)
    experience: ExperienceFeatures = Field(default_factory=ExperienceFeatures)
    education: EducationFeatures = Field(default_factory=EducationFeatures)
    behavior: BehaviorFeatures = Field(default_factory=BehaviorFeatures)
    trust: TrustFeatures = Field(default_factory=TrustFeatures)
    risk: RiskFeatures = Field(default_factory=RiskFeatures)

    # Semantic score is filled in by SemanticEngine (after embedding)
    semantic_score: float = Field(default=0.0, ge=0, le=1.0)

    # Pre-computed embedding text (used by SemanticEngine)
    embedding_text: str = Field(default="", description="Concatenated text used for embedding.")


# ===========================================================================
# Scoring & output models
# ===========================================================================

class ScoreBreakdown(BaseModel):
    """Per-dimension scores and weights that produced the final score."""

    model_config = ConfigDict(extra="allow")

    semantic: float = Field(default=0.0, ge=0, le=1.0)
    technical: float = Field(default=0.0, ge=0, le=1.0)
    experience: float = Field(default=0.0, ge=0, le=1.0)
    behavior: float = Field(default=0.0, ge=0, le=1.0)
    trust: float = Field(default=0.0, ge=0, le=1.0)
    risk_penalty: float = Field(default=0.0, ge=0, le=1.0)
    raw_weighted: float = Field(default=0.0, ge=0, le=1.0, description="Weighted sum before risk penalty.")
    final_score: float = Field(default=0.0, ge=0, le=1.0, description="Score after risk penalty.")
    weights_used: Dict[str, float] = Field(default_factory=dict)


class ExplainabilityNote(BaseModel):
    """A single human-readable explanation point for a ranked candidate."""

    model_config = ConfigDict(extra="allow")

    dimension: str = Field(..., description="e.g. 'technical', 'experience', 'risk'")
    sentiment: str = Field(..., description="'positive' | 'neutral' | 'negative'")
    message: str = Field(..., description="Human-readable explanation.")
    impact: float = Field(default=0.0, description="Signed impact on score (for ordering).")


class RankedCandidate(BaseModel):
    """A single entry in the ranked shortlist — returned by /rank and /top-candidates."""

    model_config = ConfigDict(extra="allow")

    rank: int = Field(..., ge=1, le=100)
    candidate_id: str
    name: str = Field(default="")
    current_title: str = Field(default="")
    current_company: str = Field(default="")
    location: str = Field(default="")
    years_of_experience: float = Field(default=0.0)
    score: float = Field(..., ge=0, le=1.0)
    reasoning: str = Field(..., description="1-2 sentence summary for submission CSV.")
    score_breakdown: ScoreBreakdown
    explanations: List[ExplainabilityNote] = Field(default_factory=list)
    features: Optional[CandidateFeatures] = Field(
        default=None, description="Full feature vector (omitted in list views)."
    )


class ShortlistResult(BaseModel):
    """Complete response payload for the /rank endpoint."""

    model_config = ConfigDict(extra="allow")

    job_title: str
    company: str
    total_candidates_evaluated: int
    valid_candidates: int
    invalid_candidates: int
    top_k: int
    ranked_candidates: List[RankedCandidate]
    processing_time_seconds: float
    engine_version: str = Field(default="1.0.0")
    weights_used: Dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
__all__ = [
    "EngineConfig",
    "TechnicalFeatures",
    "ExperienceFeatures",
    "EducationFeatures",
    "BehaviorFeatures",
    "TrustFeatures",
    "RiskFeatures",
    "CandidateFeatures",
    "ScoreBreakdown",
    "ExplainabilityNote",
    "RankedCandidate",
    "ShortlistResult",
]
