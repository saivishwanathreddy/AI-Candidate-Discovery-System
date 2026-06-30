"""
ranking_engine.py
=================
Hybrid Ranking Engine — combines all scoring dimensions into a final score
and produces the ranked shortlist.

Scoring formula
---------------
    weighted_score = (
        w_sem  * semantic_score   +
        w_tech * technical_score  +
        w_exp  * experience_score +
        w_beh  * behavior_score   +
        w_tru  * trust_score
    )
    risk_penalty = honeypot_probability * risk_penalty_scale
    final_score  = weighted_score * (1 - risk_penalty)

All weights are taken from EngineConfig and auto-normalised to sum to 1.

Public API
----------
    RankingEngine.compute_technical_score(tech)   -> float
    RankingEngine.compute_experience_score(exp)   -> float
    RankingEngine.score(features)                  -> ScoreBreakdown
    RankingEngine.rank(features_list)              -> List[RankedCandidate]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from candidate_models import (
    BehaviorFeatures,
    CandidateFeatures,
    EducationFeatures,
    EngineConfig,
    ExperienceFeatures,
    RankedCandidate,
    RiskFeatures,
    ScoreBreakdown,
    TechnicalFeatures,
    TrustFeatures,
)
from explainability import ExplainabilityEngine
from logger import get_logger

log = get_logger(__name__)


class RankingEngine:
    """
    Computes the final hybrid score for each candidate and returns a ranked list.

    Parameters
    ----------
    config:
        EngineConfig with weights and thresholds.
    job_profile:
        The parsed JobProfile (used for explainability context).
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        job_profile: Optional[object] = None,
    ) -> None:
        self.config = config or EngineConfig()
        self.job = job_profile
        self._explain = ExplainabilityEngine(config=self.config)

    # ================================================================
    # Dimension scorers
    # ================================================================

    def compute_technical_score(self, tech: TechnicalFeatures) -> float:
        """
        Combine required skill match ratio, preferred skill ratio,
        domain flags, and AI skill depth into a 0–1 technical score.

        Component weights:
          required_skill_ratio   45%
          domain_presence        30%  (average of 9 domain flags)
          ai_skill_depth         15%
          preferred_ratio        10%
        """
        domain_flags = [
            tech.has_python, tech.has_ai_ml, tech.has_nlp,
            tech.has_llm, tech.has_embeddings, tech.has_retrieval,
            tech.has_vector_db, tech.has_backend, tech.has_mlops,
            tech.has_evaluation_metrics,
        ]
        domain_avg = sum(domain_flags) / max(len(domain_flags), 1)

        score = (
            0.45 * tech.required_skill_match_ratio
            + 0.30 * domain_avg
            + 0.15 * tech.ai_skill_depth_score
            + 0.10 * tech.preferred_skill_match_ratio
        )
        # Bonus for AI certification (up to +0.05)
        score += 0.05 * tech.has_ai_certification
        return min(1.0, score)

    def compute_experience_score(self, exp: ExperienceFeatures) -> float:
        """
        Combine years-vs-target, AI year ratio, company quality, and
        career progression into a 0–1 experience score.

        Component weights:
          years_score           40%
          ai_year_ratio         25%
          company_quality       20%
          career_progression    15%
        """
        score = (
            0.40 * exp.years_score
            + 0.25 * exp.ai_year_ratio
            + 0.20 * exp.company_quality_score
            + 0.15 * exp.career_progression_score
        )
        # Consulting-only penalty
        if exp.consulting_only:
            score *= 0.65
        return min(1.0, score)

    # ================================================================
    # Per-candidate scoring
    # ================================================================

    def score(self, features: CandidateFeatures) -> ScoreBreakdown:
        """
        Compute a ScoreBreakdown for a single CandidateFeatures.

        Parameters
        ----------
        features:
            A fully-populated CandidateFeatures with semantic_score set.

        Returns
        -------
        ScoreBreakdown with all dimension scores and the final_score.
        """
        cfg = self.config
        weights = cfg.normalised_weights()

        # ── Dimension scores ──────────────────────────────────────────
        semantic   = features.semantic_score
        technical  = self.compute_technical_score(features.technical)
        experience = self.compute_experience_score(features.experience)
        behavior   = features.behavior.behavior_score
        trust      = features.trust.trust_score

        # ── Weighted sum ──────────────────────────────────────────────
        raw = (
            weights["semantic"]    * semantic
            + weights["technical"] * technical
            + weights["experience"]* experience
            + weights["behavior"]  * behavior
            + weights["trust"]     * trust
        )

        # ── Risk penalty ──────────────────────────────────────────────
        hp = features.risk.honeypot_probability
        risk_penalty = hp * cfg.risk_penalty_scale
        final = max(0.0, raw * (1.0 - risk_penalty))

        return ScoreBreakdown(
            semantic=round(semantic, 4),
            technical=round(technical, 4),
            experience=round(experience, 4),
            behavior=round(behavior, 4),
            trust=round(trust, 4),
            risk_penalty=round(risk_penalty, 4),
            raw_weighted=round(raw, 4),
            final_score=round(final, 4),
            weights_used=weights,
        )

    # ================================================================
    # Ranked shortlist production
    # ================================================================

    def rank(
        self,
        features_list: List[CandidateFeatures],
    ) -> List[RankedCandidate]:
        """
        Score all candidates, sort descending by final_score, and return
        the top-K as RankedCandidate objects.

        Parameters
        ----------
        features_list:
            List of CandidateFeatures with semantic_score already attached.

        Returns
        -------
        List[RankedCandidate] of length min(top_k, len(features_list)).
        """
        log.info("Scoring %d candidates …", len(features_list))

        scored = []
        for f in features_list:
            breakdown = self.score(f)
            scored.append((f, breakdown))

        # Sort descending by final score
        scored.sort(key=lambda x: x[1].final_score, reverse=True)

        top_k = min(self.config.top_k, len(scored))
        log.info("Ranking complete. Returning top %d candidates.", top_k)

        ranked: List[RankedCandidate] = []
        for rank_pos, (features, breakdown) in enumerate(scored[:top_k], start=1):
            explanations = self._explain.explain(features, breakdown)
            reasoning = self._explain.one_liner(features, breakdown, explanations)

            ranked.append(RankedCandidate(
                rank=rank_pos,
                candidate_id=features.candidate_id,
                name=features.name,
                current_title=features.experience.current_title,
                current_company=features.experience.current_company,
                location=features.location,
                years_of_experience=features.experience.total_years,
                score=breakdown.final_score,
                reasoning=reasoning,
                score_breakdown=breakdown,
                explanations=explanations,
                features=None,  # excluded from list view for response size
            ))

        return ranked


__all__ = ["RankingEngine"]
