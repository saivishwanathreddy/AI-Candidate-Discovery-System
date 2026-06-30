"""
explainability.py
=================
Explainability Engine — produces human-readable explanations for every
ranked candidate, covering all scoring dimensions.

Every RankedCandidate receives:
  - A list of ExplainabilityNote objects (per-dimension, signed impact).
  - A one-liner reasoning string suitable for the submission CSV column.

Public API
----------
    ExplainabilityEngine.explain(features, breakdown)  -> List[ExplainabilityNote]
    ExplainabilityEngine.one_liner(features, breakdown, notes) -> str
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from candidate_models import (
    CandidateFeatures,
    EngineConfig,
    ExplainabilityNote,
    ScoreBreakdown,
)
from logger import get_logger

log = get_logger(__name__)


class ExplainabilityEngine:
    """
    Generates ExplainabilityNote objects from CandidateFeatures and
    ScoreBreakdown.

    Each note specifies:
      - dimension   : which scoring area (technical, experience, …)
      - sentiment   : positive / neutral / negative
      - message     : a plain-English explanation
      - impact      : signed contribution to the final score
    """

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self.config = config or EngineConfig()

    # ================================================================
    # Main entry point
    # ================================================================

    def explain(
        self,
        features: CandidateFeatures,
        breakdown: ScoreBreakdown,
    ) -> List[ExplainabilityNote]:
        """
        Generate a list of ExplainabilityNote objects for a single candidate.
        Notes are sorted descending by |impact| so the most important reasons
        appear first.
        """
        notes: List[ExplainabilityNote] = []

        notes.extend(self._explain_semantic(features, breakdown))
        notes.extend(self._explain_technical(features, breakdown))
        notes.extend(self._explain_experience(features, breakdown))
        notes.extend(self._explain_behavior(features, breakdown))
        notes.extend(self._explain_trust(features, breakdown))
        notes.extend(self._explain_risk(features, breakdown))

        # Sort by absolute impact descending
        notes.sort(key=lambda n: abs(n.impact), reverse=True)
        return notes

    def one_liner(
        self,
        features: CandidateFeatures,
        breakdown: ScoreBreakdown,
        notes: Optional[List[ExplainabilityNote]] = None,
    ) -> str:
        """
        Produce a 1–2 sentence summary suitable for the submission CSV
        ``reasoning`` column.

        Picks the top 3 positive and top 1 negative note, then
        concatenates them into a natural sentence.
        """
        if notes is None:
            notes = self.explain(features, breakdown)

        pos = [n for n in notes if n.sentiment == "positive"][:3]
        neg = [n for n in notes if n.sentiment == "negative"][:1]

        pos_text = "; ".join(n.message for n in pos)
        neg_text = (f" Concerns: {neg[0].message}." if neg else "")

        score_str = f"{breakdown.final_score:.2f}"
        return f"Score {score_str}: {pos_text}.{neg_text}"

    # ================================================================
    # Dimension explainers
    # ================================================================

    def _explain_semantic(
        self,
        f: CandidateFeatures,
        b: ScoreBreakdown,
    ) -> List[ExplainabilityNote]:
        notes: List[ExplainabilityNote] = []
        s = b.semantic
        w = b.weights_used.get("semantic", 0.35)
        impact = round(s * w, 4)

        if s >= 0.80:
            msg = "Very high semantic similarity to the job profile"
            sentiment = "positive"
        elif s >= 0.65:
            msg = "Good semantic alignment with the job requirements"
            sentiment = "positive"
        elif s >= 0.50:
            msg = "Moderate semantic match to the job profile"
            sentiment = "neutral"
        else:
            msg = f"Low semantic similarity ({s:.0%}) — profile language diverges from JD"
            sentiment = "negative"
            impact = -impact

        notes.append(ExplainabilityNote(
            dimension="semantic",
            sentiment=sentiment,
            message=msg,
            impact=impact,
        ))
        return notes

    def _explain_technical(
        self,
        f: CandidateFeatures,
        b: ScoreBreakdown,
    ) -> List[ExplainabilityNote]:
        notes: List[ExplainabilityNote] = []
        tech = f.technical
        w = b.weights_used.get("technical", 0.30)
        t_score = b.technical
        base_impact = round(t_score * w, 4)

        # Required skills match
        n_matched = tech.required_skills_matched
        n_total   = n_matched + len(tech.unmatched_required_skill_names)
        n_total   = max(n_total, 1)

        if n_matched == n_total:
            msg = f"Matched all {n_matched} required skills"
            sentiment = "positive"
            impact = base_impact
        elif n_matched >= n_total * 0.75:
            msg = f"Matched {n_matched} of {n_total} required skills"
            sentiment = "positive"
            impact = base_impact * 0.8
        elif n_matched >= n_total * 0.5:
            msg = f"Matched {n_matched} of {n_total} required skills"
            sentiment = "neutral"
            impact = base_impact * 0.5
        else:
            missing = ", ".join(tech.unmatched_required_skill_names[:4])
            msg = f"Only {n_matched}/{n_total} required skills matched; missing: {missing}"
            sentiment = "negative"
            impact = -base_impact * 0.5

        notes.append(ExplainabilityNote(
            dimension="technical",
            sentiment=sentiment,
            message=msg,
            impact=round(impact, 4),
        ))

        # Preferred skills
        if tech.preferred_skills_matched > 0:
            pref_names = ", ".join(tech.matched_preferred_skill_names[:4])
            notes.append(ExplainabilityNote(
                dimension="technical",
                sentiment="positive",
                message=f"Also has {tech.preferred_skills_matched} preferred skill(s): {pref_names}",
                impact=round(base_impact * 0.2, 4),
            ))

        # Domain highlights
        domain_hits = [
            ("has_python", "Strong Python skills"),
            ("has_embeddings", "Embeddings / semantic search experience"),
            ("has_retrieval", "Information retrieval / ranking experience"),
            ("has_vector_db", "Vector database experience"),
            ("has_llm", "LLM / generative AI experience"),
            ("has_evaluation_metrics", "Experience with ranking evaluation metrics"),
        ]
        for attr, label in domain_hits:
            if getattr(tech, attr, 0) > 0:
                notes.append(ExplainabilityNote(
                    dimension="technical",
                    sentiment="positive",
                    message=label,
                    impact=round(base_impact * 0.08, 4),
                ))

        # AI certification
        if tech.has_ai_certification > 0:
            notes.append(ExplainabilityNote(
                dimension="technical",
                sentiment="positive",
                message="Holds an AI/ML certification",
                impact=round(base_impact * 0.05, 4),
            ))

        return notes

    def _explain_experience(
        self,
        f: CandidateFeatures,
        b: ScoreBreakdown,
    ) -> List[ExplainabilityNote]:
        notes: List[ExplainabilityNote] = []
        exp = f.experience
        w = b.weights_used.get("experience", 0.15)
        e_score = b.experience
        base_impact = round(e_score * w, 4)

        # Years of experience
        yrs = exp.total_years
        if e_score >= 0.85:
            msg = f"Experience ({yrs:.1f} yrs) closely matches target range"
            sentiment = "positive"
        elif e_score >= 0.65:
            msg = f"Experience ({yrs:.1f} yrs) is within acceptable range"
            sentiment = "neutral"
        else:
            msg = f"Experience ({yrs:.1f} yrs) may be outside the ideal range"
            sentiment = "negative"

        notes.append(ExplainabilityNote(
            dimension="experience",
            sentiment=sentiment,
            message=msg,
            impact=base_impact if sentiment != "negative" else -base_impact * 0.5,
        ))

        # AI experience
        if exp.ai_years >= 3.0:
            notes.append(ExplainabilityNote(
                dimension="experience",
                sentiment="positive",
                message=f"Strong applied AI/ML experience ({exp.ai_years:.1f} years)",
                impact=round(base_impact * 0.6, 4),
            ))
        elif exp.ai_years >= 1.0:
            notes.append(ExplainabilityNote(
                dimension="experience",
                sentiment="neutral",
                message=f"Some AI/ML experience ({exp.ai_years:.1f} years)",
                impact=round(base_impact * 0.25, 4),
            ))

        # Consulting-only penalty
        if exp.consulting_only:
            notes.append(ExplainabilityNote(
                dimension="experience",
                sentiment="negative",
                message="Entire career at consulting / services firms (negative signal for this role)",
                impact=round(-base_impact * 0.55, 4),
            ))

        # Startup experience
        if exp.has_startup_experience:
            notes.append(ExplainabilityNote(
                dimension="experience",
                sentiment="positive",
                message="Has startup / early-stage company experience",
                impact=round(base_impact * 0.15, 4),
            ))

        # Leadership
        if exp.has_leadership_role:
            notes.append(ExplainabilityNote(
                dimension="experience",
                sentiment="positive",
                message="Has held or currently holds a leadership / senior role",
                impact=round(base_impact * 0.12, 4),
            ))

        return notes

    def _explain_behavior(
        self,
        f: CandidateFeatures,
        b: ScoreBreakdown,
    ) -> List[ExplainabilityNote]:
        notes: List[ExplainabilityNote] = []
        beh = f.behavior
        w = b.weights_used.get("behavior", 0.12)
        beh_score = b.behavior
        base_impact = round(beh_score * w, 4)

        # Recruiter response rate
        rrr = beh.recruiter_response_rate
        if rrr >= 0.7:
            msg = f"Excellent recruiter response rate ({rrr:.0%})"
            sentiment = "positive"
        elif rrr >= 0.4:
            msg = f"Moderate recruiter response rate ({rrr:.0%})"
            sentiment = "neutral"
        else:
            msg = f"Low recruiter response rate ({rrr:.0%}) — may be hard to reach"
            sentiment = "negative"

        notes.append(ExplainabilityNote(
            dimension="behavior",
            sentiment=sentiment,
            message=msg,
            impact=base_impact if sentiment == "positive" else (
                base_impact * 0.5 if sentiment == "neutral" else -base_impact * 0.4
            ),
        ))

        # Recency
        days = beh.days_since_active
        if days <= 7:
            msg = "Active on platform within the last 7 days"
            sentiment = "positive"
        elif days <= 30:
            msg = f"Recently active ({days} days ago)"
            sentiment = "positive"
        elif days <= 90:
            msg = f"Last active {days} days ago"
            sentiment = "neutral"
        else:
            msg = f"Inactive for {days} days — availability uncertain"
            sentiment = "negative"

        notes.append(ExplainabilityNote(
            dimension="behavior",
            sentiment=sentiment,
            message=msg,
            impact=base_impact * 0.3 if sentiment != "negative" else -base_impact * 0.3,
        ))

        # Open to work
        if beh.open_to_work:
            notes.append(ExplainabilityNote(
                dimension="behavior",
                sentiment="positive",
                message="Actively open to work",
                impact=round(base_impact * 0.2, 4),
            ))

        # Notice period
        np_d = beh.notice_period_days
        cfg = self.config
        if np_d <= cfg.notice_period_preferred_days:
            notes.append(ExplainabilityNote(
                dimension="behavior",
                sentiment="positive",
                message=f"Short notice period ({np_d} days) — can join quickly",
                impact=round(base_impact * 0.2, 4),
            ))
        elif np_d > 90:
            notes.append(ExplainabilityNote(
                dimension="behavior",
                sentiment="negative",
                message=f"Long notice period ({np_d} days)",
                impact=round(-base_impact * 0.15, 4),
            ))

        return notes

    def _explain_trust(
        self,
        f: CandidateFeatures,
        b: ScoreBreakdown,
    ) -> List[ExplainabilityNote]:
        notes: List[ExplainabilityNote] = []
        tru = f.trust
        w = b.weights_used.get("trust", 0.08)
        base_impact = round(b.trust * w, 4)

        # Profile completeness
        if tru.profile_completeness >= 0.85:
            notes.append(ExplainabilityNote(
                dimension="trust",
                sentiment="positive",
                message=f"High profile completeness ({tru.profile_completeness:.0%})",
                impact=round(base_impact * 0.4, 4),
            ))
        elif tru.profile_completeness < 0.50:
            notes.append(ExplainabilityNote(
                dimension="trust",
                sentiment="negative",
                message=f"Low profile completeness ({tru.profile_completeness:.0%})",
                impact=round(-base_impact * 0.3, 4),
            ))

        # Verification
        verifications = sum([tru.verified_email, tru.verified_phone, tru.linkedin_connected])
        if verifications == 3:
            notes.append(ExplainabilityNote(
                dimension="trust",
                sentiment="positive",
                message="Fully verified (email, phone, LinkedIn)",
                impact=round(base_impact * 0.35, 4),
            ))
        elif verifications >= 2:
            notes.append(ExplainabilityNote(
                dimension="trust",
                sentiment="neutral",
                message=f"Partially verified ({verifications}/3 signals)",
                impact=round(base_impact * 0.15, 4),
            ))

        # GitHub
        if tru.has_github and tru.github_score >= 0.5:
            notes.append(ExplainabilityNote(
                dimension="trust",
                sentiment="positive",
                message=f"Active GitHub presence (score: {tru.github_score:.0%})",
                impact=round(base_impact * 0.25, 4),
            ))
        elif not tru.has_github:
            notes.append(ExplainabilityNote(
                dimension="trust",
                sentiment="neutral",
                message="No GitHub linked",
                impact=0.0,
            ))

        return notes

    def _explain_risk(
        self,
        f: CandidateFeatures,
        b: ScoreBreakdown,
    ) -> List[ExplainabilityNote]:
        notes: List[ExplainabilityNote] = []
        risk = f.risk
        penalty = b.risk_penalty

        if penalty == 0.0 and not risk.risk_flags:
            notes.append(ExplainabilityNote(
                dimension="risk",
                sentiment="positive",
                message="Low risk profile — no anomalies detected",
                impact=0.02,
            ))
            return notes

        if risk.honeypot_probability >= 0.7:
            notes.append(ExplainabilityNote(
                dimension="risk",
                sentiment="negative",
                message=(
                    f"High honeypot probability ({risk.honeypot_probability:.0%}). "
                    f"Flags: {'; '.join(risk.risk_flags)}"
                ),
                impact=round(-penalty, 4),
            ))
        elif risk.honeypot_probability >= 0.3:
            notes.append(ExplainabilityNote(
                dimension="risk",
                sentiment="negative",
                message=(
                    f"Moderate risk flags detected ({risk.honeypot_probability:.0%}). "
                    f"Flags: {'; '.join(risk.risk_flags)}"
                ),
                impact=round(-penalty * 0.6, 4),
            ))

        if risk.skill_stuffing_score > 0.3:
            notes.append(ExplainabilityNote(
                dimension="risk",
                sentiment="negative",
                message=(
                    f"Possible keyword stuffing (score: {risk.skill_stuffing_score:.2f}) — "
                    "AI skills listed but career history shows non-AI roles"
                ),
                impact=round(-penalty * 0.3, 4),
            ))

        return notes


__all__ = ["ExplainabilityEngine"]
