# AI Candidate Discovery & Ranking System — Comprehensive Dataset Analysis Report

> **Prepared by:** Senior AI Engineering Analysis
> **Date:** 2026-06-25
> **Scope:** Full inspection of all datasets, schema, documentation, signals, and submission specifications for the Redrob Hackathon — Intelligent Candidate Discovery & Ranking Challenge.

---

## Table of Contents

1. [Every Dataset and Its Purpose](#1-every-dataset-and-its-purpose)
2. [Every Column and What It Represents](#2-every-column-and-what-it-represents)
3. [Relationships Between Datasets](#3-relationships-between-datasets)
4. [Candidate Profile Structure](#4-candidate-profile-structure)
5. [Job Description Structure](#5-job-description-structure)
6. [Redrob Signal Fields](#6-redrob-signal-fields)
7. [Missing Values](#7-missing-values)
8. [Duplicate Records](#8-duplicate-records)
9. [Hidden Evaluation Hints](#9-hidden-evaluation-hints)
10. [Recommended Features for Ranking](#10-recommended-features-for-ranking)
11. [Risks and Edge Cases](#11-risks-and-edge-cases)
12. [Proposed AI Solution Architecture](#12-proposed-ai-solution-architecture)

---

## 1. Every Dataset and Its Purpose

The project contains **four data files** and **three documentation files**.

### 1.1 Data Files

| File | Size | Format | Purpose |
|------|------|--------|---------|
| `dataset/candidates.jsonl` | ~487 MB | Newline-delimited JSON | The **full 100,000-candidate pool** to be ranked against the job description. One JSON object per line. This is the primary input to the ranking system. |
| `dataset/sample_candidates.json` | ~300 KB | Pretty-printed JSON array | The **first 50 candidates** extracted from candidates.jsonl for quick inspection and schema validation. Identical schema to the full file. |
| `dataset/candidate_schema.json` | 8.8 KB | JSON Schema (Draft-07) | **Formal schema contract** for a single candidate record. Defines all required fields, types, enums, and validation constraints. |
| `dataset/job_description.docx` | 40 KB | DOCX | The **target job description** that all 100,000 candidates must be ranked against. Describes a Senior AI/ML Engineer role at Redrob. |
| `outputs/sample_submission.csv` | 9.2 KB | CSV | **Format reference only** — 100 pre-ranked candidates showing the required submission structure. Not a high-quality ranking. |

### 1.2 Documentation Files

| File | Purpose |
|------|---------|
| `docs/README.docx` | Participant bundle overview: file index, getting-started guide, key rules, trap warnings |
| `docs/redrob_signals_doc.docx` | Reference for all 23 behavioral signals: definitions, ranges, what each signal measures |
| `docs/submission_spec.docx` | Full submission requirements: CSV format, scoring formula, 5-stage evaluation pipeline, honeypot rules, compute constraints |

---

## 2. Every Column and What It Represents

### 2.1 Top-Level Candidate Object

All fields are defined in `candidate_schema.json`. The top-level object has **6 required sections** and **2 optional sections**.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `candidate_id` | string | Yes | Unique identifier. Format: `CAND_XXXXXXX` (7-digit zero-padded). Pattern: `^CAND_[0-9]{7}$` |
| `profile` | object | Yes | Core biographical and professional summary fields |
| `career_history` | array | Yes | Work history entries (1-10 jobs) |
| `education` | array | Yes | Education entries (0-5 records) |
| `skills` | array | Yes | Tagged skills with proficiency and endorsement counts |
| `redrob_signals` | object | Yes | 23 platform behavioral signals |
| `certifications` | array | No | Professional certifications (optional section) |
| `languages` | array | No | Language proficiencies (optional section) |

---

### 2.2 `profile` Object Fields

| Column | Type | Range/Enum | Description |
|--------|------|-----------|-------------|
| `anonymized_name` | string | — | Pseudonymized full name (e.g., "Ira Vora") |
| `headline` | string | — | One-line professional tagline |
| `summary` | string | — | Multi-sentence career summary (self-written tone) |
| `location` | string | — | City/region (e.g., "Gurgaon, Haryana") |
| `country` | string | — | Country of residence |
| `years_of_experience` | number | 0-50 | Total professional experience in years (decimal) |
| `current_title` | string | — | Current job title |
| `current_company` | string | — | Name of current employer |
| `current_company_size` | string (enum) | "1-10" / "11-50" / "51-200" / "201-500" / "501-1000" / "1001-5000" / "5001-10000" / "10001+" | Headcount band of current employer |
| `current_industry` | string | — | Industry of current employer |

---

### 2.3 `career_history` Array Item Fields

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| `company` | string | — | Employer name |
| `title` | string | — | Job title at this role |
| `start_date` | string (ISO date) | — | Start date of role (YYYY-MM-DD) |
| `end_date` | string or null | — | End date (null if current role) |
| `duration_months` | integer | >= 0 | Duration of tenure in months |
| `is_current` | boolean | — | True if this is the active role |
| `industry` | string | — | Industry sector of this employer |
| `company_size` | string (enum) | Same as profile | Headcount band of this employer |
| `description` | string | — | Free-text description of role responsibilities and achievements |

> [!WARNING]
> **Critical data quality issue:** `description` values are drawn from a **fixed pool of ~8 template descriptions** assigned randomly across roles. In the first 1,000 candidates alone, **425 out of ~1,000 job records** have description text that does not match the job title (e.g., a "Content Writer" role with an accounting description mentioning "month-end close"). This is a known synthetic data artifact meaning **job descriptions cannot be trusted for title-relevance matching** — only `title`, `industry`, `company_size`, and `company` fields are reliable.

---

### 2.4 `education` Array Item Fields

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| `institution` | string | — | Name of educational institution |
| `degree` | string | — | Degree type (B.Tech, M.Sc, Ph.D, MBA, etc.) |
| `field_of_study` | string | — | Academic discipline |
| `start_year` | integer | 1970-2030 | Year of enrollment |
| `end_year` | integer | 1970-2035 | Year of graduation |
| `grade` | string or null | — | GPA/percentage/class (e.g., "8.24 CGPA", "87%") — optional |
| `tier` | string (enum) | "tier_1" / "tier_2" / "tier_3" / "tier_4" / "unknown" | Redrob's internal prestige rating for the institution |

**Tier distribution (sample-50):**

| Tier | % |
|------|---|
| tier_3 | 36% (most common) |
| tier_4 | 29% |
| tier_2 | 14% |
| tier_1 | 7% (rarest) |

**Top degree fields (1,000-candidate sample):**

| Field of Study | Count |
|---|---|
| Data Science | 128 |
| Artificial Intelligence | 126 |
| Machine Learning | 123 |
| Information Technology | 122 |
| Computer Science | 114 |
| Computer Engineering | 112 |
| Statistics | 79 |
| Mathematics | 77 |
| Electronics | 72 |
| Electrical Engineering | 72 |

---

### 2.5 `skills` Array Item Fields

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| `name` | string | — | Skill name (free text, e.g., "NLP", "Python", "Milvus") |
| `proficiency` | string (enum) | "beginner" / "intermediate" / "advanced" / "expert" | Self-assessed skill level |
| `endorsements` | integer | >= 0 | Number of platform endorsements received for this skill |
| `duration_months` | integer | >= 0 | Months the candidate has used this skill |

**Proficiency distribution (1,000-candidate sample, ~9,600 skill entries):**

| Proficiency | Count | % |
|-------------|-------|---|
| intermediate | 4,645 | 48% |
| beginner | 3,814 | 40% |
| advanced | 1,138 | 12% |
| expert | 5 | <1% |

> [!NOTE]
> `expert` proficiency is extremely rare — only 5 instances across 9,600+ skill records. Treat `advanced` as the effective ceiling in practice.

---

### 2.6 `certifications` Array Item Fields

| Column | Type | Description |
|--------|------|-------------|
| `name` | string | Certification title |
| `issuer` | string | Issuing body (e.g., "AWS", "Scrum Alliance") |
| `year` | integer | Year obtained |

**Top certifications (1,000-candidate sample):**

| Certification | Count |
|---|---|
| Six Sigma Green Belt | 144 |
| Scrum Master Certified | 134 |
| AWS Certified Cloud Practitioner | 121 |
| NLP Specialization | 3 |
| Google Cloud Professional ML Engineer | 2 |
| Deep Learning Specialization | 1 |

> [!IMPORTANT]
> AI/ML-specific certifications (NLP Specialization, Deep Learning Specialization, Google Cloud ML) are **very rare** (~0.3-0.6% of candidates). Their presence is a **strong positive signal** for this specific JD.

---

### 2.7 `languages` Array Item Fields

| Column | Type | Enum | Description |
|--------|------|------|-------------|
| `language` | string | — | Language name |
| `proficiency` | string | "basic" / "conversational" / "professional" / "native" | Language proficiency level |

---

### 2.8 `sample_submission.csv` Columns

| Column | Type | Description |
|--------|------|-------------|
| `candidate_id` | string | `CAND_XXXXXXX` format |
| `rank` | integer (1-100) | Rank position, 1 = best fit |
| `score` | float | Model confidence score; must be non-increasing as rank increases |
| `reasoning` | string | 1-2 sentence natural-language justification |

---

## 3. Relationships Between Datasets

```
candidates.jsonl (100,000 records)
    |
    +-- SAME SCHEMA as sample_candidates.json (first 50 records)
    |        validated against candidate_schema.json
    |
    +-- Each candidate has a unique candidate_id: CAND_XXXXXXX
    |
    +-- Ranked against: job_description.docx
    |        (Senior AI/ML Engineer role at Redrob)
    |
    +-- Output format: sample_submission.csv
    |        (candidate_id, rank, score, reasoning -- top 100 only)
    |
    +-- Behavioral signals documented in: redrob_signals_doc.docx
         (23 platform signals in the redrob_signals object)
```

**Key linkages:**

| Relationship | Join Key | Notes |
|---|---|---|
| `candidates.jsonl` to `candidate_schema.json` | Schema validation | Every record must conform to the schema |
| `candidates.jsonl` to `sample_submission.csv` | `candidate_id` | Submission IDs must exist in the candidate pool |
| `candidates.jsonl` to `job_description.docx` | Semantic match | The ranking is against this specific JD |
| `redrob_signals_doc.docx` to `redrob_signals` object | Field names | Signal documentation maps 1:1 to JSON fields |

There is **no separate relational database** — all data for a candidate is embedded in a single JSON document (document-oriented structure).

---

## 4. Candidate Profile Structure

Each candidate record follows a **nested document model** with 6 required top-level sections:

```
CAND_XXXXXXX
+-- profile/                    <- Identity, headline, location, YoE
|   +-- anonymized_name
|   +-- headline
|   +-- summary                 <- Multi-sentence AI-generated text
|   +-- location + country
|   +-- years_of_experience
|   +-- current_title
|   +-- current_company
|   +-- current_company_size
|   +-- current_industry
|
+-- career_history[]            <- 1-10 jobs, reverse-chron expected
|   +-- company / title
|   +-- start_date / end_date / duration_months / is_current
|   +-- industry / company_size
|   +-- description (WARN: cross-contaminated, unreliable)
|
+-- education[]                 <- 0-5 entries
|   +-- institution / degree / field_of_study
|   +-- start_year / end_year
|   +-- grade (nullable)
|   +-- tier (tier_1 to tier_4 or unknown)
|
+-- skills[]                    <- Unbounded list
|   +-- name / proficiency / endorsements
|   +-- duration_months
|
+-- certifications[]            <- Optional, often empty (72% empty in sample)
|   +-- name / issuer / year
|
+-- languages[]                 <- Always present
|   +-- language / proficiency
|
+-- redrob_signals{}            <- 23 behavioral signals (see Section 6)
```

**Candidate diversity in the pool:**

| Dimension | Observed Values |
|---|---|
| Countries | India (72%), USA (8%), UAE (6%), Australia, UK, Germany, Canada |
| Experience range | 1.1 - 14.5+ years (avg ~7 years) |
| Company sizes | Dominated by 10001+ (48%), then 1001-5000 |
| Industries | IT Services (40%), Manufacturing (18%), Software (14%), Conglomerate, Fintech, Food Delivery |
| Work mode preference | Remote 32%, Hybrid 26%, Flexible 22%, Onsite 20% |
| Notice period | 30d (14%), 60d (24%), 90d (32%), 120d (18%), 150d (12%) |

---

## 5. Job Description Structure

The JD (`dataset/job_description.docx`) describes a **Senior AI/ML Engineer** role at Redrob.

### 5.1 Role Overview

- **Title:** Senior AI/ML Engineer (Intelligence Layer)
- **Mandate:** Own the intelligence layer — ranking, retrieval, and matching systems for the Redrob platform
- **Experience target:** 5-9 years stated; actual target is 4-5 years applied ML/AI at product companies
- **Location:** Pune/Noida preferred; Hyderabad, Mumbai, Delhi NCR also welcome; no visa sponsorship
- **Notice period preference:** Sub-30 days strongly preferred; can buy out up to 30 days; 30+ day candidates at higher bar

### 5.2 Absolute Requirements (Hard Skills)

| Skill | Specifics |
|---|---|
| Embeddings-based retrieval | Production experience: sentence-transformers, OpenAI embeddings, BGE, E5, or similar; including embedding drift, index refresh, retrieval-quality regression in production |
| Vector databases / hybrid search | Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS, or similar |
| Python | Strong code quality required (not just scripts) |
| Evaluation frameworks for ranking | NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation |

### 5.3 Desired Skills (Not Dealbreakers)

- LLM fine-tuning (LoRA, QLoRA, PEFT)
- Learning-to-rank models (XGBoost-based or neural)
- HR-tech, recruiting-tech, or marketplace product experience
- Distributed systems / large-scale inference optimization
- Open-source AI/ML contributions

### 5.4 Explicit Disqualifiers

| Disqualifier | Notes |
|---|---|
| Pure research background (academic labs, no production deployment) | Hard stop |
| AI experience consists only of recent (<12 months) LangChain/OpenAI projects | Hard stop unless substantial pre-LLM production ML |
| Senior engineer not writing production code in last 18 months | Role requires active coding |
| Entire career at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini) | Bad fit; prior product-company experience elsewhere is OK |
| Primary expertise: computer vision, speech, or robotics without NLP/IR exposure | Domain mismatch |
| 5+ years on closed-source systems with no external validation | Cannot assess thinking |

### 5.5 Hidden JD Signals (Read Between the Lines)

> [!IMPORTANT]
> The JD explicitly tells hackathon participants:
> - **Do not keyword-match** — "the right answer is not to find candidates whose skills section contains the most AI keywords"
> - **Career history context matters** — a candidate without "RAG" or "Pinecone" in their profile but with a recommendation system built at a product company **is a fit**
> - **A Marketing Manager with all AI keywords is NOT a fit**, regardless of skill list
> - **Behavioral signals must be weighted** — "a perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% recruiter response rate is not actually available"

### 5.6 Ideal Candidate Profile

| Attribute | Target |
|---|---|
| Total experience | 6-8 years |
| AI/ML-specific experience | 4-5 years in applied/production roles at product companies |
| What they've shipped | At least one end-to-end ranking, search, or recommendation system at meaningful scale |
| Location | Noida or Pune (or willing to relocate) |
| Platform activity | Active on Redrob with clear job-market signal |

---

## 6. Redrob Signal Fields

The `redrob_signals` object contains **23 platform behavioral signals**. All 23 are required by the schema.

### 6.1 Complete Signal Reference Table

| # | Signal Name | Type | Range | What It Measures | Ranking Relevance |
|---|---|---|---|---|---|
| 1 | `profile_completeness_score` | float | 0-100 | % of profile filled in | Proxy for candidate seriousness; avg = 55.9 in sample |
| 2 | `signup_date` | date string | — | When they joined Redrob | Derived: platform tenure |
| 3 | `last_active_date` | date string | — | Last login date | **Critical**: inactive >6 months = effectively unavailable |
| 4 | `open_to_work_flag` | boolean | — | Marked as available | 34% open to work; strong positive signal |
| 5 | `profile_views_received_30d` | integer | >= 0 | Recruiter profile views in 30 days | Market demand; avg=48, range=1-194 |
| 6 | `applications_submitted_30d` | integer | >= 0 | Recent applications sent | Job-search intent signal |
| 7 | `recruiter_response_rate` | float | 0.0-1.0 | Fraction of recruiter messages replied to | **Critical hire-ability signal**; <0.10 = effectively unresponsive; avg=0.44 |
| 8 | `avg_response_time_hours` | float | >= 0 | Median time to respond to recruiter | Lower = more hireable |
| 9 | `skill_assessment_scores` | dict | 0-100 per skill | Per-skill platform assessment scores | Objective validation; 80% have empty dict |
| 10 | `connection_count` | integer | >= 0 | Redrob connections | Network size proxy; range 19-485 |
| 11 | `endorsements_received` | integer | >= 0 | Total skill endorsements received | Social validation; range 3-50 |
| 12 | `notice_period_days` | integer | 0-180 | Stated notice period | **JD prefers <30 days**; 30+ increases bar |
| 13 | `expected_salary_range_inr_lpa` | object {min, max} | >= 0 | Expected salary (INR Lakhs/yr) | Budget fit signal; range min=4.6-27.3, max=6.7-60.2 LPA |
| 14 | `preferred_work_mode` | enum | remote/hybrid/onsite/flexible | Stated work-mode preference | Onsite/flexible preferred for Pune/Noida role |
| 15 | `willing_to_relocate` | boolean | — | Will relocate if needed | Positive for non-Pune/Noida candidates |
| 16 | `github_activity_score` | float | -1 to 100 | GitHub activity in last 12 months | -1 = no GitHub linked; positive = active open-source contributor |
| 17 | `search_appearance_30d` | integer | >= 0 | Recruiter search appearances | Market demand; avg=129, range=5-778 |
| 18 | `saved_by_recruiters_30d` | integer | >= 0 | Recruiter bookmarks in 30 days | Demand confirmation; range 1-10 |
| 19 | `interview_completion_rate` | float | 0.0-1.0 | Fraction of interviews attended | No-shows waste pipeline; avg=0.60 |
| 20 | `offer_acceptance_rate` | float | -1 to 1.0 | Historical offer acceptance rate | -1 = no prior offers; positive = accepted offers before |
| 21 | `verified_email` | boolean | — | Email address verified | Trust/authenticity signal |
| 22 | `verified_phone` | boolean | — | Phone verified | Trust/authenticity signal |
| 23 | `linkedin_connected` | boolean | — | LinkedIn account linked | Professional presence signal |

### 6.2 Signal Sentinel Values

| Signal | Sentinel Value | Correct Interpretation |
|---|---|---|
| `github_activity_score` | -1 | No GitHub account linked — treat as "unknown", NOT as zero |
| `offer_acceptance_rate` | -1 | No prior offer history on platform — treat as neutral, NOT negative |

These sentinel values must be handled during feature engineering. They are **not actual scores** and must not be averaged or used raw without imputation.

---

## 7. Missing Values

### 7.1 Structurally Optional Fields (Schema Level)

| Field | Empty Rate (sample-50) | Notes |
|---|---|---|
| `certifications` | 72% (36/50 empty arrays) | Explicitly optional in schema |
| `education[*].grade` | Partial; nullable | Some have GPA, others null |
| `education[*].tier` | Can be "unknown" | Institution not in Redrob's tier database |

### 7.2 Sentinel-Value "Missing" in redrob_signals

| Signal | Sentinel Rate (sample-50) | Sentinel |
|---|---|---|
| `github_activity_score == -1` | 66% (33/50) | No GitHub linked |
| `offer_acceptance_rate == -1` | 68% (34/50) | No prior offer history |
| `skill_assessment_scores == {}` | 80% (40/50) | No assessments taken |

### 7.3 Trust / Verification Gaps

| Signal | Rate Not Satisfied (sample-50) |
|---|---|
| `verified_email = false` | 22% |
| `verified_phone = false` | 34% |
| `linkedin_connected = false` | 66% |

### 7.4 Active Engagement Gaps

| Signal | Rate Not Satisfied |
|---|---|
| `open_to_work_flag = false` | 68% in sample-50; 65% in sample-1000 |

> [!WARNING]
> **Open-to-work is false for ~65% of candidates.** Candidates with `open_to_work_flag = false` should be significantly down-weighted — they may not respond to outreach even if technically qualified.

---

## 8. Duplicate Records

### 8.1 candidate_id Duplicates

| Check | Result |
|---|---|
| Duplicate `candidate_id` in sample-50 | **0 duplicates** |
| Expected in full 100K pool | None (schema enforces uniqueness; format validation rejects duplicate IDs) |

### 8.2 Name Duplicates

| Check | Result |
|---|---|
| Duplicate `anonymized_name` in sample-50 | 1 name appears twice — expected in synthetic data |

Name duplicates are **not duplicate records**. The `candidate_id` is the true primary key.

### 8.3 Career Description Cross-Contamination

> [!CAUTION]
> This is the most significant quality issue in the dataset. **Job descriptions in `career_history[*].description` are drawn from a small pool of ~8 fixed templates assigned randomly, regardless of job title.** In the first 1,000 candidates, **42.5% of job records** (425 checked) have descriptions that clearly don't match their job title.
>
> Observed examples:
> - "Content Writer" role with accounting description ("month-end close")
> - "Marketing Manager" role with mechanical engineering description (SolidWorks/CAD)
> - "Operations Manager" role with demand-generation marketing description
>
> **Implication:** Do not use `career_history[*].description` text for relevance matching. Use `title`, `industry`, and `duration_months` instead.

---

## 9. Hidden Evaluation Hints

### 9.1 Honeypot Candidates (~80 in the full pool)

The dataset explicitly contains **~80 honeypot candidates** with subtly impossible or incoherent profiles. These are forced to **relevance tier 0** in the ground truth. Submissions with >10% honeypots in top 100 are **disqualified at Stage 3**.

**Observed honeypot patterns (sample-50 analysis):**

| Anomaly Type | Count in Sample-50 | Examples |
|---|---|---|
| `signup_date > last_active_date` | 2 | CAND_0000006 (signed up 2026-04-26, last active 2025-02-28); CAND_0000021 |
| `expected_salary_range_inr_lpa.min > max` | 15 | CAND_0000009, 0000011-0000013, 0000015, 0000017, 0000019, 0000022, 0000026, 0000030, 0000032, 0000036, 0000039 |
| Experience at company > company's founding age | Possible | "8 years experience at company founded 3 years ago" (per spec) |
| "Expert" proficiency in 10+ skills with 0 months used | Possible | Per submission spec documentation |

> [!CAUTION]
> **15 out of 50 sample candidates (30%)** have `salary_min > salary_max`. This rate is far higher than the documented ~80 honeypots (which is ~0.08% of 100K), suggesting this particular anomaly is also partly a **data generation bug** in non-honeypot candidates. Use this as one honeypot signal among several, not as a hard exclusion criterion on its own.

### 9.2 Trap Candidate Types (per README)

| Trap Type | Description | Why It Traps Naive Systems |
|---|---|---|
| **Keyword Stuffers** | Candidates whose skills list contains every AI keyword but whose career is in an unrelated domain (e.g., Marketing Manager with "RAG", "Pinecone", "Milvus" as skills) | Naive TF-IDF or keyword matching ranks them highly |
| **Plain-Language Tier 5s** | Candidates who actually fit the JD but don't use exact technical keywords (e.g., "built a recommendation system" without saying "vector search") | Semantic understanding required to surface these |
| **Behavioral Twins** | Two candidates with identical skill/experience profiles but very different behavioral signals (one engaged, one dormant) | Tests whether system penalizes unavailable candidates |
| **Honeypots (~80)** | Profiles with logically impossible data | Tests if system reads profiles vs. just doing embedding similarity |

### 9.3 Evaluation Scoring Formula

```
Final Score = 0.50 x NDCG@10 + 0.30 x NDCG@50 + 0.15 x MAP + 0.05 x P@10
```

| Metric | Weight | Implication |
|---|---|---|
| NDCG@10 | 50% | **Top 10 positions are worth half the total score** — optimize aggressively here |
| NDCG@50 | 30% | Top 50 quality is second priority |
| MAP | 15% | Overall precision matters across all 100 ranks |
| P@10 | 5% | Getting tier-3+ candidates in the top 10 |

**Strategic implication:** Concentrate on placing the best candidates in positions 1-10. Even marginal improvements in the top-5 ordering will dominate the final score.

### 9.4 Reasoning Column Evaluation Criteria (Stage 4 Manual Review)

At Stage 4, 10 random rows from the submission are evaluated against 6 criteria:

| Check | What Is Required |
|---|---|
| Specific facts | Must reference actual data from the candidate (years, title, named skills, signal values) |
| JD connection | Must connect to specific JD requirements, not generic praise |
| Honest concerns | Must acknowledge gaps (notice period, location, etc.) where present |
| No hallucination | Every claim must be verifiable in the profile |
| Variation | 10 sampled rows must be substantively different — no templates |
| Rank consistency | Tone must match the rank position |

**What gets penalized:** Empty reasoning, all-identical strings, templated fill-in-the-name reasoning, hallucinated skills/experience, reasoning contradicting the rank.

### 9.5 Compute Constraint Architecture Signal

The 5-minute CPU-only no-network constraint is **not just a technical limit** — it signals the expected architecture: embeddings must be pre-computed offline, and the ranking step must be a fast scoring function over pre-built indexes. Per-candidate LLM API calls are architecturally disqualified.

---

## 10. Recommended Features for Ranking

### 10.1 Tier-1 Features: Skill Match (Highest Priority)

| Feature | Construction | Weight Rationale |
|---|---|---|
| Core AI skill overlap count | Count of JD-required skills present in candidate skills list | Primary discriminator |
| Advanced/Expert AI skill count | Same, filtered to proficiency >= "advanced" | Quality over quantity |
| Skill duration-weighted match | Sum of `duration_months` for matched AI skills | Depth of expertise |
| Skill assessment score (AI skills) | Mean of `skill_assessment_scores` for relevant skills (imputed if missing) | Objective validation vs. self-report |
| AI/ML-specific certification | Binary: NLP Specialization, Deep Learning Spec, or Google Cloud ML cert present | Very rare, strong signal |

**Core AI skill vocabulary to match against (from JD analysis):**
- Embeddings, sentence-transformers, BGE, E5, vector embeddings
- Pinecone, Weaviate, Qdrant, Milvus, FAISS, Elasticsearch, OpenSearch
- Ranking, retrieval, recommendation systems, search
- LLM, RAG, fine-tuning, LoRA, QLoRA, PEFT
- NDCG, MRR, MAP, A/B testing (evaluation fluency)
- Python (required), NLP

### 10.2 Tier-2 Features: Career History Quality

| Feature | Construction | Weight Rationale |
|---|---|---|
| Years in AI/ML roles | Sum of `duration_months` where title contains AI/ML/Data Science/Recommendation keywords, divided by 12 | JD targets 4-5 yrs applied ML at product companies |
| Product-company experience | Months at companies with size <= "1001-5000" and not pure consulting titles | JD explicitly disqualifies pure services backgrounds |
| Consulting-firm penalty | Binary: career entirely at TCS/Infosys/Wipro/Accenture/Cognizant/Capgemini | Hard disqualifier in JD |
| Current role seniority | Title parsing: Senior/Lead/Principal/Staff vs. Junior | Experience level proxy |
| Total years of experience | `profile.years_of_experience` (5-9 preferred) | Soft filter |

### 10.3 Tier-3 Features: Education

| Feature | Construction | Weight Rationale |
|---|---|---|
| Education tier | Best tier across all education records (tier_1 > tier_2 > tier_3 > tier_4) | Prestige signal |
| STEM field of study | Boolean: field_of_study in {CS, AI, ML, Data Science, Stats, Mathematics} | Relevant academic foundation |
| Advanced degree | Has M.Tech/M.Sc/M.E./Ph.D | Advanced training signal |

### 10.4 Tier-4 Features: Behavioral Signals (Availability Multiplier)

> [!IMPORTANT]
> The JD explicitly states that behavioral signals should act as a **multiplier/modifier on top of skill-match scoring**. They determine whether a theoretically qualified candidate is actually hireable.

| Feature | Direction | Weight Rationale |
|---|---|---|
| Days since last active (from `last_active_date`) | Penalty if >90 days | Platform recency = effective availability |
| `recruiter_response_rate` (0-1) | Positive | Critical hire-ability signal; <0.10 is effectively unresponsive |
| `open_to_work_flag` | Positive (2x multiplier if true) | Active availability signal |
| `interview_completion_rate` (0-1) | Positive | No-shows waste recruiter pipeline |
| `notice_period_days` | Penalty for >30d | JD strongly prefers <30d |
| `github_activity_score` (0-100, -1=null) | Positive bonus | Active open-source = external validation of capability |
| `profile_completeness_score` (0-100) | Positive | Serious candidates complete profiles |
| `saved_by_recruiters_30d` | Positive | Market demand confirmation |

### 10.5 Tier-5 Features: Location / Logistics

| Feature | Construction | Notes |
|---|---|---|
| Location match | `country == "India"` AND `location` contains Pune/Noida/Delhi NCR/Hyderabad/Mumbai | JD prefers India-based candidates |
| Willing to relocate | Boolean | Positive for non-Pune/Noida candidates |
| Salary fit | Range overlap with expected market band (~25-60 LPA for Senior AI Engineer) | Budget feasibility signal |

### 10.6 Honeypot Detection Features (Hard Gate)

| Feature | Check | Action |
|---|---|---|
| Salary inversion | `salary_range.min > salary_range.max` | Score penalty / flag |
| Date inversion | `signup_date > last_active_date` | Score penalty / flag |
| Duration anomaly | Sum of all `duration_months` >> `years_of_experience * 12` | Flag for review |
| Expert skill with 0 months | `proficiency == "expert"` AND `duration_months == 0` | Score penalty / flag |

---

## 11. Risks and Edge Cases

### 11.1 Career Description Cross-Contamination (~42.5% of job records)

**Risk:** Any system using `career_history[*].description` semantic embeddings will introduce massive noise into relevance scoring.
**Mitigation:** Use `title`, `industry`, `duration_months`, and `is_current` instead. If description is used at all, cross-validate against title and apply low weight.

### 11.2 Skill List Inflation (Keyword Stuffing Trap)

**Risk:** Candidates whose skills array lists AI/ML keywords with no substantive AI career history (e.g., Marketing Manager with 15 AI skills at "beginner" level).
**Mitigation:** Weight skills by `duration_months` and `proficiency`. Cross-validate skill presence against career_history titles and industries. A Marketing Manager listing "Pinecone" as a beginner skill is not a vector DB engineer.

### 11.3 Inactive but Qualified Candidates

**Risk:** A genuinely excellent AI engineer who hasn't been active on Redrob for 8 months gets buried despite being a strong skill match.
**Mitigation:** Apply behavioral signals as a **soft multiplier**, not a hard exclusion gate. Reduce score by 20-40% for inactivity rather than zeroing out.

### 11.4 Consulting-Firm Candidates with Prior Product Experience

**Risk:** The JD disqualifies candidates whose **entire** career is at TCS/Infosys/Wipro/etc., but candidates with prior product-company experience elsewhere are still in scope.
**Mitigation:** Check if consulting firms are the **only** employers across all career_history records, not just the current employer.

### 11.5 Salary Min > Max Anomalies (Honeypots + Data Bug)

**Risk:** 30% of sample-50 candidates have `salary_min > salary_max`. This rate significantly exceeds the documented ~80 honeypots, suggesting this is partly a **data generation artifact** in non-honeypot candidates.
**Mitigation:** Flag and penalize but don't automatically zero-score — use as one honeypot signal among several rather than a single hard exclusion criterion.

### 11.6 github_activity_score = -1 (66% Sentinel)

**Risk:** 66% of candidates have no GitHub linked. Using this field raw penalizes 66% for not linking GitHub, which is an unwarranted penalty.
**Mitigation:** Treat -1 as "unknown", not "zero". Apply github score as a small **positive bonus** for those who have it, not as a penalty for those who don't.

### 11.7 Offer Acceptance Rate = -1 (68% of Candidates)

**Risk:** 68% of candidates have no offer history, making this a weak discriminator for the majority.
**Mitigation:** Treat -1 as neutral (0.5), not negative. Use this signal only as a mild booster for candidates with actual offer history.

### 11.8 Empty skill_assessment_scores (80% of Candidates)

**Risk:** Assessments are objective and highly valuable when present, but 80% absence means this signal creates an unfair advantage for the lucky few who happened to take assessments.
**Mitigation:** Use assessment scores as a **bonus** for those who have them, not as a penalty for those who don't. Impute from mean proficiency level when missing.

### 11.9 Title vs. YoE Mismatch

**Risk:** Some profiles show inconsistency between `years_of_experience` and career history (e.g., "Junior ML Engineer" with 10+ years, or very senior title with only 2 years experience).
**Mitigation:** Independently compute career-derived YoE from career_history and compare to the declared value. Large discrepancies may indicate honeypots or career restarts.

### 11.10 Summary/Headline AI Keyword Inflation

**Risk:** Many candidates have boilerplate summaries like "Lately I've been curious about how AI tools could augment my work — I've experimented with ChatGPT" — suggesting AI interest without real expertise.
**Mitigation:** The profile summary is not a reliable signal for AI expertise. Summary keywords should carry less than 10% the weight of skills or career history evidence.

### 11.11 Education Field Inflation

**Risk:** The most common degree fields are Data Science (128), AI (126), ML (123) across 1,000 candidates — nearly all candidates have AI-adjacent degrees. Education field is a **weak discriminator**.
**Mitigation:** Education tier (`tier_1`/`tier_2`) and institution prestige are more differentiating than field_of_study alone.

### 11.12 Compute Constraint Failure

**Risk:** Any architecture making LLM API calls per candidate (100,000 calls) will not complete within the 5-minute CPU-only constraint. Even locally-run LLMs at the 7B-13B parameter scale will likely fail.
**Mitigation:** Pre-compute all embeddings offline before the ranking step. The ranking step itself must be a fast scoring function over pre-built feature vectors or indexes — targeting under 30 seconds for the online phase.

---

## 12. Proposed AI Solution Architecture

### 12.1 Architecture Overview

```
OFFLINE PHASE (Pre-computation — no time limit)
+---------------------------------------------------------------+
| 1. Feature Extraction Engine                                  |
|    - Parse all 100K candidates from candidates.jsonl          |
|    - Extract structured features (skills, career, signals)    |
|    - Detect and flag honeypot candidates                      |
|                                                               |
| 2. Text Embedding Engine (CPU-based model)                    |
|    - Model: BAAI/bge-small-en-v1.5 (~130MB)                  |
|    - Embed: profile.headline + profile.summary (truncated)    |
|    - Embed: career_history titles + industries (weighted)     |
|    - Embed: skills names (bag-of-words weighted)              |
|    - Store: embeddings matrix (100K x 384 dims) ~150MB        |
|                                                               |
| 3. JD Embedding                                               |
|    - Parse key sections of job_description.docx              |
|    - Embed same field structure as candidates                 |
|    - Build query vector                                       |
|                                                               |
| 4. Structured Feature Matrix                                  |
|    - Build 100K x N structured feature matrix                |
|    - Includes all features from Section 10                    |
+---------------------------------------------------------------+

ONLINE PHASE (Ranking step -- <5 min CPU, <16 GB RAM)
+---------------------------------------------------------------+
| Stage A: Hard Filter (Honeypot Removal)                       |
|    - Flag salary inversion (min > max)                        |
|    - Flag date inversion (signup > last_active)               |
|    - Flag impossible experience durations                     |
|    -> Zero-score confirmed honeypots                          |
|                                                               |
| Stage B: Semantic Similarity Score (weight: 40%)              |
|    - Load pre-computed embedding matrix                       |
|    - Cosine similarity: candidate_embedding vs jd_embedding   |
|                                                               |
| Stage C: Structured Skill Match Score (weight: 30%)           |
|    - Weighted count of JD-required skills in candidates       |
|    - Penalize consulting-only careers                         |
|    - Bonus for AI/ML certifications                           |
|                                                               |
| Stage D: Behavioral Signal Score (weight: 20%)                |
|    - Composite of 8 behavioral features                       |
|    - Recency, response rate, open_to_work, interview rate     |
|    - Notice period penalty, github bonus                      |
|                                                               |
| Stage E: Location/Logistics Score (weight: 10%)               |
|    - India preference, Pune/Noida bonus                       |
|    - Salary band overlap                                      |
|                                                               |
| Stage F: Final Composite + Top-100 Selection                  |
|    - Weighted sum of all stages                               |
|    - Sort descending, select top 100                          |
|    - Assign ranks 1-100                                       |
|    - Generate reasoning strings from feature values           |
+---------------------------------------------------------------+
```

### 12.2 Embedding Strategy

| Text Field | Embedding Weight | Justification |
|---|---|---|
| Skills (all names concatenated) | 0.40 | Primary signal: most reliable field in the dataset |
| Profile headline | 0.20 | Concise self-description of expertise |
| Profile summary (first 256 tokens) | 0.15 | Rich context but noisy (boilerplate risk) |
| Career history titles (deduped) | 0.25 | What roles they have actually held |

> [!NOTE]
> **Do NOT embed `career_history[*].description`** — 42.5% of descriptions are cross-contaminated and will pollute semantic similarity scores.

### 12.3 Recommended Local Embedding Models (CPU, <16GB RAM)

| Model | Size | Recommended Use |
|---|---|---|
| `BAAI/bge-small-en-v1.5` | ~130MB | **Primary** — fast, high quality, purpose-built for retrieval |
| `sentence-transformers/all-MiniLM-L6-v2` | ~80MB | Backup — fastest CPU inference |
| `BAAI/bge-m3` | ~570MB | Only if multilingual support is needed |

For 100K candidates at 384 dimensions: embedding matrix ~150MB (float32) — fits comfortably in memory.

### 12.4 Scoring Formula (Pseudocode)

```python
def composite_score(candidate, jd_embedding):
    # Stage A: Honeypot gate
    if candidate.honeypot_score > 0.8:
        return 0.0

    # Stage B: Semantic similarity
    semantic = cosine_similarity(candidate.embedding, jd_embedding)

    # Stage C: Structured skill match
    skill_match = (
        0.5 * normalize(candidate.core_ai_skill_count) +
        0.3 * normalize(candidate.advanced_ai_skill_count) +
        0.2 * normalize(candidate.ai_skill_duration_months)
    )

    # Stage D: Behavioral (availability multiplier)
    recency_score = exp(-candidate.days_since_last_active / 90)
    behavioral = (
        0.30 * candidate.recruiter_response_rate +
        0.25 * recency_score +
        0.20 * candidate.interview_completion_rate +
        0.15 * float(candidate.open_to_work) +
        0.10 * candidate.notice_penalty  # 1.0 if <30d, 0.8 if <60d, 0.6 if >60d
    )

    # Stage E: Location/logistics
    location = (
        0.5 * float(candidate.in_india) +
        0.3 * float(candidate.in_preferred_city or candidate.willing_to_relocate) +
        0.2 * candidate.salary_fit
    )

    # Weighted composite
    score = (
        0.40 * semantic +
        0.30 * skill_match +
        0.20 * behavioral +
        0.10 * location
    )

    # Hard penalty for consulting-only career
    if candidate.is_consulting_only:
        score *= 0.60

    # Bonuses
    score += 0.05 * candidate.github_score_norm  # 0 if -1, else score/100
    score += 0.03 * float(candidate.has_ai_certification)

    return min(score, 1.0)
```

### 12.5 Reasoning String Template

For the `reasoning` column (required for Stage 4 manual review):

```
Base template:
"{title} with {yoe}yr experience; {n} core AI skills ({top_skill_names});
 recruiter response {rr:.0%}; {days_active}d since last active;
 {location}; notice period {notice}d; {open_to_work_str}."

Concern injection rules:
- If notice_period_days > 60:     append "Concern: {notice}d notice period."
- If days_since_last_active > 90: append "Concern: inactive {days}d on platform."
- If recruiter_response_rate < 0.20: append "Concern: low recruiter response rate ({rr:.0%})."
- If is_consulting_only:          append "Note: entire career in services firms."
- If github_activity_score > 50:  append "Strong GitHub activity ({score:.0f}/100)."
```

### 12.6 Performance Estimates

| Phase | Estimated Time | Resource |
|---|---|---|
| Parse 100K JSONL records | ~20 seconds | CPU |
| Extract structured features | ~30 seconds | CPU |
| Generate 100K embeddings (bge-small) | ~3-4 minutes | CPU (batch) |
| Cosine similarity scoring | ~5 seconds | NumPy matmul |
| Sort + select top 100 | <1 second | NumPy |
| Generate reasoning strings | ~1 second | Template fill |
| **Total ranking step (embeddings pre-computed)** | **<30 seconds** | CPU |
| **Total including embedding generation** | **~4.5 minutes** | CPU |

Fits comfortably within the 5-minute compute constraint.

### 12.7 Pre-Submission Validation Checklist

| Check | Validator Rule |
|---|---|
| Exactly 100 rows (not 99, not 101) | Required — auto-rejected otherwise |
| Ranks 1-100, each appears exactly once | Required |
| Each candidate_id appears exactly once | Required |
| All candidate_ids exist in candidates.jsonl | Required |
| Scores non-increasing as rank increases | Required |
| Scores are not all identical | Required |
| File is .csv, UTF-8, correct column order | Required |
| Honeypot rate in top 100 < 10% | Stage 3 filter |
| Reasoning is specific, non-templated, non-hallucinated | Stage 4 filter |

---

## Appendix: Key Data Statistics Summary

| Statistic | Value |
|---|---|
| Total candidates in pool | 100,000 |
| Sample candidates inspected | 1,050 (50 + 1,000 from main file) |
| Total fields per candidate | 6 required sections + 2 optional |
| Total redrob behavioral signals | 23 (all required) |
| Approximate honeypots in pool | ~80 (documented in submission_spec.docx) |
| Career description cross-contamination rate | ~42.5% of job records |
| Candidates with empty skill_assessment_scores | ~80% |
| Candidates with github_activity_score = -1 | ~66% |
| Candidates with offer_acceptance_rate = -1 | ~68% |
| Candidates not open to work | ~65% |
| Most common education tier | tier_3 |
| Most common degree fields | Data Science, AI, ML, IT, CS |
| Submission scoring formula | 0.50*NDCG@10 + 0.30*NDCG@50 + 0.15*MAP + 0.05*P@10 |
| Maximum submissions allowed | 3 |
| Ranking step compute budget | 5 min CPU, 16 GB RAM, no GPU, no network |
| Salary anomaly rate (min > max) | ~30% of sample-50 candidates |
| Consulting-firm-only candidates | Unknown; TCS/Wipro/Infosys most common employers |
