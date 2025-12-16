"""
Prompt for documentation generation of Python files.

You can customize the documentation style and content by modifying the DOC_PROMPT variable below.
"""

DOC_PROMPT = """
You are a senior Python engineer.

You must generate documentation for the following Python file.
The user request below specifies what to emphasize. Follow it carefully when relevant.

IMPORTANT SAFETY RULES:
- Never include secrets, credentials, API keys, tokens, private keys, or passwords.
- If the source contains sensitive-looking values, do not reproduce them. Describe them generically.

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
  - Usage examples (short, realistic)
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

Generate a final report, in markdown, based on the following inputs:

- Processed: {num_files}
- Header issues found: {header_issues}
- Secrets issues found: {secret_issues}

Organize the report in dedicated sections, each one with a proper heading.

"""
