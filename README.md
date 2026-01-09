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

## Setup
1. Create a python 3.11+ environment

For example, 
```
conda create -n code_quality_agent python==3.11
```

activate the environment. If you're using conda:
```
conda activate code_quality_agent
```

2. Install the following python libraries
```
pip install oci -U
pip install langchain -U
pip install langchain-oci -U
pip install langgraph -U
```

3. Create a config_private.py file

Start from the template provided in the repository and create a **config_private.py** file.
Put in the file your compartment's OCID.


4. Have your local OCI config setup

Setup under $HOME/.oci
See: https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm

5. Set policies to use Generative AI

See: https://docs.oracle.com/en-us/iaas/Content/generative-ai/iam-policies.htm

Ask your tenancy admin for help.
