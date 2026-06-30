"""
feature_utils.py
================
Pure helper functions for the Feature Engine.

No state, no side effects — all functions are safe to call from multiple
threads.  Importing this module has zero startup cost.

Contents
--------
  Skill matching        : match_skills_against_candidate
  Company classification: is_consulting_firm, is_product_company, is_startup
  Domain detection      : detect_domain_skills (Python, AI, NLP, LLM, …)
  Experience parsing    : estimate_ai_years, sum_career_months
  Education helpers     : degree_rank, is_stem_field
  Text helpers          : build_embedding_text, clean_text
  Salary helpers        : salary_inverted
  Date helpers          : days_since, compute_recency_score
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Consulting / services firm detection
# ---------------------------------------------------------------------------

CONSULTING_FIRMS: FrozenSet[str] = frozenset([
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "hcl technologies", "tech mahindra", "mphasis",
    "l&t infotech", "ltimindtree", "hexaware", "zensar", "niit technologies",
    "mindtree",  # acquired but still services-flavored
    "ibm", "deloitte", "kpmg", "ey", "ernst & young", "pwc",
    "price waterhouse", "bearingpoint", "bdo", "slalom", "booz allen",
])

PRODUCT_COMPANY_SIGNALS: FrozenSet[str] = frozenset([
    "google", "meta", "microsoft", "amazon", "apple", "netflix", "uber",
    "airbnb", "stripe", "openai", "anthropic", "deepmind", "cohere",
    "hugging face", "databricks", "snowflake", "confluent", "databricks",
    "redrob", "razorpay", "zepto", "swiggy", "zomato", "ola", "myntra",
    "paytm", "phonepe", "nykaa", "meesho", "groww", "cred",
    "flipkart", "sharechat", "unacademy", "vedantu", "lenskart",
    "delhivery", "druva", "browserstack", "freshworks", "zoho", "postman",
])

STARTUP_SIGNALS: FrozenSet[str] = frozenset([
    "seed", "series a", "series b", "early stage", "pre-ipo",
    "stealth", "venture", "startup", "incubator", "y combinator",
    "techstars", "antler",
])

SIZE_STARTUP: FrozenSet[str] = frozenset(["1-10", "11-50", "51-200"])
SIZE_MID: FrozenSet[str] = frozenset(["201-500", "501-1000"])
SIZE_LARGE: FrozenSet[str] = frozenset(["1001-5000", "5001-10000", "10001+"])

# ---------------------------------------------------------------------------
# Domain skill vocabularies
# ---------------------------------------------------------------------------

PYTHON_TERMS: FrozenSet[str] = frozenset([
    "python", "django", "flask", "fastapi", "pydantic", "asyncio", "numpy",
    "pandas", "scipy", "pytest", "poetry",
])

AI_ML_TERMS: FrozenSet[str] = frozenset([
    "machine learning", "deep learning", "neural network", "ai", "ml",
    "artificial intelligence", "model training", "model inference",
    "gradient boosting", "xgboost", "lightgbm", "catboost",
    "random forest", "decision tree", "support vector",
    "scikit-learn", "sklearn", "tensorflow", "pytorch", "keras",
    "jax", "onnx", "triton",
])

NLP_TERMS: FrozenSet[str] = frozenset([
    "nlp", "natural language processing", "text classification",
    "named entity recognition", "ner", "sentiment analysis",
    "question answering", "summarisation", "summarization",
    "text mining", "information extraction", "spacy", "nltk",
    "bert", "roberta", "gpt", "t5", "bart", "tokenization",
])

LLM_TERMS: FrozenSet[str] = frozenset([
    "llm", "large language model", "gpt", "gpt-4", "gpt-3",
    "chatgpt", "openai", "anthropic", "claude", "llama", "mistral",
    "gemini", "palm", "cohere", "fine-tuning", "fine tuning",
    "lora", "qlora", "peft", "instruction tuning", "rlhf",
    "prompt engineering", "rag", "retrieval augmented generation",
    "langchain", "llamaindex", "llm inference", "vllm", "text generation",
])

EMBEDDING_TERMS: FrozenSet[str] = frozenset([
    "embedding", "embeddings", "vector embedding", "sentence embedding",
    "sentence-transformers", "sentence transformers",
    "openai embedding", "bge", "e5", "instructor", "all-minilm",
    "dense retrieval", "bi-encoder", "cross-encoder",
    "semantic search", "semantic similarity", "cosine similarity",
])

RETRIEVAL_TERMS: FrozenSet[str] = frozenset([
    "retrieval", "information retrieval", "ir", "bm25", "tfidf", "tf-idf",
    "inverted index", "sparse retrieval", "dense retrieval",
    "hybrid search", "hybrid retrieval", "reranking", "rerank",
    "re-ranking", "passage retrieval", "document retrieval",
    "query expansion", "approximate nearest neighbor", "ann",
    "ranking", "candidate retrieval",
])

VECTOR_DB_TERMS: FrozenSet[str] = frozenset([
    "pinecone", "weaviate", "qdrant", "milvus", "faiss", "chroma",
    "opensearch", "elasticsearch", "redis", "vector database",
    "vector store", "vector db", "vector search", "ann index",
    "hnsw", "ivf", "ivfpq",
])

BACKEND_TERMS: FrozenSet[str] = frozenset([
    "backend", "api", "rest", "graphql", "grpc", "microservices",
    "distributed systems", "kafka", "rabbitmq", "redis", "postgresql",
    "mysql", "mongodb", "cassandra", "spark", "hadoop", "airflow",
    "celery", "docker", "kubernetes", "aws", "gcp", "azure",
    "cloud", "infrastructure", "devops", "ci/cd",
])

MLOPS_TERMS: FrozenSet[str] = frozenset([
    "mlops", "ml ops", "ml pipeline", "model deployment", "model serving",
    "mlflow", "kubeflow", "sagemaker", "vertex ai", "model monitoring",
    "feature store", "data pipeline", "experiment tracking",
    "model registry", "continuous training", "data drift", "concept drift",
    "a/b testing", "canary deployment", "shadow deployment",
])

EVALUATION_TERMS: FrozenSet[str] = frozenset([
    "ndcg", "mrr", "map", "precision", "recall", "f1",
    "evaluation", "metrics", "offline evaluation", "online evaluation",
    "a/b test", "a/b testing", "hit rate", "ranking metrics",
    "benchmark", "ablation", "experiment",
])

AI_CERTIFICATIONS: FrozenSet[str] = frozenset([
    "deep learning specialization", "nlp specialization",
    "machine learning specialization", "mlops specialization",
    "gcp professional ml engineer", "aws certified ml",
    "azure ai engineer", "tensorflow developer",
    "pytorch certification", "coursera ml", "fast.ai",
])

LEADERSHIP_TITLES: FrozenSet[str] = frozenset([
    "lead", "senior", "principal", "staff", "architect",
    "manager", "director", "head", "vp", "cto", "chief",
    "founding engineer", "tech lead",
])

# ---------------------------------------------------------------------------
# Helper: clean text
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalise whitespace and lowercase a string."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _token_set(text: str) -> Set[str]:
    """Tokenise text into a set of unique lowercased words (3+ chars)."""
    return set(re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower()))


# ---------------------------------------------------------------------------
# Skill matching
# ---------------------------------------------------------------------------

def _skill_text_pool(candidate_record: Any) -> str:
    """
    Build a flat searchable text blob from a CandidateRecord's:
    - skills (name + proficiency)
    - career history titles and industries
    - profile headline + summary + current_title
    - certifications
    """
    parts: List[str] = []

    # Profile
    p = candidate_record.profile
    parts.extend([
        p.headline, p.summary, p.current_title, p.current_industry,
    ])

    # Skills (name weighted by proficiency)
    prof_weight = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
    for s in candidate_record.skills:
        weight = prof_weight.get(s.proficiency, 1)
        parts.extend([s.name] * weight)

    # Career history (title + industry only — not description, which is contaminated)
    for job in candidate_record.career_history:
        parts.extend([job.title, job.industry])

    # Certifications
    for cert in candidate_record.certifications:
        parts.append(cert.name)
        parts.append(cert.issuer)

    return " ".join(parts).lower()


def match_skills_against_candidate(
    job_skills: List[Any],   # List[SkillItem] from JobProfile
    candidate_record: Any,   # CandidateRecord
) -> Tuple[List[str], List[str]]:
    """
    Match JD skill items against a candidate's profile.

    Returns
    -------
    (matched_canonical_names, unmatched_canonical_names)
    """
    pool = _skill_text_pool(candidate_record)

    matched: List[str] = []
    unmatched: List[str] = []

    for skill in job_skills:
        canonical = skill.canonical.lower()
        # Try exact substring
        if canonical in pool:
            matched.append(skill.original)
            continue
        # Try individual tokens (handles multi-word skills)
        tokens = [t for t in re.split(r"[\s/\-,]+", canonical) if len(t) > 2]
        if tokens and any(t in pool for t in tokens):
            matched.append(skill.original)
        else:
            unmatched.append(skill.original)

    return matched, unmatched


# ---------------------------------------------------------------------------
# Domain detection
# ---------------------------------------------------------------------------

def _domain_score(pool_text: str, vocab: FrozenSet[str]) -> float:
    """
    Return 1.0 if any term from vocab appears in pool_text, else 0.0.
    Uses substring matching after lowercasing.
    """
    for term in vocab:
        if term in pool_text:
            return 1.0
    return 0.0


def detect_domain_skills(candidate_record: Any) -> Dict[str, float]:
    """
    Return a dict of domain-presence flags (0.0 or 1.0) for all tracked domains.
    """
    pool = _skill_text_pool(candidate_record)
    return {
        "has_python": _domain_score(pool, PYTHON_TERMS),
        "has_ai_ml": _domain_score(pool, AI_ML_TERMS),
        "has_nlp": _domain_score(pool, NLP_TERMS),
        "has_llm": _domain_score(pool, LLM_TERMS),
        "has_embeddings": _domain_score(pool, EMBEDDING_TERMS),
        "has_retrieval": _domain_score(pool, RETRIEVAL_TERMS),
        "has_vector_db": _domain_score(pool, VECTOR_DB_TERMS),
        "has_backend": _domain_score(pool, BACKEND_TERMS),
        "has_mlops": _domain_score(pool, MLOPS_TERMS),
        "has_evaluation_metrics": _domain_score(pool, EVALUATION_TERMS),
    }


def compute_ai_skill_depth(candidate_record: Any) -> float:
    """
    Weighted depth score 0.0–1.0 based on AI-relevant skills,
    their proficiency level, and months of usage.
    """
    prof_weight = {"beginner": 0.25, "intermediate": 0.50, "advanced": 0.85, "expert": 1.0}
    ai_terms = AI_ML_TERMS | NLP_TERMS | LLM_TERMS | EMBEDDING_TERMS | RETRIEVAL_TERMS

    total_weight = 0.0
    for skill in candidate_record.skills:
        name_lower = skill.name.lower()
        if any(t in name_lower for t in ai_terms):
            p_score = prof_weight.get(skill.proficiency, 0.25)
            duration = getattr(skill, "duration_months", None) or 0
            # Duration bonus: 12+ months → +0.1 bonus, capped at 1.0
            dur_bonus = min(0.20, duration / 60.0)
            total_weight += p_score + dur_bonus

    # Normalise: assume 5 AI skills at advanced = 5*0.85 = 4.25 → score 1.0
    return min(1.0, total_weight / 4.25)


def has_ai_certification(candidate_record: Any) -> bool:
    """Return True if candidate holds at least one AI-related certification."""
    for cert in candidate_record.certifications:
        cert_lower = cert.name.lower()
        if any(ac in cert_lower for ac in AI_CERTIFICATIONS):
            return True
    return False


# ---------------------------------------------------------------------------
# Company classification
# ---------------------------------------------------------------------------

def is_consulting_firm(company_name: str) -> bool:
    """Return True if the company name matches a known consulting firm."""
    name_lower = company_name.lower().strip()
    return any(firm in name_lower for firm in CONSULTING_FIRMS)


def is_product_company(company_name: str) -> bool:
    """Return True if the company name matches a known product company."""
    name_lower = company_name.lower().strip()
    return any(signal in name_lower for signal in PRODUCT_COMPANY_SIGNALS)


def is_startup_by_size(company_size: str) -> bool:
    """Return True if company_size indicates a startup."""
    return company_size in SIZE_STARTUP


def has_leadership_role(title: str) -> bool:
    """Return True if the job title contains leadership signals."""
    title_lower = title.lower()
    return any(ldr in title_lower for ldr in LEADERSHIP_TITLES)


# ---------------------------------------------------------------------------
# Experience helpers
# ---------------------------------------------------------------------------

_AI_INDUSTRY_SIGNALS: FrozenSet[str] = frozenset([
    "ai", "artificial intelligence", "machine learning", "ml",
    "data science", "nlp", "natural language", "deep learning",
    "computer vision", "robotics", "autonomous", "intelligent",
])

_AI_TITLE_SIGNALS: FrozenSet[str] = frozenset([
    "ai", "ml", "machine learning", "data scientist", "nlp",
    "computer vision", "research scientist", "applied scientist",
    "research engineer", "ai engineer", "ml engineer",
])


def estimate_ai_years(candidate_record: Any) -> float:
    """
    Estimate the number of years in AI/ML roles from career history.

    A job counts as AI if its title or industry contains AI signals.
    Duration is in months; we convert to years.
    """
    ai_months = 0.0
    for job in candidate_record.career_history:
        title_lower = job.title.lower()
        industry_lower = job.industry.lower()
        is_ai_role = (
            any(s in title_lower for s in _AI_TITLE_SIGNALS)
            or any(s in industry_lower for s in _AI_INDUSTRY_SIGNALS)
        )
        if is_ai_role:
            ai_months += job.duration_months
    return round(ai_months / 12.0, 1)


def compute_product_company_months(candidate_record: Any) -> float:
    """
    Sum of months spent at identifiable product companies.
    """
    total = 0.0
    for job in candidate_record.career_history:
        if is_product_company(job.company) or not is_consulting_firm(job.company):
            # Heuristic: if not consulting and not tiny company, assume product-ish
            if job.company_size not in ("1-10",):
                total += job.duration_months
    return total


def is_consulting_only_career(candidate_record: Any) -> bool:
    """
    Return True if every job in the candidate's career history is at a
    known consulting / services firm.
    """
    jobs = candidate_record.career_history
    if not jobs:
        return False
    return all(is_consulting_firm(j.company) for j in jobs)


def sum_career_months(candidate_record: Any) -> float:
    """Sum all non-overlapping (we assume) job duration_months."""
    return sum(j.duration_months for j in candidate_record.career_history)


def has_startup_experience(candidate_record: Any) -> bool:
    """Return True if any role in career history was at a startup."""
    for job in candidate_record.career_history:
        if is_startup_by_size(job.company_size):
            return True
        company_lower = job.company.lower()
        if any(s in company_lower for s in STARTUP_SIGNALS):
            return True
    return False


def score_years_vs_target(
    actual_years: float,
    target_min: float,
    target_max: float,
    recommended_min: Optional[float] = None,
    recommended_max: Optional[float] = None,
) -> float:
    """
    Score how well actual_years aligns with the JD experience target.

    Uses a trapezoidal scoring function:
    - Peak score (1.0) in the recommended or target window.
    - Linear decay outside the window.
    - Penalty for significant over-shoot (too senior).
    """
    rmin = recommended_min if recommended_min is not None else target_min
    rmax = recommended_max if recommended_max is not None else target_max

    if rmin <= actual_years <= rmax:
        return 1.0

    if actual_years < rmin:
        # Under-qualified: linear decay from rmin to rmin-3 years → 0
        gap = rmin - actual_years
        return max(0.0, 1.0 - gap / max(rmin, 3.0))

    # Over-qualified: slight penalty for very senior candidates
    overshoot = actual_years - rmax
    return max(0.5, 1.0 - overshoot * 0.06)


# ---------------------------------------------------------------------------
# Education helpers
# ---------------------------------------------------------------------------

STEM_FIELDS: FrozenSet[str] = frozenset([
    "computer science", "software engineering", "electrical engineering",
    "electronics", "mathematics", "statistics", "physics",
    "information technology", "information systems", "data science",
    "artificial intelligence", "machine learning", "computational",
    "operations research", "applied mathematics",
])

ADVANCED_DEGREES: FrozenSet[str] = frozenset([
    "m.tech", "mtech", "m.e.", "me", "m.s.", "ms", "master",
    "mba", "phd", "ph.d", "doctor", "postdoc",
])


def is_stem_field(field: str) -> bool:
    """Return True if field_of_study is STEM."""
    f = field.lower()
    return any(s in f for s in STEM_FIELDS)


def degree_tier_to_int(tier: Optional[str]) -> int:
    """
    Convert education tier string to int (lower = better).
    tier_1 → 1, tier_2 → 2, …, unknown/None → 4.
    """
    mapping = {"tier_1": 1, "tier_2": 2, "tier_3": 3, "tier_4": 4}
    return mapping.get(tier or "unknown", 4)


def score_education(candidate_record: Any) -> Tuple[int, bool, bool, bool, float, str, str]:
    """
    Compute education features from a CandidateRecord.

    Returns
    -------
    (best_tier, has_stem, has_advanced, has_ai_cert, edu_score, highest_degree, field)
    """
    ed_list = candidate_record.education
    if not ed_list:
        return 4, False, False, has_ai_certification(candidate_record), 0.3, "Unknown", ""

    best_tier = 4
    has_stem = False
    has_advanced = False
    highest_degree = ""
    field_of_study = ""

    for ed in ed_list:
        tier_int = degree_tier_to_int(getattr(ed, "tier", None))
        if tier_int < best_tier:
            best_tier = tier_int
            highest_degree = ed.degree
            field_of_study = ed.field_of_study

        if is_stem_field(ed.field_of_study):
            has_stem = True

        degree_lower = ed.degree.lower()
        if any(d in degree_lower for d in ADVANCED_DEGREES):
            has_advanced = True

    ai_cert = has_ai_certification(candidate_record)

    # Score: tier contributes most, then STEM, advanced degree, cert
    tier_score = {1: 1.0, 2: 0.8, 3: 0.55, 4: 0.35}[best_tier]
    edu_score = (
        tier_score * 0.55
        + (0.20 if has_stem else 0.0)
        + (0.15 if has_advanced else 0.0)
        + (0.10 if ai_cert else 0.0)
    )
    return best_tier, has_stem, has_advanced, ai_cert, edu_score, highest_degree, field_of_study


# ---------------------------------------------------------------------------
# Date & recency helpers
# ---------------------------------------------------------------------------

def days_since(date_str: str) -> int:
    """Return days elapsed since a YYYY-MM-DD date string. Returns 999 on error."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return 999


