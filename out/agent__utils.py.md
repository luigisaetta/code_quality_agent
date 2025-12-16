# `agent/utils.py`

## Overview
- Provides small helper utilities used across the demo LangGraph RAG agent.  
- Supplies a **console logger** factory that avoids duplicate handlers.  
- Contains text‑parsing helpers:
  - `extract_text_triple_backticks` – pulls the first code block wrapped in triple back‑ticks.  
  - `extract_json_from_text` – finds the first JSON object in a string and returns a Python `dict`.  
- Offers a simple path‑manipulation function `remove_path_from_ref` to strip directory components from a file reference.  
- All functions are pure‑Python and have no external dependencies beyond the standard library (plus `langchain_core.documents.Document` which is only imported for type hinting).

## Public API
| Function / Class | Signature | Purpose |
|------------------|-----------|---------|
| `get_console_logger(name: str = "ConsoleLogger", level: str = "INFO") -> logging.Logger` | Returns a configured logger that writes to `stdout`. |
| `extract_text_triple_backticks(_text: str) -> str` | Returns the first block of text found between ````` ```. |
| `extract_json_from_text(text: str) -> dict` | Parses the first JSON object found in *text* and returns it as a dictionary. |
| `remove_path_from_ref(ref_pathname: str) -> str` | Strips directory components from a path, returning only the final filename. |

## Key Behaviors and Edge Cases
| Function | Normal behavior | Edge‑case handling |
|----------|----------------|-------------------|
| `get_console_logger` | Creates a logger, sets the requested level, attaches a `StreamHandler` with a simple formatter, and disables propagation. | If the logger already has handlers, it **does not** add another – prevents duplicate log lines when the function is called repeatedly. |
| `extract_text_triple_backticks` | Uses a non‑greedy regex `r"```(.*?)```"` with `re.DOTALL` to capture multiline code blocks. Returns the **first** captured block, stripped of surrounding whitespace. | If no back‑ticks are present or any exception occurs, logs an informational message and **returns the original input text** (fallback behavior). |
| `extract_json_from_text` | Searches for the first `{ … }` substring (including newlines) and feeds it to `json.loads`. | Raises `ValueError` when no JSON is found or when `json.loads` fails (invalid JSON). The exception message includes the underlying `JSONDecodeError`. |
| `remove_path_from_ref` | Splits the input on the OS‑specific separator (`os.sep`) and returns the last segment. | Works even when the path contains no separator (returns the original string). Does **not** normalize Windows‑style mixed separators (`/` vs `\`). |

## Inputs / Outputs and Side Effects
| Function | Input(s) | Output | Side Effects |
|----------|----------|--------|--------------|
| `get_console_logger` | `name` (optional), `level` (optional) | `logging.Logger` instance | May add a `StreamHandler` to the logger (only once). |
| `extract_text_triple_backticks` | `_text: str` | `str` – first code block or the whole text if none found | Emits an INFO log via the console logger when no back‑ticks are detected. |
| `extract_json_from_text` | `text: str` | `dict` – parsed JSON | Raises exceptions on failure; no logging. |
| `remove_path_from_ref` | `ref_pathname: str` | `str` – filename component | Pure function, no side effects. |

## Usage Examples
```python
from agent.utils import (
    get_console_logger,
    extract_text_triple_backticks,
    extract_json_from_text,
    remove_path_from_ref,
)

# 1. Obtain a ready‑to‑use console logger
logger = get_console_logger(level="DEBUG")
logger.info("Utility module loaded")

# 2. Pull a code snippet out of a LLM response
response = """
Here is the config you asked for:

```json
{
    "model": "gpt-4o-mini",
    "temperature": 0.7
}
```
Enjoy!
"""
code_block = extract_text_triple_backticks(response)
print("Extracted block:", code_block)

# 3. Directly parse the JSON from the same response
config = extract_json_from_text(response)
print("Parsed config:", config)

# 4. Strip directory information from a reference string
ref = "/home/user/project/data/file.txt"
filename = remove_path_from_ref(ref)
print("Filename only:", filename)   # → "file.txt"
```

## Risks / TODOs
- **Limited back‑tick extraction** – only the *first* triple‑back‑tick block is returned; callers expecting multiple blocks will lose data. Consider returning a list or adding a parameter to control this.
- **Regex fragility** – `extract_json_from_text` uses a simple `{.*}` pattern which can mistakenly capture braces inside non‑JSON text (e.g., in log messages). A more robust JSON detection (e.g., using a parser that balances braces) would reduce false positives.
- **Path handling on Windows** – `remove_path_from_ref` relies on `os.sep` only; mixed separators (`/` in a Windows path) are not normalized. Using `os.path.basename` would be safer.
- **Logging level mismatch** – the logger’s *handler* is always set to `DEBUG` regardless of the `level` argument, which may expose verbose output unintentionally. Align handler level with the requested logger level.
- No explicit type hints for `extract_text_triple_backticks` and `remove_path_from_ref`; adding them would improve static analysis support.
