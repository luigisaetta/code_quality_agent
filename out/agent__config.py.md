# `agent/config.py`

## Overview
- Provides a central place for **runtime configuration constants** used by the LangGraph RAG agent.  
- Defines flags for debugging and streaming output.  
- Holds OCI (Oracle Cloud Infrastructure) authentication mode, region, and service endpoint construction.  
- Specifies default LLM settings: model identifier, temperature, top‑p, and max token limit.  
- Designed to be imported by other modules; no executable code runs on import.

## Public API
The module exports only **constants** (no functions or classes):

| Constant | Description |
|----------|-------------|
| `DEBUG` | Boolean flag to enable verbose debugging output. |
| `STREAMING` | Boolean flag to enable streaming responses from the LLM. |
| `AUTH` | Authentication method for OCI (default `"API_KEY"`). |
| `USE_LANGCHAIN_OPENAI` | Switch to use LangChain’s OpenAI integration (`True`/`False`). |
| `REGION` | OCI region string (e.g., `"us-chicago-1"`). |
| `SERVICE_ENDPOINT` | Fully‑qualified inference endpoint built from `REGION`. |
| `LLM_MODEL_ID` | Identifier of the default language model (e.g., `"openai.gpt-oss-120b"`). |
| `TEMPERATURE` | Sampling temperature for the LLM (float, default `0.0`). |
| `TOP_P` | Nucleus sampling probability (float, default `1`). |
| `MAX_TOKENS` | Maximum token count per request (int, default `4000`). |

## Key Behaviors and Edge Cases
- **Dynamic endpoint**: `SERVICE_ENDPOINT` is constructed with an f‑string; changing `REGION` automatically updates the URL.
- **Auth mode**: The module only stores the auth type (`"API_KEY"`). Actual credential handling must be performed elsewhere.
- **Model selection**: Several model IDs are commented out; the active `LLM_MODEL_ID` can be swapped by editing the constant.
- **Debug/Streaming flags**: Down‑stream code should respect these booleans; they default to `False` for production stability.
- **Future‑proofing**: The comment `# This module is in development, may change in future versions.` warns that constants may be renamed or expanded.

## Inputs / Outputs and Side Effects
- **Inputs**: None at runtime; all values are hard‑coded constants.
- **Outputs**: The module makes the constants available to any importer.
- **Side Effects**: Importing the module has no side effects beyond evaluating the constant definitions.

## Usage Examples
```python
# Example 1: Accessing configuration in another module
import agent.config as cfg

if cfg.DEBUG:
    print("Debug mode is ON")

print(f"Connecting to OCI endpoint: {cfg.SERVICE_ENDPOINT}")
print(f"Using model: {cfg.LLM_MODEL_ID}")

# Example 2: Passing config to an LLM client
from some_llm_lib import LLMClient

client = LLMClient(
    model_id=cfg.LLM_MODEL_ID,
    temperature=cfg.TEMPERATURE,
    max_tokens=cfg.MAX_TOKENS,
    streaming=cfg.STREAMING,
)

response = client.generate("Explain the RAG architecture.")
print(response)
```

## Risks / TODOs
- **Potential secret exposure**: `AUTH = "API_KEY"` is a placeholder that could be replaced with a real API key. Ensure that actual credentials are **never hard‑coded** in source control; load them securely from environment variables or secret managers.
- **Hard‑coded region/endpoint**: Changing deployment regions requires code changes. Consider externalizing these values to environment variables or a configuration file.
- **Missing validation**: No runtime checks enforce valid values (e.g., temperature range). Adding simple validation could prevent misconfiguration.
- **Future changes**: As the module is marked “in development,” downstream code should guard against missing constants or renamed identifiers.
