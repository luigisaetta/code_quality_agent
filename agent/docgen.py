"""
File name: docgen.py
Author: Luigi Saetta
Date last modified: 2025-12-15
Python Version: 3.11

Description:
    Per-file documentation generation using an LLM. Output is written elsewhere.

    - Accepts the Python source as text (read-only input).
    - Produces a Markdown document in an output folder (no in-place edits).
    - Designed to work with an LLM returned by oci.models.get_llm().

    Supported LLM call styles (best-effort):
    - await llm.ainvoke(prompt) -> str or object with .content
    - await llm(prompt) -> str or object with .content

Usage:
    from pathlib import Path
    from oci.models import get_llm
    from agent.docgen import generate_doc_for_file

    llm = get_llm()
    await generate_doc_for_file(
        llm=llm,
        relpath=Path("pkg/module.py"),
        source=python_source_text,
        out_dir=Path("./out_docs"),
        request="Focus on public API and side effects."
    )

License:
    MIT
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import re
from langchain_core.messages import HumanMessage

from agent.docgen_prompt import DOC_PROMPT
from agent.utils import get_console_logger

logger = get_console_logger()

# ----------------------------
# Public API
# ----------------------------


@dataclass(frozen=True)
class DocGenResult:
    out_path: Path
    bytes_written: int
    model_hint: str | None = None



def ensure_dir(p: Path) -> None:
    """Create directory if needed."""
    p.mkdir(parents=True, exist_ok=True)


def safe_doc_filename(relpath: Path) -> str:
    """
    Convert "a/b/c.py" -> "a__b__c.py.md" (safe single-file output namespace).
    """
    return "__".join(relpath.parts) + ".md"


async def generate_doc_for_file(
    *,
    llm: Any,
    relpath: Path,
    source: str,
    out_dir: Path,
    request: str = "",
    prompt_template: str = DOC_PROMPT,
    max_source_chars: int = 120_000,
) -> DocGenResult:
    """
    Generate Markdown documentation for a single Python file.

    Args:
        llm: LLM object (expected to support .ainvoke(prompt) or be awaitable).
        relpath: Path relative to the scanned root (used only for labeling/output naming).
        source: Python source code text.
        out_dir: Output directory (docs will be written here).
        request: User request/goal for the documentation (e.g., "focus on security and public API").
        prompt_template: Prompt template string with {relpath}, {source}, and {request}.
        max_source_chars: Safety limit to avoid sending huge files to the LLM.

    Returns:
        DocGenResult with the output path and bytes written.

    Raises:
        ValueError: if source is empty or too large.
        RuntimeError: if LLM call fails or returns empty content.
    """
    if not source or not source.strip():
        raise ValueError(f"Empty source for {relpath}")

    # Light guardrail to avoid huge prompts; adjust as needed.
    if len(source) > max_source_chars:
        source = _truncate_source(source, max_source_chars)

    ensure_dir(out_dir)

    prompt = prompt_template.format(
        relpath=str(relpath),
        source=source,
        request=(request or "").strip(),
    )

    text, model_hint = await _call_llm_normalized(llm, prompt)
    text = _postprocess_markdown(text, relpath)

    if not text.strip():
        raise RuntimeError("LLM returned empty documentation content.")

    out_path = out_dir / safe_doc_filename(relpath)
    data = (text.rstrip() + "\n").encode("utf-8")
    out_path.write_bytes(data)

    return DocGenResult(
        out_path=out_path,
        bytes_written=len(data),
        model_hint=model_hint,
    )


# ----------------------------
# Internals
# ----------------------------


def _truncate_source(source: str, max_chars: int) -> str:
    """
    Truncate source while keeping head + tail to preserve context.
    """
    head = source[: int(max_chars * 0.65)]
    tail = source[-int(max_chars * 0.25) :]
    note = (
        "\n\n# --- TRUNCATED ---\n"
        "# The source file was truncated before being sent to the LLM.\n"
        "# Consider generating docs per-section if you need full coverage.\n"
        "# --- TRUNCATED ---\n\n"
    )
    return head + note + tail


async def _call_llm_normalized(llm: Any, prompt: str) -> tuple[str, Optional[str]]:
    """
    Call the LLM using *sync* invoke(), but keep this function async by
    running the blocking call in a worker thread.

    Returns (text, model_hint).

    Rewritten using invoke (not ainvoke) for better compatibility.
    """
    msg = [HumanMessage(content=prompt)]

    def _sync_call():
        # Prefer invoke() if available; fallback to calling the object directly.
        if hasattr(llm, "invoke"):
            return llm.invoke(msg)
        return llm(msg)

    try:
        resp = await asyncio.to_thread(_sync_call)
    except Exception as e:
        raise RuntimeError(f"LLM invocation failed: {e}") from e

    text = _extract_text(resp)
    model_hint = _extract_model_hint(resp)
    return text, model_hint


def _extract_text(resp: Any) -> str:
    """
    Normalize LLM outputs across:
    - str
    - LangChain messages (.content as str)
    - Responses-style content blocks (list of {"type": "text", "text": ...})
    - dict-like OpenAI / OCI shapes

    this version manages also Responses-style content blocks
    """

    if resp is None:
        return ""

    # 1. Plain string
    if isinstance(resp, str):
        return resp

    # 2. Responses API / LC adapters: content=[{type: "text", text: "..."}]
    content = getattr(resp, "content", None)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
        if parts:
            return "\n".join(parts)

    # 3. LangChain message: .content is str
    if isinstance(content, str):
        return content

    # 4. Dict-like payloads
    if isinstance(resp, dict):
        # Direct keys
        for k in ("content", "text", "output", "message"):
            v = resp.get(k)
            if isinstance(v, str):
                return v

        # Nested Responses-like structure
        v = _dig_for_string(resp)
        if isinstance(v, str):
            return v

    # 5. Fallback (last resort)
    return str(resp)


def _extract_model_hint(resp: Any) -> Optional[str]:
    """Best-effort model hint extraction (optional)."""
    for attr in ("model", "model_name"):
        v = getattr(resp, attr, None)
        if isinstance(v, str) and v.strip():
            return v.strip()

    if isinstance(resp, dict):
        for k in ("model", "model_name"):
            v = resp.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    return None


def _dig_for_string(obj: Any, depth: int = 0) -> Optional[str]:
    """Recursively search nested dict/list structures for a likely content string."""
    if depth > 6:
        return None

    if isinstance(obj, str):
        return obj

    if isinstance(obj, dict):
        # Prefer message.content if present
        msg = obj.get("message")
        if isinstance(msg, dict):
            c = msg.get("content")
            if isinstance(c, str):
                return c
        # Common "choices" shape
        ch = obj.get("choices")
        if isinstance(ch, list):
            for it in ch:
                s = _dig_for_string(it, depth + 1)
                if s:
                    return s
        # Generic scan
        for _, v in obj.items():
            s = _dig_for_string(v, depth + 1)
            if s:
                return s

    if isinstance(obj, list):
        for it in obj:
            s = _dig_for_string(it, depth + 1)
            if s:
                return s

    return None


def _postprocess_markdown(text: str, relpath: Path) -> str:
    """
    Minimal cleanup:
    - Ensure it starts with a title
    - Remove stray triple backticks at edges (common formatting glitches)
    """
    t = text.strip()

    # If model returns a fenced block only, unwrap once.
    t = _unwrap_single_fence(t)

    # Ensure title
    if not re.match(r"^\s*#\s+", t):
        t = f"# {relpath}\n\n" + t

    return t


def _unwrap_single_fence(t: str) -> str:
    """If the whole content is wrapped in a single ```...``` fence, unwrap it."""
    if t.startswith("```") and t.endswith("```"):
        lines = t.splitlines()
        if (
            len(lines) >= 3
            and lines[0].startswith("```")
            and lines[-1].startswith("```")
        ):
            return "\n".join(lines[1:-1]).strip()
    return t
