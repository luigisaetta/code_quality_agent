# `agent/docgen_prompt.py`

## Overview
- Provides two multi‑line string templates (`DOC_PROMPT` and `REPORT_PROMPT`) used to generate prompts for automated documentation creation and final reporting.  
- The templates embed placeholders (`{request}`, `{relpath}`, `{source}`, `{now_datetime}`, `{num_files}`, `{header_issues}`, `{secret_issues}`) that are intended to be filled in at runtime via `str.format` or f‑strings.  
- Includes a module‑level docstring describing the purpose of the file and its MIT license.  
- No executable code; the module only defines constants.  
- Designed to be imported by other parts of the system that handle prompt construction and LLM interaction.

## Public API
| Name | Type | Description |
|------|------|-------------|
| `DOC_PROMPT` | `str` | Template for generating a documentation‑generation prompt. It expects the placeholders `{request}`, `{relpath}`, and `{source}` to be substituted with the user request, relative file path, and source code respectively. |
| `REPORT_PROMPT` | `str` | Template for generating a final markdown report. It expects placeholders `{now_datetime}`, `{num_files}`, `{header_issues}`, and `{secret_issues}` to be filled with the current timestamp and analysis results. |

## Key Behaviors and Edge Cases
- **Placeholder substitution** – The templates rely on `str.format` (or equivalent) to replace placeholders. Missing or misspelled keys will raise a `KeyError`.  
- **Safety notice** – Both prompts embed a “IMPORTANT SAFETY RULES” block that reminds downstream processing not to expose secrets. The templates themselves do not contain any secrets.  
- **Multiline formatting** – The raw strings preserve indentation and line breaks, which is important for the LLM to interpret the prompt correctly.  
- **Unicode handling** – The templates are plain ASCII; they will work with any Unicode content inserted via placeholders.  
- **Potential injection** – If user‑provided values (e.g., `{request}`) contain formatting braces (`{}`), they must be escaped or passed through a safe templating method to avoid `KeyError` or unintended substitution.

## Inputs / Outputs and Side Effects
| Component | Input | Output | Side Effects |
|-----------|-------|--------|--------------|
| `DOC_PROMPT.format(request, relpath, source)` | `request` (str), `relpath` (str), `source` (str) | Fully‑rendered markdown prompt ready for an LLM | None (pure string operation) |
| `REPORT_PROMPT.format(now_datetime, num_files, header_issues, secret_issues)` | `now_datetime` (datetime or str), `num_files` (int), `header_issues` (int), `secret_issues` (int) | Final markdown report summarising the analysis | None |

## Usage Examples
```python
from agent.docgen_prompt import DOC_PROMPT, REPORT_PROMPT
from datetime import datetime

# Example 1 – Build a documentation generation prompt
user_request = "Explain the public API and give usage examples."
rel_path = "my_module/utils.py"
source_code = """def add(a, b):\n    return a + b"""

doc_prompt = DOC_PROMPT.format(
    request=user_request,
    relpath=rel_path,
    source=source_code,
)

print(doc_prompt)   # Send this string to the LLM

# Example 2 – Build a final report after processing several files
now = datetime.utcnow().isoformat()
final_report = REPORT_PROMPT.format(
    now_datetime=now,
    num_files=42,
    header_issues=0,
    secret_issues=0,
)

print(final_report)   # Rendered markdown report
```

## Risks / TODOs
- **Placeholder safety** – Ensure any user‑supplied text is escaped or sanitized before formatting to avoid `KeyError` or accidental injection.  
- **Missing data handling** – Add defensive code (e.g., `str.format_map(defaultdict(str))`) to gracefully handle absent placeholders.  
- **Testing** – Include unit tests that verify the templates render correctly with typical and edge‑case inputs.  
- **Documentation** – Consider exposing a small helper function (e.g., `render_doc_prompt(request, relpath, source)`) to encapsulate formatting and validation.  

### Secrets Scan
No hard‑coded secrets, API keys, tokens, or passwords were found in this file. The only sensitive‑looking content is the generic safety notice, which is intentional and does not expose real credentials.
