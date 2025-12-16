# `agent/header_rules.py`

## Overview
- Provides a **simple, practical header validator** for Python source files.  
- Enforces the presence of a fixed set of header keys (file name, author, date, etc.) within the first *N* lines.  
- Checks that the **Description** field is non‑empty.  
- When a file path is supplied, validates that the **Date last modified** header matches the file’s actual modification timestamp (UTC).  
- Returns a structured, immutable `HeaderCheckResult` describing success or the specific failure(s).  

## Public API
| Name | Type | Description |
|------|------|-------------|
| `REQUIRED_KEYS` | `list[str]` | Header keys that must appear in the top of the file. |
| `HeaderCheckResult` | `@dataclass(frozen=True)` | Immutable result object with fields: `ok`, `missing_keys`, `message`, `date_mismatch`. |
| `check_header(source: str, *, path: Path | None = None, top_lines: int = 40) -> HeaderCheckResult` | Function | Core validator – see *Inputs/Outputs* for details. |

*Note:* `DATE_RE` is an internal regular expression used by `check_header` and is **not** part of the public API.

## Key Behaviors and Edge Cases
| Situation | Behaviour |
|-----------|-----------|
| **Missing required keys** | Returns `ok=False` with `missing_keys` listing the absent entries. |
| **Empty Description field** | Returns `ok=False` with a message indicating the description is empty. |
| **No `path` supplied** | Skips the date‑alignment check; only key presence and description are validated. |
| **`Date last modified` not parseable** | Returns `ok=False` with a message about the missing or unparsable date field. |
| **Unsupported date format** | Only `YYYY‑MM‑DD` (or an ISO datetime that starts with that pattern) is accepted; otherwise returns `ok=False`. |
| **Header date ≠ file mtime (UTC)** | Returns `ok=False` with `date_mismatch=True` and a detailed mismatch message. |
| **All checks pass** | Returns `ok=True` with `missing_keys=[]` and a success message. |
| **`top_lines` too small** | If required keys appear after the cut‑off, they will be reported as missing. |
| **Large source strings** | Only the first `top_lines` lines are examined, keeping the operation O(`top_lines`). |

## Inputs / Outputs and Side Effects
| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Full text of the Python file to be inspected. |
| `path` | `Path | None` | Optional filesystem path to the same file; used for mtime comparison. |
| `top_lines` | `int` (default `40`) | Number of leading lines examined for header keys. |

**Return:** `HeaderCheckResult` – immutable dataclass containing:
- `ok` (`bool`): overall success flag.
- `missing_keys` (`list[str]`): any required keys not found.
- `message` (`str`): human‑readable explanation.
- `date_mismatch` (`bool`, default `False`): `True` only when the header date differs from the file’s mtime.

**Side effects:** None, except a single `stat()` call on `path` when provided (read‑only filesystem metadata access).

## Usage Examples
```python
from pathlib import Path
from agent.header_rules import check_header

# Example 1: Validate a file's header without date check
src = Path("my_module.py").read_text(encoding="utf-8")
result = check_header(src)
print(result.ok)          # True / False
print(result.message)    # Explanation

# Example 2: Validate with date alignment
path = Path("my_module.py")
src = path.read_text(encoding="utf-8")
result = check_header(src, path=path)
if not result.ok:
    print("Header problem:", result.message)
    if result.date_mismatch:
        print("⚠️  Header date does not match file modification time.")
else:
    print("Header is valid.")
```

## Risks / TODOs
- **Date format rigidity:** Only `YYYY‑MM‑DD` (or ISO strings beginning with that) are accepted; other common formats (e.g., `DD/MM/YYYY`) will cause false failures.  
- **Fixed key list:** Adding or removing header fields requires code changes; consider making `REQUIRED_KEYS` configurable.  
- **No logging or exception propagation:** Errors are reported only via the result object; callers needing richer diagnostics must extend the API.  
- **UTC‑only mtime comparison:** Filesystems with non‑UTC timestamps may lead to mismatches; a timezone‑aware option could be useful.  
- **Potential false negatives** if required keys appear after `top_lines`; callers should ensure the header is within the examined range.  

No secrets, credentials, or sensitive values were detected in this file.
