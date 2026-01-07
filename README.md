# Code Quality Agent

A lightweight **LangGraph-based** agent that scans a local Python codebase (read-only) to:

- ✅ **Check file headers** against a simple template policy
- ✅ **Scan for secrets** (heuristic patterns + suspicious assignments)
- ✅ **Generate per-file documentation** in Markdown via an LLM (OCI GenAI / OCI OpenAI via LangChain)

It produces artifacts in a separate output folder (no in-place edits).


---

## Features

### Header policy checks
For each discovered `.py` file, the agent validates that a header block contains:

- `File name:`
- `Author:`
- `Date last modified:`
- `Python Version:`
- `Description:`
- `License:`

It also performs a **date alignment check** (header date vs. file `mtime` in UTC) when the file path is available.

### Secrets scanning (heuristic)
The agent searches each file for:
- known patterns (AWS keys, GitHub tokens, OCI OCIDs, private key blocks, bearer headers, etc.)
- suspicious string assignments / dict values with sensitive names (password, token, secret, api_key, …)

Findings are reported with:
- kind
- line number
- a redacted excerpt

### Per-file doc generation (LLM)
For each Python file, the agent can generate Markdown documentation with sections such as:
- overview
- public API
- behaviors/edge cases
- side effects
- usage examples
- risks/TODOs

A final summary report is also generated in Markdown.

---

## Repository layout

```text
.
├── agent/
│   ├── graph_agent.py        # LangGraph pipeline (discover → check → scan → docgen → report)
│   ├── fs_ro.py              # Read-only sandboxed filesystem access
│   ├── header_rules.py       # Header policy checker
│   ├── secrets_scan.py       # Heuristic secrets scanner
│   ├── docgen.py             # Per-file documentation generation
│   ├── docgen_prompt.py      # Prompts for doc generation + final report
│   ├── docgen_utils.py       # LLM invocation + output normalization
│   ├── oci_models.py         # OCI GenAI / OCI OpenAI LangChain adapters
│   └── utils.py              # Logging helpers, etc.
├── out/                      # Default output folder (generated artifacts)
├── run_agent.py              # CLI entry point
├── run_agent.sh              # Convenience runner
├── requirements.txt
└── LICENSE
```
