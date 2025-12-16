# `agent/docgen_utils.py`

## Overview
- Provides helper utilities to **normalize** and extract textual content from a wide variety of LLM response formats (plain strings, LangChain messages, OpenAI‑style dicts, Responses API blocks, etc.).
- Includes a **recursive digger** (`_dig_for_string`) that walks nested dict/list structures to locate the first plausible text string.
- Supplies a **model‑hint extractor** (`extract_model_hint`) that attempts to retrieve the model identifier from common attributes or keys.
- Offers an **async wrapper** (`call_llm_normalized`) that runs a synchronous LLM `invoke` call in a thread, returning both the extracted text and optional model hint.
- Designed to be lightweight and framework‑agnostic, only depending on `langchain_core` for the `HumanMessage` type.

## Public API
| Symbol | Purpose | Typical import |
|--------|---------|----------------|
| `extract_text(resp: Any) -> str` | Normalizes any LLM response into a plain string. | `from agent.docgen_utils import extract_text` |
| `extract_model_hint(resp: Any) -> Optional[str]` | Retrieves a model name/identifier if present. | `from agent.docgen_utils import extract_model_hint` |
| `call_llm_normalized(llm: Any, prompt: str) -> Awaitable[tuple[str, Optional[str]]]` | Async helper that sends a prompt to an LLM (via `invoke` or callable) and returns normalized text + model hint. | `from agent.docgen_utils import call_llm_normalized` |
| `_dig_for_string(obj: Any, depth: int = 0) -> Optional[str]` | Internal recursive scanner used by `extract_text`. Not part of the public contract. | *internal* |

## Key Behaviors and Edge Cases
- **Depth limit**: `_dig_for_string` stops recursing after 6 levels to avoid runaway loops on pathological payloads.
- **Responses API handling**: Detects `content` attribute that is a list of dicts with `type: "text"` and concatenates their `text` fields with newline separators.
- **LangChain messages**: If the response object has a `content` attribute that is a string, it is returned directly.
- **Dict‑shaped payloads**: Looks for top‑level keys `content`, `text`, `output`, `message`; if none match, falls back to the recursive digger.
- **Fallback**: Anything not matched is stringified via `str(resp)`, guaranteeing a non‑empty return.
- **Model hint extraction**: Checks both attribute access (`resp.model`, `resp.model_name`) and dict keys; trims whitespace and ignores empty strings.
- **Threaded sync call**: `call_llm_normalized` runs the potentially blocking `llm.invoke` (or direct call) in `asyncio.to_thread`, preserving async flow without requiring the LLM to be async‑compatible.
- **Error handling**: Any exception from the LLM call is wrapped in a `RuntimeError` with a clear message.

## Inputs / Outputs / Side Effects
| Function | Input(s) | Output | Side Effects |
|----------|----------|--------|--------------|
| `extract_text` | `resp`: any object representing an LLM response (string, dict, object with `.content`, etc.) | Normalized `str` (empty string if `resp` is `None`) | None |
| `extract_model_hint` | `resp`: same as above | `str` model identifier or `None` | None |
| `call_llm_normalized` | `llm`: LLM object exposing `invoke(msg)` or callable; `prompt`: `str` | `tuple[text: str, model_hint: Optional[str]]` | Executes LLM inference (potentially network I/O) in a background thread. |

## Usage Examples
```python
import asyncio
from agent.docgen_utils import call_llm_normalized, extract_text, extract_model_hint

# Example 1: Direct use of extract_text on a raw OpenAI‑style dict
raw_resp = {
    "choices": [
        {"message": {"content": "Hello, world!"}}
    ]
}
print(extract_text(raw_resp))          # → "Hello, world!"
print(extract_model_hint(raw_resp))    # → None

# Example 2: Async call to a LangChain LLM
async def demo():
    # `my_llm` could be any LangChain-compatible LLM instance
    text, model = await call_llm_normalized(my_llm, "Summarize the plot of *Hamlet*.")
    print("Model:", model or "unknown")
    print("Response:", text)

# Run the demo
# asyncio.run(demo())
```

## Risks / TODOs
- **No secrets detected** in the source code.
- The recursive digger has a hard‑coded depth limit (6). If future LLM payloads become deeper, the limit may need adjustment.
- `call_llm_normalized` assumes the LLM’s `invoke` method is **synchronous**; if an async `ainvoke` is provided, the wrapper will still run it in a thread, which may be sub‑optimal.
- No explicit type checking for the LLM object; passing an incompatible object will raise a runtime error. Consider adding a protocol or validation step in future revisions.
