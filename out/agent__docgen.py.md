# `agent/docgen.py`

## Overview
- Generates per‑file Markdown documentation for a Python source file using a language model (LLM).  
- Accepts the source code as a **read‑only** string and writes the resulting Markdown to a designated output directory (no in‑place modifications).  
- Works with any LLM that supports either `await llm.ainvoke(prompt)` or `await llm(prompt)`, falling back to a synchronous `invoke` call wrapped in a thread.  
- Includes safety guards: rejects empty sources, truncates overly large files, and validates that the LLM returns non‑empty content.  
- Provides a small utility to create a safe, deterministic output filename based on the relative path of the source file.  

## Public API
| Symbol | Type | Description |
|--------|------|-------------|
| `DocGenResult` | `@dataclass(frozen=True)` | Holds the result of a documentation run: output path, number of bytes written, optional model hint. |
| `ensure_dir(p: Path) -> None` | function | Guarantees that a directory exists (creates it recursively if needed). |
| `safe_doc_filename(relpath: Path) -> str` | function | Converts a relative file path like `a/b/c.py` into a safe markdown filename `a__b__c.py.md`. |
| `generate_doc_for_file(*, llm, relpath, source, out_dir, request="", prompt_template=DOC_PROMPT, max_source_chars=120_000) -> DocGenResult` | async function | Core entry point – builds the prompt, calls the LLM, post‑processes the markdown, and writes the file. |

*All other symbols (`_truncate_source`, `_call_llm_normalized`, `_extract_text`, `_extract_model_hint`, `_dig_for_string`, `_postprocess_markdown`, `_unwrap_single_fence`) are internal helpers and not intended for external import.*

## Key Behaviors and Edge Cases
- **Empty source** → raises `ValueError`.  
- **Source longer than `max_source_chars`** → truncated to keep head (≈65 %) and tail (≈25 %) with a clear “TRUNCATED” notice inserted.  
- **LLM invocation failures** → wrapped in `RuntimeError` with the original exception message.  
- **LLM returns empty or whitespace‑only content** → raises `RuntimeError`.  
- **Prompt formatting** – the template must contain `{relpath}`, `{source}`, and `{request}` placeholders; they are filled with the provided values.  
- **Markdown post‑processing** – ensures the output starts with a level‑1 heading (adds one based on the file path if missing) and unwraps a single fenced code block that some models may return.  
- **Threaded sync LLM calls** – `_call_llm_normalized` runs a potentially blocking `invoke` call inside `asyncio.to_thread` to keep the API fully async.  

## Inputs / Outputs / Side Effects
| Parameter | Meaning | Expected type |
|-----------|---------|---------------|
| `llm` | LLM client object (must support async invoke or be awaitable) | `Any` |
| `relpath` | Relative path of the source file (used for labeling & filename) | `Path` |
| `source` | Full Python source code as a string | `str` |
| `out_dir` | Directory where the markdown file will be written | `Path` |
| `request` | Optional user instruction to steer the documentation (e.g., “focus on public API”) | `str` |
| `prompt_template` | Prompt template containing placeholders | `str` |
| `max_source_chars` | Upper bound on characters sent to the LLM | `int` |

**Returns**: `DocGenResult` containing the absolute output path, byte count, and optional model hint.  

**Side effects**:  
- Creates `out_dir` if it does not exist.  
- Writes a markdown file named via `safe_doc_filename(relpath)` inside `out_dir`.  

## Usage Examples
```python
import asyncio
from pathlib import Path
from oci.models import get_llm          # OCI‑specific LLM provider
from agent.docgen import generate_doc_for_file

async def main():
    llm = get_llm()                     # obtain an LLM instance
    source_path = Path("my_pkg/utils.py")
    source_text = source_path.read_text(encoding="utf-8")

    result = await generate_doc_for_file(
        llm=llm,
        relpath=source_path,
        source=source_text,
        out_dir=Path("./generated_docs"),
        request="Summarize public functions and note any side effects."
    )

    print(f"Documentation written to: {result.out_path}")
    print(f"Bytes written: {result.bytes_written}")
    if result.model_hint:
        print(f"Model hint: {result.model_hint}")

asyncio.run(main())
```

## Risks / TODOs
- **No secrets detected** in the source file.  
- The module assumes the LLM returns text in one of the handled formats; exotic response shapes may need additional extraction logic.  
- Truncation discards middle sections of very large files – callers should consider splitting large modules into smaller logical units for better coverage.  
- No explicit timeout handling for the LLM call; a very slow model could block the async task indefinitely.  
- Logging is delegated to `agent.utils.get_console_logger`; ensure the logger configuration does not inadvertently expose sensitive information.