def compute_recency_score(days: int, half_life: float = 90.0) -> float:
    """
    Exponential decay: score = exp(-ln2 * days / half_life).
    Returns 1.0 for days=0, 0.5 at half_life, approaches 0 for large days.
    """
    return math.exp(-math.log(2) * days / half_life)


def notice_period_score(
    notice_days: int,
    preferred_max: int = 30,
    absolute_max: int = 150,
) -> float:
    """
    Linear score: 1.0 if notice <= preferred_max, 0.0 if >= absolute_max.
    """
    if notice_days <= preferred_max:
        return 1.0
    if notice_days >= absolute_max:
        return 0.0
    return 1.0 - (notice_days - preferred_max) / (absolute_max - preferred_max)


# ---------------------------------------------------------------------------
# Risk / honeypot detection
# ---------------------------------------------------------------------------

def check_salary_inverted(candidate_record: Any) -> bool:
    """Return True if salary_min > salary_max (honeypot signal)."""
    try:
        salary = candidate_record.redrob_signals.expected_salary_range_inr_lpa
        return salary.min > salary.max
    except Exception:
        return False


def check_date_inverted(candidate_record: Any) -> bool:
    """Return True if signup_date > last_active_date (honeypot signal)."""
    try:
        sig = candidate_record.redrob_signals
        signup = datetime.strptime(sig.signup_date, "%Y-%m-%d").date()
        last_active = datetime.strptime(sig.last_active_date, "%Y-%m-%d").date()
        return signup > last_active
    except Exception:
        return False


