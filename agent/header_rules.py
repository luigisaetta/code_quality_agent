"""
File name: header_rules.py
Author: Luigi Saetta
Date last modified: 2025-12-14
Python Version: 3.11

Description:
    Header template rules and a checker for Python source files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


# Simple, practical header requirements:
# - Must contain these keys in the first N lines
REQUIRED_KEYS = [
    "File name:",
    "Author:",
    "Date last modified:",
    "Python Version:",
    "Description:",
    "License:"
]


@dataclass(frozen=True)
class HeaderCheckResult:
    ok: bool
    missing_keys: list[str]
    message: str


def check_header(source: str, *, top_lines: int = 40) -> HeaderCheckResult:
    head = "\n".join(source.splitlines()[:top_lines])
    missing = [k for k in REQUIRED_KEYS if k not in head]

    if missing:
        return HeaderCheckResult(
            ok=False,
            missing_keys=missing,
            message=f"Missing header keys in first {top_lines} lines: {missing}",
        )

    # Optional sanity checks
    if "Description:" in head:
        # Require at least something after "Description:"
        m = re.search(r"Description:\s*(.+)", head)
        if not m or not m.group(1).strip():
            return HeaderCheckResult(
                ok=False,
                missing_keys=[],
                message="Description field is present but empty.",
            )

    return HeaderCheckResult(ok=True, missing_keys=[], message="Header looks OK.")
