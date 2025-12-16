# `agent/docgen_prompt.py`

## Overview
- Provides a **template string** (`DOC_PROMPT`) used to generate prompts for automatic documentation creation of Python files.  
- The template embeds placeholders for:
  - The user’s specific request (`{request}`)  
  - The relative file path (`{relpath}`)  
  - The source code to be documented (`{source}`)  
- Designed to be **customizable**: developers can edit `DOC_PROMPT` to change style, wording, or additional instructions.  
- Includes a short module‑level docstring explaining its purpose.  
- No executable code; the module simply exports the constant.

## Public API
```python
DOC_PROMPT: str
```
*`DOC_PROMPT`* – a multi‑line formatted string that can be interpolated with `.format()` (or an f‑string) to produce a ready‑to‑use prompt for a language model.

## Key Behaviors and Edge Cases
| Situation | Behaviour |
|-----------|-----------|
| **Standard use** – call `DOC_PROMPT.format(request=..., relpath=..., source=...)` | Returns a prompt containing the supplied values, preserving the surrounding markdown and code fences. |
| **Missing placeholder** – omit one of the required keys | `KeyError` is raised by `str.format`. Caller must ensure all three placeholders are supplied. |
| **User‑provided content contains backticks or triple‑quotes** | The template already wraps the source code in a fenced code block (```python). Embedded backticks are safe, but stray triple‑quotes could break the outer string if the template is edited; keep the outer triple‑quoted string unchanged. |
| **Large source files** | The entire source is inserted verbatim; very large files may produce extremely long prompts, potentially exceeding model token limits. Consider truncating or summarising before insertion. |

## Inputs / Outputs / Side Effects
| Component | Type | Description |
|-----------|------|-------------|
| `request` | `str` | User‑specific instruction that guides the documentation style or focus. |
| `relpath` | `str` | Relative path of the file being documented (e.g., `agent/docgen_prompt.py`). |
| `source` | `str` | Full source code of the target Python file. |
| **Return** | `str` | A fully‑rendered prompt ready for submission to an LLM. |
| **Side effects** | None | The module only defines a constant; it does not perform I/O or mutate state. |

## Usage Examples
```python
from agent.docgen_prompt import DOC_PROMPT

# Example inputs
user_request = "Emphasize security considerations."
file_path = "agent/docgen_prompt.py"
source_code = """def hello():\n    print("Hello, world!")"""

# Render the prompt
prompt = DOC_PROMPT.format(
    request=user_request,
    relpath=file_path,
    source=source_code,
)

print(prompt)
```

*Result (truncated for brevity):*
```
You are a senior Python engineer.

You must generate documentation for the following Python file.
The user request below specifies what to emphasize. Follow it carefully when relevant.

IMPORTANT SAFETY RULES:
- Never include secrets, credentials, API keys, tokens, private keys, or passwords.
- If the source contains sensitive-looking values, do not reproduce them. Describe them generically.

USER REQUEST (high priority):
Emphasize security considerations.

Output format:
- Markdown
- Title: the file path
- Sections:
  - Overview (what it does, in 3-6 bullet points)
  - Public API (functions/classes likely intended for import/use)
  - Key behaviors and edge cases
  - Inputs/outputs and side effects
  - Usage examples (short, realistic)
  - Risks/TODOs (brief)

Keep it practical and concise.

FILE PATH: agent/docgen_prompt.py

PYTHON SOURCE:
```python
def hello():
    print("Hello, world!")
```
```

## Risks / TODOs
- **Placeholder safety**: Ensure that the values supplied for `{request}`, `{relpath}`, and `{source}` are properly sanitized if they originate from untrusted users, to avoid prompt injection.  
- **Token limits**: Very large `source` strings may exceed the token budget of downstream LLMs; consider adding logic to truncate or summarize before formatting.  
- **Maintainability**: If the template is edited, verify that the triple‑quoted outer string remains syntactically correct and that all placeholders are still present.  

No secrets or credentials were detected in the source.
