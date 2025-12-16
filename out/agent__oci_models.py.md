# `agent/oci_models.py`

## Overview
- Provides a thin wrapper to create an OCI GenAI language model (or OpenAI‑compatible model) instance using LangChain integrations.  
- Supports two initialization paths:
  1. **OCI‑only** (`ChatOCIGenAI`) – the original LangChain‑OCI approach.  
  2. **OpenAI‑compatible** (`ChatOCIOpenAI`) – built on `langchain-openai` + `oci-openai` for user‑principal authentication.  
- Handles models that do **not** accept `temperature` / `max_tokens` parameters (e.g., `openai.gpt-5`).  
- Offers a small debugging helper (`debug_llm`) that prints selected attributes of the created LLM object when `DEBUG` is enabled.  
- Relies on configuration values from `agent.config` and a private compartment identifier from `agent.config_private`.

## Public API
| Name | Type | Description |
|------|------|-------------|
| `get_llm(model_id=LLM_MODEL_ID, temperature=TEMPERATURE, max_tokens=MAX_TOKENS)` | function | Returns a ready‑to‑use LangChain LLM object (`ChatOCIGenAI` or `ChatOCIOpenAI`) based on the current configuration flags. |
| `debug_llm(llm)` | function *(internal)* | Prints the class name and a subset of attributes for a given LLM instance; used only when `DEBUG` is `True`. |
| `MODELS_WITHOUT_KWARGS` | `set[str]` | Constant listing model IDs that cannot receive `temperature` / `max_tokens` arguments. |

## Key Behaviors and Edge Cases
| Situation | Behaviour |
|-----------|-----------|
| **Model supports kwargs** (`model_id` not in `MODELS_WITHOUT_KWARGS`) | `model_kwargs` is built with `temperature` and `max_tokens` and passed to the OCI constructor. |
| **Model does *not* support kwargs** (`model_id` in `MODELS_WITHOUT_KWARGS`) | `model_kwargs` is set to `None` (OCI path) or the explicit `temperature`/`max_tokens` arguments are omitted (OpenAI path). |
| **`USE_LANGCHAIN_OPENAI` = `False`** | Instantiates `ChatOCIGenAI` (OCI‑only mode). |
| **`USE_LANGCHAIN_OPENAI` = `True`** | Instantiates `ChatOCIOpenAI` (OpenAI‑compatible mode) with `OciUserPrincipalAuth`. |
| **`DEBUG` = `True`** | After creating the OpenAI‑compatible LLM, `debug_llm` prints diagnostic information. |
| **Missing required config (e.g., `COMPARTMENT_ID`)** | An exception will be raised by the underlying LangChain class; the wrapper does not catch it. |
| **`STREAMING` flag** | Propagated to the OCI constructor (`is_stream`). The OpenAI path currently ignores it (commented out). |

## Inputs / Outputs / Side Effects
| Parameter | Type | Default (from `agent.config`) | Meaning |
|-----------|------|------------------------------|---------|
| `model_id` | `str` | `LLM_MODEL_ID` | Identifier of the LLM model to load (OCI model ID or OpenAI model name). |
| `temperature` | `float` | `TEMPERATURE` | Sampling temperature (if supported). |
| `max_tokens` | `int` | `MAX_TOKENS` | Maximum token count for generated completions (if supported). |

**Return value**: an instance of either `ChatOCIGenAI` or `ChatOCIOpenAI`, ready for `.invoke()` / `.stream()` calls.

**Side effects**:
- Imports and may trigger lazy loading of heavy LangChain modules.
- Logs via a console logger (`agent.utils.get_console_logger`).
- When `DEBUG` is true, prints diagnostic information to stdout.

## Usage Examples
```python
# Example 1 – default OCI model
from agent.oci_models import get_llm

llm = get_llm()                     # uses defaults from agent.config
response = llm.invoke("What is the capital of France?")
print(response)

# Example 2 – explicit OpenAI‑compatible model
from agent.config import USE_LANGCHAIN_OPENAI

# Force OpenAI‑compatible path (e.g., for gpt-5)
USE_LANGCHAIN_OPENAI = True

llm = get_llm(
    model_id="openai.gpt-5",
    temperature=0.0,               # ignored for this model
    max_tokens=200,
)

# Streaming response (if the model supports it)
for chunk in llm.stream("Summarize the latest AI news."):
    print(chunk, end="")
```

## Risks / TODOs
- **Secret exposure**: The module imports `COMPARTMENT_ID` from `agent.config_private`. Ensure that this private file is never committed to version control and that the compartment ID does not contain sensitive information that could be abused.  
- **Configuration validation**: No explicit checks for required config values (`SERVICE_ENDPOINT`, `AUTH`, etc.). Adding validation would produce clearer error messages.  
- **Streaming flag mismatch**: `STREAMING` is passed to the OCI constructor but ignored for the OpenAI path (commented out). Align the behavior or expose a separate flag.  
- **Model‑specific kwargs**: The current handling assumes only `temperature` and `max_tokens` need omission. Future models may require additional or different parameters; consider a more flexible per‑model kwargs map.  
- **Logging verbosity**: `debug_llm` prints directly to stdout, which may be undesirable in production. Replace with structured logger calls.  

*No hard‑coded secrets or credentials were found in the source file.*
