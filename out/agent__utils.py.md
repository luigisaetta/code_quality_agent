# `agent/utils.py`

## Overview
- Provides small helper utilities used across the demo LangGraph RAG agent.  
- Supplies a simple console logger that avoids duplicate handlers.  
- Contains text‑parsing helpers:
  - `extract_text_triple_backticks` – returns the first code block wrapped in triple back‑ticks.  
  - `extract_json_from_text` – pulls a JSON object from arbitrary text and parses it.  
- Includes a path‑manipulation helper `remove_path_from_ref` that strips directory components from a file reference.  
- All functions are pure (no external network calls) and rely only on the Python standard library and `langchain_core`.

## Public API
| Function / Class | Signature | Purpose |
|------------------|-----------|---------|
| `get_console_logger(name: str = "ConsoleLogger", level: str = "INFO") -> logging.Logger` | Returns a configured `logging.Logger` that writes to `stdout`. |
| `extract_text_triple_backticks(_text: str) -> str` | Extracts the **first** block of text surrounded by triple back‑ticks (```). |
| `extract_json_from_text(text: str) -> dict` | Finds the first JSON object (`{…}`) inside a string and returns it as a Python `dict`. |
| `remove_path_from_ref(ref_pathname: str) -> str` | Strips any directory components from a path, returning only the final filename/reference. |

*(No classes are defined in this module.)*

## Key Behaviors and Edge Cases
| Function | Important Behaviour | Edge Cases |
|----------|--------------------|------------|
| `get_console_logger` | - Creates a logger only once per `name` (checks `logger.handlers`). <br> - Sets the logger’s own level to the supplied `level` (string accepted by `logging`). <br> - Adds a `StreamHandler` with `DEBUG` level and a simple timestamp formatter. | - If an invalid log level string is passed, `logger.setLevel` will raise a `ValueError`. <br> - Propagation is disabled (`logger.propagate = False`). |
| `extract_text_triple_backticks` | - Uses a non‑greedy regex `r"```(.*?)```"` with `re.DOTALL` to capture multiline content. <br> - Returns **only the first** matched block, stripped of surrounding whitespace. <br> - Logs a message and falls back to returning the whole input when no match is found. | - If the input contains multiple back‑tick blocks, only the first is returned. <br> - If the input is `None` or not a string, `re.findall` will raise a `TypeError`. |
| `extract_json_from_text` | - Searches for the first `{…}` substring (greedy, includes nested braces). <br> - Parses it with `json.loads`. <br> - Raises `ValueError` when no JSON is found or when parsing fails. | - The regex may capture an incomplete JSON object if there are stray braces before the real payload. <br> - Does **not** handle JSON arrays (`[...]`). |
| `remove_path_from_ref` | - Splits the path using the OS‑specific separator (`os.sep`). <br> - Returns the last component (or the original string if split yields a single element). | - Works with both forward (`/`) and backward (`\`) separators on Windows because `os.sep` matches the native separator; however, mixed separators are not normalized. <br> - Does not resolve `..` or symbolic links. |

## Inputs / Outputs / Side Effects
| Function | Input(s) | Output | Side Effects |
|----------|----------|--------|--------------|
| `get_console_logger` | `name` (str), `level` (str) | `logging.Logger` instance | May add a `StreamHandler` to the logger (once). |
| `extract_text_triple_backticks` | `_text` (str) | `str` – first back‑tick block or the original text | Emits an INFO log when no block is found. |
| `extract_json_from_text` | `text` (str) | `dict` – parsed JSON | Raises `ValueError` on failure; no logging. |
| `remove_path_from_ref` | `ref_pathname` (str) | `str` – filename/reference without directories | Pure function, no side effects. |

## Usage Examples
```python
from agent.utils import (
    get_console_logger,
    extract_text_triple_backticks,
    extract_json_from_text,
    remove_path_from_ref,
)

# 1. Obtain a console logger
log = get_console_logger(level="DEBUG")
log.info("Utility module ready")

# 2. Pull a code block from a LLM response
response = """Here is the snippet:\n```python\nprint('hello')\n```\nEnjoy!"""
code = extract_text_triple_backticks(response)
print("Extracted code:", code)   # -> print('hello')

# 3. Extract JSON payload from a mixed text
msg = "The result is: {\"status\": \"ok\", \"count\": 42} thanks."
payload = extract_json_from_text(msg)
print(payload["count"])          # -> 42

# 4. Strip directory from a reference path
ref = "/tmp/data/file.txt"
filename = remove_path_from_ref(ref)
print(filename)                  # -> file.txt
```

## Risks / TODOs
- **Logging level validation** – `get_console_logger` accepts any string; passing an invalid level raises an exception. Consider validating against `logging._nameToLevel`.
- **Back‑tick extraction limited to first block** – If callers need *all* blocks, the function must be extended or renamed to reflect its current behavior.
- **JSON extraction regex is simplistic** – It may capture unintended braces or fail on arrays. A more robust parser (e.g., using a streaming JSON detector) would reduce false positives.
- **Path handling is OS‑specific** – Mixed separators or relative components (`..`) are not normalized. Using `os.path.basename` or `pathlib.Path` would be safer.
- No unit tests are bundled with this module; adding tests for edge cases (empty strings, malformed JSON, multiple back‑ticks) is recommended.
