# `agent/docgen.py`

## Overview
- Generates per‑file Markdown documentation for a Python source file by invoking a language model (LLM).  
- Accepts the source code as a **read‑only** string and writes the resulting documentation to a separate output directory (no in‑place modifications).  
- Works with LLM objects that either expose an async `ainvoke(prompt)` method or are directly awaitable.  
- Includes safety guards: rejects empty sources, truncates overly large files, and validates that the LLM returns non‑empty content.  
- Performs minimal post‑processing on the LLM output (unwraps stray fences, ensures a top‑level title).  
- Returns a small immutable `DocGenResult` describing where the file was written and how many bytes were produced.

## Public API
| Symbol | Type | Description |
|--------|------|-------------|
| `DocGenResult` | `@dataclass(frozen=True)` | Holds `out_path: Path`, `bytes_written: int`, and optional `model_hint: str`. |
| `ensure_dir(p: Path) -> None` | function | Guarantees that a directory exists (creates it recursively if needed). |
| `safe_doc_filename(relpath: Path) -> str` | function | Turns a relative file path like `a/b/c.py` into a safe single‑file name `a__b__c.py.md`. |
| `generate_doc_for_file(*, llm, relpath, source, out_dir, request="", prompt_template=DOC_PROMPT, max_source_chars=120_000) -> DocGenResult` | async function | Core entry point – builds the prompt, calls the LLM, post‑processes the markdown, writes the file, and returns a `DocGenResult`. |

## Key Behaviors & Edge Cases
- **Empty source** → raises `ValueError`.  
- **Source > `max_source_chars`** → truncated to keep head (≈65 %) + tail (≈25 %) with a clear “TRUNCATED” notice inserted.  
- **LLM call failures** (exception or empty response) → raise `RuntimeError`.  
- **Output post‑processing**:  
  - Strips surrounding whitespace.  
  - If the whole response is wrapped in a single fenced code block (```…```), the fences are removed.  
  - Guarantees the markdown starts with a level‑1 heading; if missing, a heading containing the relative path is prepended.  
- **File naming collisions** are avoided by the `safe_doc_filename` transformation, which replaces path separators with double underscores.  
- The function is **pure** aside from filesystem side‑effects (directory creation and file write).

## Inputs / Outputs & Side Effects
| Parameter | Expected type / description |
|-----------|-----------------------------|
| `llm` | Any object supporting `await llm.ainvoke(prompt)` **or** `await llm(prompt)`. |
| `relpath` | `Path` – relative path of the source file (used for labeling and output naming). |
| `source` | `str` – full Python source code of the file. |
| `out_dir` | `Path` – directory where the generated markdown will be stored. |
| `request` | `str` (optional) – extra user instruction to steer the documentation. |
| `prompt_template` | `str` – template containing `{relpath}`, `{source}`, `{request}` placeholders (defaults to `DOC_PROMPT`). |
| `max_source_chars` | `int` – safety ceiling for the number of characters sent to the LLM. |

**Returns**: `DocGenResult` containing the absolute output path, byte count, and optional model hint.

**Side effects**:
- May create `out_dir` (and any missing parents).  
- Writes a single markdown file named via `safe_doc_filename`.  

## Usage Examples
```python
import asyncio
from pathlib import Path
from oci.models import get_llm          # <-- your LLM provider
from agent.docgen import generate_doc_for_file

async def main():
    # Load source code (could be read from disk or any other source)
    source_path = Path("my_pkg/utils.py")
    source_text = source_path.read_text(encoding="utf-8")

    llm = get_llm()                     # obtain an LLM instance
    result = await generate_doc_for_file(
        llm=llm,
        relpath=source_path.relative_to(Path.cwd()),
        source=source_text,
        out_dir=Path("./generated_docs"),
        request="Highlight public functions and any side‑effects."
    )

    print(f"Documentation written to: {result.out_path}")
    print(f"Bytes written: {result.bytes_written}")

asyncio.run(main())
```

## Risks / TODOs
- **No secrets detected** in the source file.  
- The module assumes the LLM returns plain markdown; if the model returns HTML or other formats, post‑processing may need extension.  
- `max_source_chars` is a static guard; for very large projects a more sophisticated chunking strategy could be added.  
- No explicit timeout handling for the LLM call – consider wrapping `call_llm_normalized` with a timeout in production.  
- Unit tests for edge cases (empty source, truncated output, fence‑unwrap) are recommended.
