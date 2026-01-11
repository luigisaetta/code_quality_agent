# Code Quality Agent

A lightweight **LangGraph-based** agent that scans a local codebase (read-only) to:

- ✅ **Check file headers** against a simple template policy
- ✅ **Scan for secrets** (heuristic patterns + suspicious assignments)
- ✅ **Check for license**
- ✅ **Check for dependencies licenses**
- ✅ **Generate header fixes**
- ✅ **Generate per-file documentation** (optional) in Markdown via an LLM (OCI GenAI via LangChain)

It produces artifacts in a separate output folder (no in-place edits).


---

## Features

### Header policy checks
For each discovered source file, the agent validates that a header block contains:

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

### License check
Check that an approved LICENSE file is provided.

### Header fix generation
For each of the files where the header check fails, provide the snippet suggested to use.
- modifiy the Author field
- check the rest.

### Per-file doc generation (LLM)
For each Python file, the agent can generate Markdown documentation with sections such as:
- overview
- public API
- behaviors/edge cases
- side effects
- usage examples
- risks/TODOs

### Report generation
A final summary report is also generated, in Markdown.

### Languages supported
For now, tests have been done using:
- Python

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

## How-to use it
Modify the [run_agent.sh](./run_agent.sh) file. 

Change the params:
- root (root directory for all the files to be scanned)
- out
with the full path to input_dir and output_dir

run 
```
run_agent.sh
```

