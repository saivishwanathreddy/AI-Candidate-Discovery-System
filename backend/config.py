"""
config.py
=========
Central configuration for the AI Candidate Discovery System backend.

All file paths, limits, and tuneable constants are declared here.
Import this module wherever a path or setting is needed; never hardcode
paths in business-logic files.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root  (two levels up from this file: backend/ -> project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Dataset paths
# ---------------------------------------------------------------------------
DATASET_DIR: Path = PROJECT_ROOT / "dataset"

# Primary 100 000-candidate pool (newline-delimited JSON)
CANDIDATES_JSONL: Path = DATASET_DIR / "candidates.jsonl"

# 50-candidate pretty-printed sample (used for quick smoke-tests)
SAMPLE_CANDIDATES_JSON: Path = DATASET_DIR / "sample_candidates.json"

# JSON Schema Draft-07 contract for a single candidate record
CANDIDATE_SCHEMA_JSON: Path = DATASET_DIR / "candidate_schema.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR: Path = PROJECT_ROOT / "logs"
LOG_FILE: Path = LOG_DIR / "data_loader.log"

# Python logging level for console handler  ("DEBUG" | "INFO" | "WARNING" | "ERROR")
LOG_LEVEL_CONSOLE: str = os.getenv("LOG_LEVEL_CONSOLE", "INFO")

# Python logging level for file handler
LOG_LEVEL_FILE: str = os.getenv("LOG_LEVEL_FILE", "DEBUG")

# Maximum size of each log file before rotation (bytes)
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB

# Number of backup log files to keep
LOG_BACKUP_COUNT: int = 5

# ---------------------------------------------------------------------------
# Data-loader behaviour
# ---------------------------------------------------------------------------
# Number of lines to read between progress-bar updates
# (lower = more updates, higher = slightly faster I/O)
LOADER_PROGRESS_UPDATE_INTERVAL: int = 1_000

# When True the loader validates each record against candidate_schema.json.
# Disable only for profiling / debugging when schema validation overhead matters.
LOADER_SCHEMA_VALIDATION_ENABLED: bool = True

# Maximum number of validation errors to store per invalid record before
# truncating.  Prevents pathological records from filling the log.
LOADER_MAX_ERRORS_PER_RECORD: int = 10

# File encoding for all JSON sources
FILE_ENCODING: str = "utf-8"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
__all__ = [
    "PROJECT_ROOT",
    "DATASET_DIR",
    "CANDIDATES_JSONL",
    "SAMPLE_CANDIDATES_JSON",
    "CANDIDATE_SCHEMA_JSON",
    "LOG_DIR",
    "LOG_FILE",
    "LOG_LEVEL_CONSOLE",
    "LOG_LEVEL_FILE",
    "LOG_MAX_BYTES",
    "LOG_BACKUP_COUNT",
    "LOADER_PROGRESS_UPDATE_INTERVAL",
    "LOADER_SCHEMA_VALIDATION_ENABLED",
    "LOADER_MAX_ERRORS_PER_RECORD",
    "FILE_ENCODING",
]