def check_experience_anomaly(candidate_record: Any) -> bool:
    """
    Return True if the sum of career_history months exceeds declared
    years_of_experience by more than 2 years.
    """
    declared = candidate_record.profile.years_of_experience
    career_months = sum_career_months(candidate_record)
    career_years = career_months / 12.0
    return career_years > (declared + 2.5)


def keyword_stuffing_score(candidate_record: Any) -> float:
    """
    Score the probability of keyword-stuffing.

    High AI-domain skill count with a clearly non-AI current title/industry
    suggests stuffing.  Returns 0.0–1.0.
    """
    ai_skills = sum(
        1 for s in candidate_record.skills
        if any(t in s.name.lower() for t in AI_ML_TERMS | NLP_TERMS | LLM_TERMS)
    )
    title_lower = candidate_record.profile.current_title.lower()
    industry_lower = candidate_record.profile.current_industry.lower()

    is_ai_role_now = (
        any(s in title_lower for s in _AI_TITLE_SIGNALS)
        or any(s in industry_lower for s in _AI_INDUSTRY_SIGNALS)
    )

    if ai_skills >= 8 and not is_ai_role_now:
        return min(1.0, (ai_skills - 6) / 10.0)

    return 0.0


def compute_honeypot_probability(
    salary_inv: bool,
    date_inv: bool,
    exp_anomaly: bool,
    stuffing: float,
) -> float:
    """
    Aggregate honeypot probability from individual risk signals.
    Returns 0.0–1.0.
    """
    score = 0.0
    if salary_inv:
        score += 0.40
    if date_inv:
        score += 0.35
    if exp_anomaly:
        score += 0.15
    score += stuffing * 0.10
    return min(1.0, score)


