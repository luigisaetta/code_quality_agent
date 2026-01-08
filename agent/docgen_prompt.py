"""
Prompt for documentation generation of Python files.

You can customize the documentation style and content by modifying the DOC_PROMPT variable below.

License:
    MIT
"""

DOC_PROMPT = """
You are a senior Python engineer.

You must generate documentation for the following Python file.
The user request below specifies what to emphasize. Follow it carefully when relevant.

IMPORTANT SAFETY / COMPLIANCE RULES (highest priority):
- Never include secrets, credentials, API keys, tokens, private keys, or passwords.
- Never include or reproduce personal data (PII). This includes (non-exhaustive):
  emails, phone numbers, IBAN, credit card numbers, tax IDs, personal addresses.
- If the source contains sensitive-looking values or PII-like strings, DO NOT reproduce them.
  Instead, describe them generically and mention that values were redacted.

USER REQUEST (high priority):
{request}

Output format:
- Markdown
- Title: the file path
- Sections:
  - Overview (what it does, in 3-6 bullet points)
  - Public API (functions/classes likely intended for import/use)
  - Key behaviors and edge cases
  - Inputs/outputs and side effects
  - Usage examples (short, realistic) - IMPORTANT: use placeholders, never real identifiers
  - Risks/TODOs (brief)

Keep it practical and concise.

FILE PATH: {relpath}

PYTHON SOURCE:
```python
{source}
```
"""

# This is the prompt with instructions for the final report
REPORT_PROMPT = """
You are a senior Python engineer.

Today is: {now_datetime}.

Generate a final report in markdown based on the following inputs.

## Inputs
- Processed: {num_files}
- Header issues found: {header_issues}
- Secrets issues found: {secret_issues}
- License check: {license_check}
- PII hard failures (direct identifiers): {pii_hard_failures}
- PII warnings (structured name/address): {pii_warnings}

## PII Policy
Explain the policy outcome clearly:
- HARD FAIL: direct identifiers (email, phone, IBAN, credit card, tax id, etc.)
- WARN: possible names/addresses only when in structured form

If there are any secrets issues and PII hard failures, the report must prominently state that 
the policies are NOT satisfied.

## Output requirements
- Title: Code Compliance & Risk Assessment Report
- Organize the report into dedicated sections with proper headings:
  1) Executive summary (pass/fail + key numbers)
  2) License compliance
  3) Header compliance
  4) Secrets scan results
  5) PII compliance (separate subsections for HARD FAIL and WARN)
  6) Recommendations (actionable, prioritized)

## Safety rules for the report (highest priority)
- Never include secrets or credentials.
- Never include raw PII. If excerpts are present in the inputs, assume they are already masked;
  do not attempt to reconstruct or infer the original values.
- When providing examples, always use placeholders.

Keep it concise, practical, and suitable for a CI compliance artifact.
"""
