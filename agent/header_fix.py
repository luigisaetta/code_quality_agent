"""
header_fix.py

Generate compliant header docstrings for files that fail header checks.
Outputs patch text (unified diff) to apply externally (repo is read-only).
"""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

from agent.docgen_utils import call_llm_normalized
from agent.utils import get_console_logger

REQUIRED_HEADER_FIELDS = (
    "File name:",
    "Author:",
    "Date last modified:",
    "Python Version:",
    "License:",
    "Description:",
)

HEADER_GEN_PROMPT = """
You are a senior Python engineer.

Generate a compliant Python module header as a SINGLE triple-quoted docstring.

CRITICAL REQUIREMENTS:
- Output MUST be ONLY the docstring. No markdown. No backticks. No explanation.
- The docstring MUST contain ALL required fields EXACTLY ONCE, with the exact labels:
  File name:
  Author:
  Date last modified:
  Python Version:
  License:
  Description:
- Values must be on the same line as the label, except Description which can be 1-3 lines.
- Do NOT include secrets or PII. Use placeholders if unsure.

Inputs:
- file path: {relpath}
- today's date (YYYY-MM-DD): {today}
- python version: {pyver}
- detected project license (if available): {license_hint}

Rules:
- If license_hint is not "Unknown", set the License field to exactly license_hint.
- If author is unknown, use "Unknown".

Return ONLY the docstring.
"""


logger = get_console_logger()

def _has_all_required_fields(docstring: str) -> bool:
    return all(field in docstring for field in REQUIRED_HEADER_FIELDS)


def _normalize_docstring(text: str) -> str:
    t = text.strip()

    # Strip markdown fences robustly
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()

    # Ensure triple-quoted docstring
    if not (t.startswith('"""') and t.endswith('"""')):
        inner = t.strip().strip('"').strip()
        t = '"""\n' + inner + '\n"""'

    # Normalize first/last lines ONLY (avoid corrupting body)
    lines = t.splitlines()
    if lines and lines[0].startswith('"""'):
        lines[0] = '"""'
    if lines and lines[-1].endswith('"""'):
        lines[-1] = '"""'
    t = "\n".join(lines)

    # Ensure it starts/ends exactly like a docstring block
    if not t.startswith('"""\n'):
        t = '"""\n' + t[3:].lstrip()
    if not t.endswith('\n"""'):
        t = t[:-3].rstrip() + '\n"""'

    return t.strip() + "\n"


def _fallback_header(relpath: Path, pyver: str, today: str, license_hint: str) -> str:
    lic = license_hint if license_hint and license_hint != "Unknown" else "Unknown"
    return (
        '"""\n'
        f"File name: {relpath.name}\n"
        "Author: Unknown\n"
        f"Date last modified: {today}\n"
        f"Python Version: {pyver}\n"
        f"License: {lic}\n"
        "Description:\n"
        "- Module description unavailable (auto-generated header).\n"
        '"""\n'
    )



async def generate_header_snippet(
    *,
    llm: Any,
    relpath: Path,
    license_hint: str = "Unknown",
    pyver: str = "3.11",
) -> str:
    """
    Returns ONLY the header docstring text (with trailing newline).
    """
    prompt = HEADER_GEN_PROMPT.format(
        relpath=str(relpath).replace("\\", "/"),
        today=date.today().isoformat(),
        pyver=pyver,
    )

    header: str | None = None

    for _attempt in range(3):
        text, _ = await call_llm_normalized(llm, prompt)
        candidate = _normalize_docstring(text)
        if _has_all_required_fields(candidate):
            header = candidate
            break

        # tighten prompt for retry
        prompt = HEADER_GEN_PROMPT.format(
            relpath=str(relpath).replace("\\", "/"),
            today=date.today().isoformat(),
            pyver=pyver,
            license_hint=license_hint or "Unknown",
        )

    if header is None:
        header = _fallback_header(
            relpath,
            pyver=pyver,
            today=date.today().isoformat(),
            license_hint=license_hint or "Unknown",
        )

    return header
