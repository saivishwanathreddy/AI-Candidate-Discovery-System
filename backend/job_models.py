"""
job_models.py
=============
Pydantic v2 data models for the Job Intelligence Engine.

These models represent a structured, validated, semantically-rich
interpretation of a job description — not a raw text dump.

All models are importable independently; they carry no parser logic.

Public classes
--------------
    ExperienceRange
    SkillItem
    SalaryRange
    NoticePeriod
    JobProfile      ← primary model returned by the parser
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class ExperienceRange(BaseModel):
    """
    Parsed experience expectation from the JD.

    Stores both the soft-range stated in the JD and the implicit
    recommended range decoded from context ("What we mean by 5-9 years").
    """

    model_config = ConfigDict(extra="allow")

    min_years: float = Field(..., ge=0, description="Minimum required years of experience.")
    max_years: float = Field(..., ge=0, description="Maximum / upper bound stated in JD.")
    recommended_min: Optional[float] = Field(
        None,
        ge=0,
        description=(
            "Implicit recommended minimum derived from contextual parsing. "
            "For this JD: 4 years (product ML)."
        ),
    )
    recommended_max: Optional[float] = Field(
        None,
        ge=0,
        description="Implicit recommended upper bound from contextual parsing.",
    )
    note: Optional[str] = Field(
        None,
        description="Free-text clarification the JD provides about the range.",
    )

    @model_validator(mode="after")
    def _range_valid(self) -> "ExperienceRange":
        if self.min_years > self.max_years:
            raise ValueError(
                f"min_years ({self.min_years}) cannot exceed max_years ({self.max_years})."
            )
        if (
            self.recommended_min is not None
            and self.recommended_max is not None
            and self.recommended_min > self.recommended_max
        ):
            raise ValueError(
                "recommended_min cannot exceed recommended_max."
            )
        return self

    def __str__(self) -> str:
        return f"{self.min_years}-{self.max_years} years"


class SkillItem(BaseModel):
    """
    A single normalised skill entry extracted from the JD.

    ``canonical`` is the normalised, lowercased, deduplicated form used
    for matching.  ``original`` preserves the raw text for display.
    """

    model_config = ConfigDict(extra="allow")

    original: str = Field(..., description="Raw skill text as it appears in the JD.")
    canonical: str = Field(..., description="Normalised lowercase skill label.")
    category: Optional[str] = Field(
        None,
        description=(
            "Taxonomy bucket: 'embedding' | 'vector_db' | 'evaluation' | "
            "'llm' | 'language' | 'framework' | 'platform' | 'soft_skill' | 'other'."
        ),
    )

    @field_validator("canonical")
    @classmethod
    def _strip_canonical(cls, v: str) -> str:
        return v.strip().lower()

    def __hash__(self) -> int:
        return hash(self.canonical)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SkillItem):
            return self.canonical == other.canonical
        return False

    def __str__(self) -> str:
        return self.original


class SalaryRange(BaseModel):
    """Salary expectation range, when stated in the JD."""

    model_config = ConfigDict(extra="allow")

    min_lpa: Optional[float] = Field(None, ge=0, description="Minimum CTC in LPA (INR).")
    max_lpa: Optional[float] = Field(None, ge=0, description="Maximum CTC in LPA (INR).")
    currency: str = Field(default="INR", description="Currency code.")
    note: Optional[str] = Field(None, description="Raw salary text from the JD.")

    @model_validator(mode="after")
    def _range_valid(self) -> "SalaryRange":
        if (
            self.min_lpa is not None
            and self.max_lpa is not None
            and self.min_lpa > self.max_lpa
        ):
            raise ValueError("min_lpa cannot exceed max_lpa.")
        return self


class NoticePeriod(BaseModel):
    """Parsed notice period expectation."""

    model_config = ConfigDict(extra="allow")

    preferred_max_days: Optional[int] = Field(
        None,
        ge=0,
        description="Preferred maximum notice period in days.",
    )
    acceptable_max_days: Optional[int] = Field(
        None,
        ge=0,
        description="Absolute maximum acceptable notice period in days.",
    )
    buyout_available: bool = Field(
        default=False,
        description="True if the employer offers to buy out the notice period.",
    )
    buyout_max_days: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum days the employer is willing to buy out.",
    )
    note: Optional[str] = Field(None, description="Raw notice-period text from the JD.")


# ---------------------------------------------------------------------------
# Primary model
# ---------------------------------------------------------------------------

class JobProfile(BaseModel):
    """
    A structured, validated, semantically-rich representation of a job
    description.

    All 18 fields requested in the specification are present.  Several carry
    cross-field validation (e.g. required_skills cannot be empty, experience
    range must be consistent).

    Helper methods
    --------------
    required_skill_count()  -> int
    has_skill(name)         -> bool
    to_dict()               -> Dict[str, Any]
    summary()               -> str
    """

    model_config = ConfigDict(extra="allow")

    # ── 1. Identity ────────────────────────────────────────────────────────
    job_title: str = Field(..., description="Normalised job title.")
    company: str = Field(..., description="Hiring company name.")
    department: Optional[str] = Field(None, description="Team / department if stated.")
    employment_type: Optional[str] = Field(
        None, description="e.g. 'Full-time', 'Contract'."
    )

    # ── 2. Experience ───────────────────────────────────────────────────────
    experience: ExperienceRange = Field(
        ..., description="Parsed experience requirement."
    )

    # ── 3-4. Skills ─────────────────────────────────────────────────────────
    required_skills: List[SkillItem] = Field(
        ...,
        description="Skills explicitly required — failing to have these is disqualifying.",
    )
    preferred_skills: List[SkillItem] = Field(
        default_factory=list,
        description="Skills desired but not dealbreakers.",
    )
    disqualifying_profiles: List[str] = Field(
        default_factory=list,
        description=(
            "Candidate archetypes the JD explicitly rejects "
            "(e.g. 'Pure research background', 'Consulting-only career')."
        ),
    )

    # ── 5. Responsibilities ─────────────────────────────────────────────────
    responsibilities: List[str] = Field(
        default_factory=list,
        description="What the role entails (bullet points from the JD).",
    )

    # ── 6. Qualifications ───────────────────────────────────────────────────
    qualifications: List[str] = Field(
        default_factory=list,
        description=(
            "Formal qualification requirements. For this JD these are implicit "
            "(no degree requirement stated) so derived from context."
        ),
    )

    # ── 7. Preferred locations ──────────────────────────────────────────────
    preferred_locations: List[str] = Field(
        default_factory=list,
        description="Normalised preferred work location strings.",
    )
    relocation_open: bool = Field(
        default=False,
        description="True if the role is open to relocation candidates.",
    )
    visa_sponsorship: bool = Field(
        default=False,
        description="True if the employer sponsors work visas.",
    )

    # ── 8. Preferred company types ──────────────────────────────────────────
    preferred_company_types: List[str] = Field(
        default_factory=list,
        description="e.g. ['Product company', 'Startup', 'Series A'].",
    )
    disqualified_company_types: List[str] = Field(
        default_factory=list,
        description="e.g. ['TCS', 'Infosys', 'Wipro', 'Accenture', 'Cognizant', 'Capgemini'].",
    )

    # ── 9. Behavioral expectations ──────────────────────────────────────────
    behavioral_expectations: List[str] = Field(
        default_factory=list,
        description=(
            "Soft expectations about how the person operates "
            "(async-first, ships fast, writes clearly, etc.)."
        ),
    )

    # ── 10. Salary ──────────────────────────────────────────────────────────
    salary: Optional[SalaryRange] = Field(
        None,
        description="Salary range if stated. None if not disclosed in the JD.",
    )

    # ── 11. Notice period ───────────────────────────────────────────────────
    notice_period: NoticePeriod = Field(
        ..., description="Parsed notice period expectation."
    )

    # ── 12. Work mode ───────────────────────────────────────────────────────
    work_mode: str = Field(
        ...,
        description="Normalised work mode: 'Remote' | 'Hybrid' | 'Onsite' | 'Flexible'.",
    )
    in_office_cadence: Optional[str] = Field(
        None,
        description="Any specific cadence mentioned (e.g. 'Tue/Thu in office').",
    )

    # ── 13. Keywords ────────────────────────────────────────────────────────
    keywords: List[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, lowercased domain keywords extracted from the full JD. "
            "Used for BM25 / keyword matching by downstream modules."
        ),
    )

    # ── 14. AI technologies ─────────────────────────────────────────────────
    ai_technologies: List[str] = Field(
        default_factory=list,
        description=(
            "Specific AI/ML tools, frameworks, and models mentioned: "
            "e.g. sentence-transformers, BGE, FAISS, Pinecone, LoRA …"
        ),
    )

    # ── 15. Evaluation metrics ──────────────────────────────────────────────
    evaluation_metrics: List[str] = Field(
        default_factory=list,
        description=(
            "Ranking/retrieval evaluation metrics explicitly mentioned: "
            "e.g. NDCG, MRR, MAP, P@10 …"
        ),
    )

    # ── 16. Soft skills ─────────────────────────────────────────────────────
    soft_skills: List[str] = Field(
        default_factory=list,
        description=(
            "Interpersonal / behavioural soft skills inferred from the JD text: "
            "e.g. 'Technical writing', 'Mentoring', 'Product thinking' …"
        ),
    )

    # ── 17. Ideal candidate summary (derived) ───────────────────────────────
    ideal_candidate_notes: List[str] = Field(
        default_factory=list,
        description=(
            "Key attributes of the 'ideal candidate' as stated in the JD's "
            "'How to read between the lines' section."
        ),
    )

    # ── 18. Raw metadata ────────────────────────────────────────────────────
    source_file: Optional[str] = Field(
        None, description="Filename of the source document."
    )

    # ────────────────────────────────────────────────────────────────────────
    # Validators
    # ────────────────────────────────────────────────────────────────────────

    @field_validator("required_skills")
    @classmethod
    def _required_not_empty(cls, v: List[SkillItem]) -> List[SkillItem]:
        if not v:
            raise ValueError("required_skills cannot be empty.")
        return v

    @field_validator("required_skills", "preferred_skills", mode="before")
    @classmethod
    def _deduplicate_skills(cls, v: Any) -> Any:
        """Remove duplicate skill entries (keyed on canonical)."""
        if not isinstance(v, list):
            return v
        seen: Set[str] = set()
        unique: List[Any] = []
        for item in v:
            key: str
            if isinstance(item, dict):
                key = item.get("canonical", item.get("original", "")).strip().lower()
            elif isinstance(item, SkillItem):
                key = item.canonical
            else:
                key = str(item).strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    @field_validator("keywords", "ai_technologies", "evaluation_metrics", "soft_skills", mode="before")
    @classmethod
    def _deduplicate_strings(cls, v: Any) -> Any:
        """Deduplicate plain string lists while preserving order."""
        if not isinstance(v, list):
            return v
        seen: Set[str] = set()
        unique: List[str] = []
        for item in v:
            key = str(item).strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    @field_validator("work_mode")
    @classmethod
    def _normalise_work_mode(cls, v: str) -> str:
        v_lower = v.strip().lower()
        mapping = {
            "remote": "Remote",
            "hybrid": "Hybrid",
            "onsite": "Onsite",
            "on-site": "Onsite",
            "flexible": "Flexible",
            "flex": "Flexible",
        }
        for key, normalised in mapping.items():
            if key in v_lower:
                return normalised
        return v.strip().title()

    # ────────────────────────────────────────────────────────────────────────
    # Helper methods
    # ────────────────────────────────────────────────────────────────────────

    def required_skill_count(self) -> int:
        """Return the number of required skills."""
        return len(self.required_skills)

    def has_skill(self, name: str) -> bool:
        """
        Return True if *name* appears in either required or preferred skills.

        Matching is case-insensitive and handles partial canonical matches.

        Parameters
        ----------
        name:
            Skill name to look up (e.g. "pinecone", "NDCG", "Python").
        """
        needle = name.strip().lower()
        all_skills = self.required_skills + self.preferred_skills
        for skill in all_skills:
            if needle in skill.canonical or skill.canonical in needle:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a plain Python dict representation of this JobProfile.

        Uses Pydantic's model_dump() so nested models are also serialised.
        """
        return self.model_dump()

    def summary(self) -> str:
        """
        Return a concise multi-line textual summary of the job profile.

        This is printed by the parser after a successful parse.
        """
        req_skills = ", ".join(s.original for s in self.required_skills)
        pref_skills = ", ".join(s.original for s in self.preferred_skills)
        locs = ", ".join(self.preferred_locations)
        techs = ", ".join(self.ai_technologies)
        metrics = ", ".join(self.evaluation_metrics)

        np = self.notice_period
        np_str = (
            f"Preferred <={np.preferred_max_days}d"
            if np.preferred_max_days is not None
            else "Not specified"
        )
        if np.buyout_available and np.buyout_max_days:
            np_str += f" (buyout up to {np.buyout_max_days}d)"

        salary_str = "Not disclosed"
        if self.salary and (self.salary.min_lpa or self.salary.max_lpa):
            salary_str = (
                f"{self.salary.min_lpa}–{self.salary.max_lpa} LPA "
                f"({self.salary.currency})"
            )

        lines = [
            "",
            "=" * 60,
            "  ## Job Summary",
            "=" * 60,
            f"  Title            : {self.job_title}",
            f"  Company          : {self.company}",
            f"  Department       : {self.department or 'Not stated'}",
            f"  Experience       : {self.experience}",
            f"  Work Mode        : {self.work_mode}",
            f"  Locations        : {locs or 'Not specified'}",
            f"  Notice Period    : {np_str}",
            f"  Salary           : {salary_str}",
            f"  Required Skills  : {req_skills}",
            f"  Preferred Skills : {pref_skills or 'None stated'}",
            f"  Technologies     : {techs or 'None stated'}",
            f"  Eval Metrics     : {metrics or 'None stated'}",
            f"  Soft Skills      : {', '.join(self.soft_skills) or 'None stated'}",
            "=" * 60,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "ExperienceRange",
    "SkillItem",
    "SalaryRange",
    "NoticePeriod",
    "JobProfile",
]
