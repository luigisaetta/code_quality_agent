# `agent/header_rules.py`

## Overview
- Provides a **simple header validator** for Python source files.
- Defines a list of **required header keys** (e.g., `File name:`, `Author:`) that must appear within the first *N* lines of a file.
- Implements a **dataclass** `HeaderCheckResult` to encapsulate the validation outcome.
- Offers a single public function `check_header` that:
  1. Scans the top `top_lines` lines of a source string.
  2. Detects missing required keys.
  3. Performs a minimal sanity check on the `Description:` field (must not be empty).
- Returns a clear, structured result indicating success, missing keys, and a human‑readable message.

## Public API
| Name | Type | Description |
|------|------|-------------|
| `REQUIRED_KEYS` | `list[str]` | The header fields that must be present. |
| `HeaderCheckResult` | `@dataclass(frozen=True)` | Immutable result object with fields `ok`, `missing_keys`, and `message`. |
| `check_header(source: str, *, top_lines: int = 40) -> HeaderCheckResult` | function | Validates a Python source string against the header rules. |

## Key Behaviors and Edge Cases
- **Scope of search** – Only the first `top_lines` lines (default 40) are examined; anything beyond is ignored.
- **Missing keys** – If any required key is absent, `ok` is `False`, `missing_keys` lists the absent items, and `message` explains the failure.
- **Description sanity** – When the `Description:` key is present, the validator ensures there is non‑whitespace text after the colon. An empty description triggers a failure even though the key exists.
- **Case sensitivity** – Header keys are matched **exactly** (case‑sensitive). `"author:"` would be considered missing.
- **Immutable result** – `HeaderCheckResult` is frozen; callers cannot modify the result after creation.
- **No file I/O** – The function works on a string; reading from disk is the caller’s responsibility.

## Inputs / Outputs / Side Effects
| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Full text of a Python source file (or any code) to be checked. |
| `top_lines` | `int` (keyword‑only) | Number of leading lines to inspect; defaults to 40. |

**Returns**: `HeaderCheckResult` – immutable object with:
- `ok` (`bool`): `True` if all required keys are present and description is non‑empty.
- `missing_keys` (`list[str]`): List of any required keys that were not found.
- `message` (`str`): Human‑readable explanation of the result.

**Side effects**: None (pure function).

## Usage Examples
```python
from agent.header_rules import check_header

# Example source string (could be read from a .py file)
source_code = """\
\"\"\"
File name: my_module.py
Author: Jane Doe
Date last modified: 2025-12-14
Python Version: 3.11
Description: Utility functions for data processing.
License: MIT
\"\"\"

def foo():
    pass
"""

result = check_header(source_code)

print(result.ok)          # True
print(result.missing_keys)  # []
print(result.message)    # "Header looks OK."
```

### Detecting a missing key
```python
bad_source = """\
\"\"\"
File name: my_module.py
Author: Jane Doe
Python Version: 3.11
Description: .
License: MIT
\"\"\"
"""

res = check_header(bad_source)
# res.ok == False
# res.missing_keys == ['Date last modified:']
# res.message == "Missing header keys in first 40 lines: ['Date last modified:']"
```

## Risks / TODOs
- **No secret detection** – The module does not inspect header values for secrets; callers should ensure no credentials are placed in header fields.
- **Hard‑coded key list** – Adding or removing required keys requires code change; consider external configuration for flexibility.
- **Case‑sensitivity** – May cause false negatives if header style varies; could be made case‑insensitive.
- **No multiline handling** – The simple regex assumes the description is on the same line as the key; multiline descriptions will be flagged as empty.  
- **No file reading convenience** – A helper that reads a file and calls `check_header` could improve ergonomics.
