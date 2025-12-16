# `agent/secrets_scan.py`

## Overview
- Provides a **light‑weight heuristic scanner** for hard‑coded secrets in Python source code.  
- Detects secrets via:
  1. **Pre‑defined regex patterns** (AWS keys, GitHub tokens, private‑key blocks, etc.).
  2. **Sensitive variable/keyword names** (e.g., `password`, `api_key`, `token`) combined with sufficiently long alphanumeric values.
  3. **Dictionary key/value pairs** that match the same heuristic.
- Redacts any discovered value in the output to avoid leaking it further.  
- Returns a list of `SecretFinding` objects, each describing the kind, line number, identifier, and a redacted excerpt.  
- Stops scanning once `max_findings` (default 200) is reached.

## Public API
| Name | Type | Description |
|------|------|-------------|
| `SecretFinding` | `@dataclass(frozen=True)` | Immutable record of a finding: `kind`, `line`, `name_or_key`, `excerpt`. |
| `scan_for_secrets(source: str, *, max_findings: int = 200) -> list[SecretFinding]` | function | Main entry point – scans a Python source string and returns detected secret findings. |

*Internal helpers (`_redact_value`, `_redact_line_keep_structure`, `_is_probably_secret`) are deliberately not exported.*

## Key Behaviors and Edge Cases
| Situation | Behaviour |
|-----------|-----------|
| **Pattern match** (e.g., `AKIA…` or `-----BEGIN PRIVATE KEY-----`) | Immediately recorded as a finding with kind derived from `PATTERNS`. |
| **Simple assignment** (`NAME = "value"`) | If the variable name matches `SENSITIVE_NAME_RE` **or** the value is ≥ 20 characters of allowed charset, it is flagged. |
| **Dictionary entry** (`"key": "value",`) | Same heuristic as assignments, but the *key* is examined for sensitivity. |
| **Placeholder values** (`"changeme"`, `"dummy"` etc.) | Explicitly ignored to reduce false positives. |
| **Very short values** (`len(value) ≤ 4`) | Ignored – unlikely to be real secrets. |
| **Multiple matches on the same line** | All pattern matches are reported; only the first assignment/dict match per line is processed. |
| **`max_findings` limit** | Scanning stops early once the limit is reached, returning the partial list. |
| **Non‑string assignments** (e.g., `NUM = 42`) | Not matched by `ASSIGNMENT_STR_RE`; therefore ignored. |
| **Multi‑line strings or complex expressions** | Not captured – the scanner works line‑by‑line on simple literal assignments. |

## Inputs / Outputs / Side Effects
| Aspect | Details |
|--------|---------|
| **Input** | `source`: a single string containing the full Python source to be inspected. |
| **Optional input** | `max_findings`: upper bound on the number of findings returned (default 200). |
| **Output** | List of `SecretFinding` objects (may be empty). Each object contains a **redacted** excerpt, never the raw secret. |
| **Side effects** | None – pure function; does not modify files, environment, or external state. |

## Usage Examples
```python
from agent.secrets_scan import scan_for_secrets, SecretFinding

# Example source (could be read from a file)
code = """
API_KEY = "AKIA1234567890ABCDEF"
config = {
    "password": "s3cr3tP@ssw0rd!",
    "url": "https://example.com"
}
"""

findings = scan_for_secrets(code)

for f in findings:
    print(f"[Line {f.line}] {f.kind}: {f.name_or_key} -> {f.excerpt}")
```

Typical output (values redacted):
```
[Line 2] AWS Access Key ID: (pattern) -> API_KEY = A***F
[Line 3] Sensitive dict value: password -> "password": "s***d",
```

## Risks / TODOs
- **Heuristic nature** – may miss secrets that do not follow the listed patterns or naming conventions (false negatives).  
- **False positives** – generic long alphanumeric strings with a “sensitive” name can be flagged even if they are not secrets.  
- **Limited scope** – does not parse multi‑line strings, f‑strings, or values constructed at runtime.  
- **No configurable pattern list** – extending detection requires code changes.  
- **No integration with external secret‑scanning services** – intended only as a quick, local sanity check.  

*No actual secrets were found in the source file itself.*
