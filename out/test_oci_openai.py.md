# `test_oci_openai.py`

## Overview
- Provides a tiny asynchronous test harness for an OCI‑based OpenAI‑compatible LLM.  
- Retrieves an LLM instance via `agent.oci_models.get_llm` using the model identifier from configuration.  
- Normalises the call signature so it works with both LangChain‑style `invoke` methods and plain awaitable callables.  
- Logs the invocation step and surfaces any exception as a `RuntimeError`.  
- Executes a single “hello” prompt when the module is run as a script.

## Public API
| Name | Type | Description |
|------|------|-------------|
| `llm` | `Any` | The LLM instance created at import time (`get_llm(LLM_MODEL_ID, max_tokens=1024)`). |
| `_call_llm_normalized(llm: Any, prompt: str) -> tuple[str, Optional[str]]` | `async def` | Calls the supplied LLM with a prompt, handling two common invocation patterns and returning the raw response (documented as a tuple of text and optional model hint). |
| `main()` | `async def` | Simple demo coroutine that calls `_call_llm_normalized` with the hard‑coded prompt `"hello"` and prints the result. |

> **Note:** The leading underscore in `_call_llm_normalized` signals that it is intended for internal use, but it is still importable for testing or reuse.

## Key Behaviors and Edge Cases
| Situation | Behaviour |
|-----------|-----------|
| **LLM has an `ainvoke` attribute** | Calls `llm.invoke([HumanMessage(content=prompt)])` (synchronous `invoke` wrapped in an async context). |
| **LLM is an awaitable callable** | Directly awaits `llm([HumanMessage(content=prompt)])`. |
| **LLM raises any exception** | Catches the exception and re‑raises a `RuntimeError` with a concise message, preserving the original traceback (`from e`). |
| **Unexpected return shape** | The function returns whatever the LLM produced; the docstring claims a `(text, model_hint)` tuple, but the implementation forwards the raw response unchanged. Consumers must therefore inspect the actual type. |
| **Missing `HumanMessage` import** | The module already imports `HumanMessage` from `langchain_core.messages`; if the library is not installed, import will fail at module load time. |
| **`max_tokens` limit** | The LLM is instantiated with `max_tokens=1024`; callers must ensure the model respects this limit. |

## Inputs / Outputs and Side Effects
| Element | Description |
|---------|-------------|
| **Input `prompt`** | `str` – the user message to be sent to the LLM. |
| **Input `llm`** | Any object that either implements `ainvoke` or is an awaitable callable accepting a list of `HumanMessage`. |
| **Returned value** | Whatever the LLM returns (commonly a string or a LangChain response object). The type is not enforced. |
| **Side effects** | - Logs an informational message (`"Invoking llm.invoke..."`) via the console logger. <br> - Prints a blank line and the raw response to stdout when `main()` runs. |

## Usage Examples
```python
import asyncio
from test_oci_openai import _call_llm_normalized, llm

async def ask(question: str) -> str:
    # Normalised call – works with both invoke‑style and awaitable LLMs
    response = await _call_llm_normalized(llm, question)
    # Assuming the LLM returns a simple string; adapt as needed
    return response

# Simple script execution
if __name__ == "__main__":
    answer = asyncio.run(ask("What is the capital of France?"))
    print("LLM answer:", answer)
```

Running the module directly (e.g., `python test_oci_openai.py`) will execute the built‑in `main()` coroutine, printing the response to the `"hello"` prompt.

## Risks / TODOs
- **Potential secret exposure:** `LLM_MODEL_ID` is imported from `agent.config`. If this identifier embeds an API key or other credential, ensure it is sourced from a secure location (environment variable, secret manager) and never hard‑coded.  
- **Return‑type mismatch:** The docstring advertises a `(str, Optional[str])` tuple, but the function returns the raw LLM response. Align the implementation with the documentation or update the docstring to avoid confusion.  
- **Error handling granularity:** All LLM errors are wrapped in a generic `RuntimeError`. Consider defining custom exception types to allow callers to differentiate between network failures, authentication errors, and model‑specific issues.  
- **Logging verbosity:** Currently only a single `info` log is emitted. Adding more detailed logs (e.g., prompt content, timing) could aid debugging but must be balanced against leaking sensitive prompt data.  
- **Test coverage:** The module is a minimal sanity check; expand with unit tests that mock both `invoke`‑style and awaitable LLMs to verify the normalisation logic.
