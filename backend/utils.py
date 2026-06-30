"""
utils.py
========
General-purpose helper utilities for the AI Candidate Discovery System backend.

This module contains pure functions with no dependencies on project-specific
business logic.  It is safe to import from any other backend module.

Functions
---------
load_json_file          – load and parse a JSON file, returning a dict/list
format_duration         – format elapsed seconds into a human-readable string
safe_get                – safely traverse nested dicts with a dotted key path
count_file_lines        – count newline-delimited lines in a (potentially large) file
bytes_to_human          – convert a byte count to a readable string (KB/MB/GB)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def load_json_file(path: Union[str, Path]) -> Any:
    """
    Load and parse a UTF-8 JSON file.

    Parameters
    ----------
    path:
        Absolute or relative path to the JSON file.

    Returns
    -------
    Parsed Python object (dict, list, …).

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    json.JSONDecodeError
        If the file content is not valid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    log.debug("Loading JSON file: %s", path)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    log.debug("Loaded JSON file successfully: %s", path)
    return data


def count_file_lines(path: Union[str, Path]) -> int:
    """
    Count the number of non-empty lines in a text file without loading
    the entire file into memory.

    This is used to pre-populate the tqdm total so the progress bar shows
    an accurate percentage from the very first record.

    Parameters
    ----------
    path:
        Path to the target file.

    Returns
    -------
    int
        Number of lines that contain at least one non-whitespace character.
    """
    path = Path(path)
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                count += 1
    return count


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_duration(seconds: float) -> str:
    """
    Format an elapsed time in seconds into a human-readable string.

    Examples
    --------
    >>> format_duration(0.5)
    '0.50s'
    >>> format_duration(75.3)
    '1m 15.30s'
    >>> format_duration(3700.0)
    '1h 1m 40.00s'
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    else:
        hours = int(seconds // 3600)
        remainder = seconds % 3600
        minutes = int(remainder // 60)
        secs = remainder % 60
        return f"{hours}h {minutes}m {secs:.2f}s"


def bytes_to_human(num_bytes: int) -> str:
    """
    Convert a byte count to a human-readable size string.

    Examples
    --------
    >>> bytes_to_human(1024)
    '1.00 KB'
    >>> bytes_to_human(1_500_000)
    '1.43 MB'
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0  # type: ignore[assignment]
    return f"{num_bytes:.2f} PB"


# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------

def safe_get(
    data: Dict[str, Any],
    dotted_key: str,
    default: Any = None,
) -> Any:
    """
    Safely traverse nested dicts using a dot-separated key path.

    Parameters
    ----------
    data:
        The root dictionary to traverse.
    dotted_key:
        A key path such as ``"profile.years_of_experience"`` or
        ``"redrob_signals.recruiter_response_rate"``.
    default:
        Value returned if any key in the path is missing or the value
        at an intermediate key is not a dict.

    Returns
    -------
    The value at the resolved path, or *default* if not found.

    Examples
    --------
    >>> safe_get({"a": {"b": 42}}, "a.b")
    42
    >>> safe_get({"a": {}}, "a.b.c", default="fallback")
    'fallback'
    """
    keys = dotted_key.split(".")
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def chunk_list(items: List[Any], size: int) -> Generator[List[Any], None, None]:
    """
    Yield successive fixed-size chunks from *items*.

    Parameters
    ----------
    items:
        Any list.
    size:
        Maximum number of elements per chunk.

    Yields
    ------
    List[Any]
        A slice of *items* of at most *size* elements.
    """
    for i in range(0, len(items), size):
        yield items[i : i + size]


# ---------------------------------------------------------------------------
# Timing context manager
# ---------------------------------------------------------------------------

class Timer:
    """
    Context manager that measures wall-clock elapsed time.

    Usage
    -----
    ::

        with Timer() as t:
            do_work()
        print(f"Elapsed: {t.elapsed_seconds:.2f}s")
    """

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed_seconds: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed_seconds = time.perf_counter() - self._start

    @property
    def human(self) -> str:
        """Return elapsed time as a formatted human-readable string."""
        return format_duration(self.elapsed_seconds)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
__all__ = [
    "load_json_file",
    "count_file_lines",
    "format_duration",
    "bytes_to_human",
    "safe_get",
    "chunk_list",
    "Timer",
]