# ---------------------------------------------------------------------------
# Embedding text builder
# ---------------------------------------------------------------------------

def build_embedding_text(candidate_record: Any) -> str:
    """
    Build a concise, information-rich text passage for embedding.

    Design choices:
    - Uses title, industry, skill names (not descriptions — contaminated).
    - Weights AI skills higher by repeating them.
    - Omits noise (location, company size, dates).
    - Keeps under ~512 tokens (MiniLM context limit).
    """
    p = candidate_record.profile
    parts: List[str] = [
        f"{p.current_title} at {p.current_company}.",
        f"{p.years_of_experience} years of experience in {p.current_industry}.",
        p.headline,
    ]

    # Top skills (sorted by endorsements desc)
    skills_sorted = sorted(
        candidate_record.skills, key=lambda s: s.endorsements, reverse=True
    )[:20]
    skill_names = ", ".join(s.name for s in skills_sorted)
    if skill_names:
        parts.append(f"Skills: {skill_names}.")

    # Career titles (not descriptions)
    titles = [j.title for j in candidate_record.career_history[:5]]
    if titles:
        parts.append(f"Career: {'; '.join(titles)}.")

    # Certifications
    certs = [c.name for c in candidate_record.certifications[:5]]
    if certs:
        parts.append(f"Certifications: {', '.join(certs)}.")

    text = " ".join(parts)
    # Truncate to ~1500 chars (safe for MiniLM 512 token limit)
    return text[:1500]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "clean_text",
    "match_skills_against_candidate",
    "detect_domain_skills",
    "compute_ai_skill_depth",
    "has_ai_certification",
    "is_consulting_firm",
    "is_product_company",
    "is_startup_by_size",
    "has_leadership_role",
    "estimate_ai_years",
    "compute_product_company_months",
    "is_consulting_only_career",
    "sum_career_months",
    "has_startup_experience",
    "score_years_vs_target",
    "is_stem_field",
    "degree_tier_to_int",
    "score_education",
    "days_since",
    "compute_recency_score",
    "notice_period_score",
    "check_salary_inverted",
    "check_date_inverted",
    "check_experience_anomaly",
    "keyword_stuffing_score",
    "compute_honeypot_probability",
    "build_embedding_text",
]
