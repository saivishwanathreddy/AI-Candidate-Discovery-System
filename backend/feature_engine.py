"""
feature_engine.py
=================
Feature Engine — converts a CandidateRecord + JobProfile into CandidateFeatures.

The engine performs all feature extraction in a single pass per candidate:
  1. Technical features  (skill matching, domain detection, depth scores)
  2. Experience features (YoE scoring, company type, AI years)
  3. Education features  (tier, STEM, advanced degree, AI certs)
  4. Behavior features   (recency, notice period, responsiveness)
  5. Trust features      (completeness, verification, GitHub)
  6. Risk features       (honeypot signals, keyword stuffing)

The ``extract()`` method is the primary entry point.  Call ``batch_extract()``
for efficient bulk processing of many candidates.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional

# Resolve backend package path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from candidate_models import (
    BehaviorFeatures,
    CandidateFeatures,
    EducationFeatures,
    EngineConfig,
    ExperienceFeatures,
    RiskFeatures,
    TechnicalFeatures,
    TrustFeatures,
)
from feature_utils import (
    build_embedding_text,
    check_date_inverted,
    check_experience_anomaly,
    check_salary_inverted,
    compute_ai_skill_depth,
    compute_honeypot_probability,
    compute_product_company_months,
    compute_recency_score,
    days_since,
    detect_domain_skills,
    estimate_ai_years,
    has_ai_certification,
    has_leadership_role,
    has_startup_experience,
    is_consulting_only_career,
    keyword_stuffing_score,
    match_skills_against_candidate,
    notice_period_score,
    score_education,
    score_years_vs_target,
)
from logger import get_logger

log = get_logger(__name__)


class FeatureEngine:
    """
    Converts CandidateRecord + JobProfile into CandidateFeatures.

    Parameters
    ----------
    job_profile:
        The parsed JobProfile representing the recruiter's intent.
    config:
        EngineConfig with scoring weights and thresholds.
    """

    def __init__(self, job_profile: Any, config: Optional[EngineConfig] = None) -> None:
        self.job = job_profile
        self.config = config or EngineConfig()

    # ================================================================
    # Public API
    # ================================================================

    def extract(self, candidate: Any) -> CandidateFeatures:
        """
        Extract and normalise all features for a single CandidateRecord.

        Parameters
        ----------
        candidate:
            A CandidateRecord instance from data_loader.

        Returns
        -------
        CandidateFeatures
        """
        try:
            return self._extract_safe(candidate)
        except Exception as exc:
            log.warning(
                "Feature extraction failed for %s: %s",
                getattr(candidate, "candidate_id", "unknown"),
                exc,
            )
            # Return a zero-feature record so the candidate is ranked last
            return CandidateFeatures(
                candidate_id=getattr(candidate, "candidate_id", "unknown"),
                name=getattr(getattr(candidate, "profile", None), "anonymized_name", ""),
            )

    def batch_extract(
        self,
        candidates: Iterable[Any],
        log_interval: int = 500,
    ) -> List[CandidateFeatures]:
        """
        Extract features for a collection of CandidateRecord objects.

        Parameters
        ----------
        candidates:
            Iterable of CandidateRecord (typically from stream_candidates or
            load_candidates().candidates).
        log_interval:
            How often to emit a progress log message.

        Returns
        -------
        List[CandidateFeatures]
        """
        results: List[CandidateFeatures] = []
        for i, cand in enumerate(candidates, start=1):
            results.append(self.extract(cand))
            if i % log_interval == 0:
                log.info("Feature extraction: %d candidates processed", i)
        log.info("Batch feature extraction complete. Total: %d", len(results))
        return results

    # ================================================================
    # Internal extraction pipeline
    # ================================================================

    def _extract_safe(self, cand: Any) -> CandidateFeatures:
        """Full feature extraction pipeline — called inside try/except."""
        p = cand.profile
        sig = cand.redrob_signals

        # ── Technical ─────────────────────────────────────────────────
        technical = self._extract_technical(cand)

        # ── Experience ────────────────────────────────────────────────
        experience = self._extract_experience(cand)

        # ── Education ─────────────────────────────────────────────────
        education = self._extract_education(cand)

        # ── Behavior ──────────────────────────────────────────────────
        behavior = self._extract_behavior(cand, sig)

        # ── Trust ─────────────────────────────────────────────────────
        trust = self._extract_trust(cand, sig)

        # ── Risk ──────────────────────────────────────────────────────
        risk = self._extract_risk(cand)

        # ── Embedding text ────────────────────────────────────────────
        emb_text = build_embedding_text(cand)

        return CandidateFeatures(
            candidate_id=cand.candidate_id,
            name=p.anonymized_name,
            location=p.location,
            country=p.country,
            technical=technical,
            experience=experience,
            education=education,
            behavior=behavior,
            trust=trust,
            risk=risk,
            embedding_text=emb_text,
        )

    # ----------------------------------------------------------------
    # Technical
    # ----------------------------------------------------------------

    def _extract_technical(self, cand: Any) -> TechnicalFeatures:
        # Skill matching
        req_matched, req_unmatched = match_skills_against_candidate(
            self.job.required_skills, cand
        )
        pref_matched, _ = match_skills_against_candidate(
            self.job.preferred_skills, cand
        )

        n_req = max(len(self.job.required_skills), 1)
        n_pref = max(len(self.job.preferred_skills), 1)

        req_ratio = len(req_matched) / n_req
        pref_ratio = len(pref_matched) / n_pref

        # Domain detection
        domains = detect_domain_skills(cand)

        # Depth
        ai_depth = compute_ai_skill_depth(cand)
        ai_cert = has_ai_certification(cand)

        return TechnicalFeatures(
            required_skills_matched=len(req_matched),
            preferred_skills_matched=len(pref_matched),
            required_skill_match_ratio=req_ratio,
            preferred_skill_match_ratio=pref_ratio,
            has_python=domains["has_python"],
            has_ai_ml=domains["has_ai_ml"],
            has_nlp=domains["has_nlp"],
            has_llm=domains["has_llm"],
            has_embeddings=domains["has_embeddings"],
            has_retrieval=domains["has_retrieval"],
            has_vector_db=domains["has_vector_db"],
            has_backend=domains["has_backend"],
            has_mlops=domains["has_mlops"],
            has_evaluation_metrics=domains["has_evaluation_metrics"],
            ai_skill_depth_score=ai_depth,
            has_ai_certification=1.0 if ai_cert else 0.0,
            matched_required_skill_names=req_matched,
            matched_preferred_skill_names=pref_matched,
            unmatched_required_skill_names=req_unmatched,
        )

    # ----------------------------------------------------------------
    # Experience
    # ----------------------------------------------------------------

    def _extract_experience(self, cand: Any) -> ExperienceFeatures:
        p = cand.profile
        exp = self.job.experience

        total_yrs = p.years_of_experience
        ai_yrs = estimate_ai_years(cand)
        ai_ratio = ai_yrs / max(total_yrs, 0.1)

        prod_months = compute_product_company_months(cand)
        consulting_only = is_consulting_only_career(cand)
        startup_exp = has_startup_experience(cand)

        # Leadership: any current/past senior title
        leadership = has_leadership_role(p.current_title) or any(
            has_leadership_role(j.title) for j in cand.career_history
        )

        years_score = score_years_vs_target(
            total_yrs,
            exp.min_years, exp.max_years,
            exp.recommended_min, exp.recommended_max,
        )

        # Company quality: product > startup > generic > consulting-only
        if consulting_only:
            company_score = 0.25
        elif startup_exp:
            company_score = 0.70
        else:
            product_yr_bonus = min(0.30, prod_months / 120.0)
            company_score = 0.55 + product_yr_bonus

        # Career progression: did they grow in seniority?
        progression_score = 0.6
        if leadership:
            progression_score = 0.85
        if consulting_only:
            progression_score *= 0.6

        return ExperienceFeatures(
            total_years=total_yrs,
            ai_years=ai_yrs,
            ai_year_ratio=min(1.0, ai_ratio),
            product_company_months=prod_months,
            consulting_only=consulting_only,
            has_startup_experience=startup_exp,
            has_leadership_role=leadership,
            years_score=years_score,
            company_quality_score=min(1.0, company_score),
            career_progression_score=progression_score,
            current_title=p.current_title,
            current_company=p.current_company,
            current_industry=p.current_industry,
        )

    # ----------------------------------------------------------------
    # Education
    # ----------------------------------------------------------------

    def _extract_education(self, cand: Any) -> EducationFeatures:
        tier, has_stem, has_adv, ai_cert, edu_score, degree, field = score_education(cand)
        return EducationFeatures(
            best_tier=tier,
            has_stem_degree=has_stem,
            has_advanced_degree=has_adv,
            has_ai_certification=ai_cert,
            education_score=edu_score,
            highest_degree=degree,
            field_of_study=field,
        )

    # ----------------------------------------------------------------
    # Behavior
    # ----------------------------------------------------------------

    def _extract_behavior(self, cand: Any, sig: Any) -> BehaviorFeatures:
        cfg = self.config
        d_since = days_since(sig.last_active_date)
        recency = compute_recency_score(d_since, cfg.inactivity_decay_halflife_days)

        np_days = sig.notice_period_days
        np_score = notice_period_score(
            np_days,
            cfg.notice_period_preferred_days,
            cfg.notice_period_max_days,
        )

        # Offer acceptance and interview completion may be -1 (no history)
        icr = sig.interview_completion_rate
        rrr = sig.recruiter_response_rate

        # Composite behavior score
        behavior_score = (
            (0.25 * rrr)
            + (0.20 * icr)
            + (0.25 * recency)
            + (0.20 * np_score)
            + (0.10 * (1.0 if sig.open_to_work_flag else 0.0))
        )

        return BehaviorFeatures(
            open_to_work=sig.open_to_work_flag,
            recruiter_response_rate=rrr,
            interview_completion_rate=icr,
            recency_score=recency,
            notice_period_days=np_days,
            notice_period_score=np_score,
            applications_submitted_30d=sig.applications_submitted_30d,
            profile_views_30d=sig.profile_views_received_30d,
            days_since_active=d_since,
            behavior_score=min(1.0, behavior_score),
        )

    # ----------------------------------------------------------------
    # Trust
    # ----------------------------------------------------------------

    def _extract_trust(self, cand: Any, sig: Any) -> TrustFeatures:
        completeness = sig.profile_completeness_score / 100.0

        github_raw = sig.github_activity_score
        has_github = github_raw >= 0
        github_norm = (github_raw / 100.0) if has_github else 0.0

        # Verification bonus
        verify_count = sum([
            sig.verified_email,
            sig.verified_phone,
            sig.linkedin_connected,
        ])

        trust_score = (
            0.35 * completeness
            + 0.25 * (verify_count / 3.0)
            + 0.25 * github_norm
            + 0.15 * (sig.endorsements_received / max(sig.endorsements_received + 10, 10))
        )

        return TrustFeatures(
            profile_completeness=completeness,
            verified_email=sig.verified_email,
            verified_phone=sig.verified_phone,
            linkedin_connected=sig.linkedin_connected,
            github_score=github_norm,
            has_github=has_github,
            trust_score=min(1.0, trust_score),
        )

    # ----------------------------------------------------------------
    # Risk
    # ----------------------------------------------------------------

    def _extract_risk(self, cand: Any) -> RiskFeatures:
        sal_inv = check_salary_inverted(cand)
        date_inv = check_date_inverted(cand)
        exp_anom = check_experience_anomaly(cand)
        stuffing = keyword_stuffing_score(cand)
        hp_prob = compute_honeypot_probability(sal_inv, date_inv, exp_anom, stuffing)

        flags: List[str] = []
        if sal_inv:
            flags.append("salary_min > salary_max")
        if date_inv:
            flags.append("signup_date > last_active_date")
        if exp_anom:
            flags.append("career_months >> declared_yoe")
        if stuffing > 0.3:
            flags.append(f"keyword_stuffing={stuffing:.2f}")

        return RiskFeatures(
            salary_inverted=sal_inv,
            date_inverted=date_inv,
            experience_anomaly=exp_anom,
            skill_stuffing_score=stuffing,
            honeypot_probability=hp_prob,
            risk_flags=flags,
        )


__all__ = ["FeatureEngine"]
