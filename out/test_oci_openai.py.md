# `test_oci_openai.py`

## Overview
- Provides a tiny asynchronous test harness for an OCI‑based OpenAI LLM wrapper.  
- Retrieves an LLM instance via `agent.oci_models.get_llm` using the model ID from configuration.  
- Defines `_call_llm_normalized` to invoke the LLM while handling two common calling patterns (`llm.invoke` vs. an awaitable callable).  
- Executes a simple “hello” prompt in an `asyncio` event loop and prints the raw response.  
- Uses a console logger for basic diagnostic output.

## Public API
| Name | Type | Intended use |
|------|------|--------------|
| `_call_llm_normalized(llm: Any, prompt: str) -> tuple[str, Optional[str]]` | `async def` | Internal helper that normalizes LLM invocation and returns a tuple of `(text, model_hint)`. |
| `main()` | `async def` | Entry‑point used by the script to run the test prompt. |
| `llm` | `Any` | Module‑level LLM instance created at import time (not meant to be imported elsewhere). |

> **Note:** The leading underscore on `_call_llm_normalized` signals that it is intended for internal use only; the script is primarily a self‑contained test, not a reusable library.

## Key Behaviors and Edge Cases
- **Dual invocation strategy** – If the LLM object has an `ainvoke` attribute, the code calls `llm.invoke([...])`; otherwise it treats the LLM as an awaitable callable and does `await llm([...])`.  
- **Error handling** – Any exception raised during the LLM call is wrapped in a `RuntimeError` with a clear message.  
- **Normalization mismatch** – The docstring claims the function returns a `(text, model_hint)` tuple, but the implementation returns the raw response object unchanged. Callers must be aware of this discrepancy.  
- **Missing `await` for async `invoke`** – When `llm.invoke` is an async method, the current code does **not** `await` it, which could lead to a coroutine being returned instead of the actual response.  
- **Prompt packaging** – The prompt is wrapped in a `HumanMessage` from LangChain, matching the expected input shape for most LLM wrappers.  

## Inputs / Outputs and Side Effects
| Parameter | Description |
|-----------|-------------|
| `llm` | An LLM client object (could be sync, async, or a callable). |
| `prompt` | A plain‑text string that will be sent to the model. |

| Return | Description |
|--------|-------------|
| `tuple[str, Optional[str]]` (as documented) | Intended to be the generated text and an optional model hint. In practice the raw response from the LLM is returned. |

**Side effects**
- Logs an informational message (`"Invoking llm.invoke..."`) via the console logger.  
- Prints a blank line and the raw response to stdout when `main()` runs.  

## Usage Examples
```python
import asyncio
from test_oci_openai import _call_llm_normalized, llm

async def demo():
    # Simple prompt
    response = await _call_llm_normalized(llm, "What is the capital of France?")
    print("LLM response:", response)

# Run the demo
asyncio.run(demo())
```

Running the module directly (e.g., `python test_oci_openai.py`) will execute the built‑in `main()` function, which sends the prompt `"hello"` and prints the result.

## Risks / TODOs
- **Secret exposure** – No secrets, API keys, or credentials are present in the source.  
- **Docstring vs. implementation mismatch** – Update the return handling to actually produce a `(text, model_hint)` tuple or adjust the docstring accordingly.  
- **Potential missing `await`** – If `llm.invoke` is asynchronous, the call should be `await llm.invoke(...)`. Add a check for coroutine objects and await them.  
- **Hard‑coded prompt** – The script uses a static `"hello"` prompt; consider exposing the prompt via CLI arguments for more flexible testing.  
- **Module‑level LLM creation** – Instantiating the LLM at import time can be undesirable in larger applications; refactor to lazy initialization if needed.
