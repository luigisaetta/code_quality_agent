# `agent/secrets_scan.py`

## Overview
- Provides a **light‑weight heuristic scanner** for detecting potential secrets in a block of source code (or any text).  
- Uses a combination of **regular‑expression patterns** (e.g., AWS keys, GitHub tokens, private‑key blocks) and **simple name/value heuristics**.  
- Redacts discovered values in the output to avoid leaking them further.  
- Returns a list of immutable `SecretFinding` objects describing each potential secret, including its line number and a short excerpt.  
- Limits the number of findings via `max_findings` to keep processing time bounded.  

## Public API
| Symbol | Type | Description |
|--------|------|-------------|
| `SecretFinding` | `@dataclass(frozen=True)` | Immutable record of a finding: `kind`, `line`, `name_or_key`, `excerpt`. |
| `scan_for_secrets(source: str, *, max_findings: int = 200) -> list[SecretFinding]` | function | Main entry point – scans the supplied `source` string and returns a list of `SecretFinding` objects. |

*(All other helpers are internal (`_redact_*`, `_is_probably_secret`) and not intended for external import.)*

## Key Behaviors and Edge Cases
| Situation | Behaviour |
|-----------|-----------|
| **Pattern match** (e.g., `AKIA…` or `-----BEGIN PRIVATE KEY-----`) | Immediately recorded as a finding with `kind` set to the pattern description; `name_or_key` is `"(pattern)"`. |
| **Simple assignment** (`NAME = "value"` ) | If the variable name matches a *sensitive* keyword **or** the value looks like a long base‑64/hex token, it is flagged as `"Sensitive assignment"`. |
| **Dictionary entry** (`"key": "value",`) | Same heuristic as assignments, flagged as `"Sensitive dict value"`. |
| **Placeholder values** (`"changeme"`, `"dummy"` etc.) | Explicitly ignored – they are treated as non‑secrets. |
| **Empty or whitespace‑only values** | Ignored – not considered a secret. |
| **Maximum findings reached** (`max_findings`) | Scanning stops early and returns the current list. |
| **Redaction** | Values are replaced with a short masked form (`a***z`) or `***` for very short strings, preserving line structure for readability. |
| **Multiline constructs** (e.g., multi‑line strings, dicts spanning several lines) | Not detected – the scanner works line‑by‑line, so secrets split across lines will be missed. |
| **Non‑string literals** (e.g., `NUM = 123`) | Ignored – the regex only matches quoted strings. |

## Inputs / Outputs / Side Effects
| Aspect | Details |
|--------|---------|
| **Input** | `source: str` – any text (typically source code) to be scanned. |
| **Optional param** | `max_findings: int` – upper bound on the number of findings returned (default 200). |
| **Output** | `list[SecretFinding]` – ordered by appearance in the source. Each `SecretFinding` contains:<br>• `kind` – description of why it was flagged.<br>• `line` – 1‑based line number.<br>• `name_or_key` – variable name, dict key, or `"(pattern)"`.<br>• `excerpt` – the original line with the secret redacted. |
| **Side effects** | None – pure function; does not modify files, environment, or external state. |

## Usage Examples
```python
from agent.secrets_scan import scan_for_secrets, SecretFinding

sample_code = """
api_key = "AKIA1234567890ABCD"
config = {
    "password": "s3cr3tP@ss",
    "url": "https://example.com"
}
# A fake placeholder
token = "changeme"
"""

findings = scan_for_secrets(sample_code)

for f in findings:
    print(f"[Line {f.line}] {f.kind}: {f.name_or_key}")
    print(f"  → {f.excerpt}")
```

**Typical output**
```
[Line 2] Sensitive assignment: api_key
  → api_key = "A***D"
[Line 3] Sensitive dict value: password
  → "password": "s***t",
[Line 4] Sensitive dict value: url
  → "url": "h***m",
```

*(Values are redacted; the actual secret strings are not printed.)*

## Risks / TODOs
- **False positives / negatives**: Heuristics are simple; legitimate strings may be flagged, and multi‑line or obfuscated secrets may be missed.  
- **No support for multiline constructs** – consider extending the scanner to handle continuation lines or raw‑string blocks.  
- **Pattern list is static** – new secret formats (e.g., newer cloud provider keys) need manual updates.  
- **No configurable sensitivity** – exposing a way to add custom regexes or adjust placeholder lists could improve flexibility.  

*No hard‑coded secrets were discovered in the source file.*
