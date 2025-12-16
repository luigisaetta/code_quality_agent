# `run_agent.py`

## Overview
- Parses command‑line arguments for a source root directory, an output directory, and a user request.  
- Builds a graph representation of the codebase using `agent.graph_agent.build_graph`.  
- Executes the agent asynchronously via `agent.graph_agent.run_agent`, passing the graph and the supplied arguments.  
- Prints a concise summary of the agent’s work, any header‑related issues, and any discovered secrets.  
- Designed to be run as a standalone script (`python run_agent.py …`).  

## Public API
| Name | Type | Description |
|------|------|-------------|
| `main()` | function | Entry point invoked when the module is executed as a script. Handles argument parsing, graph construction, agent execution, and result reporting. |
| `logger` | `logging.Logger` | Console logger obtained from `agent.utils.get_console_logger`. Primarily used for internal debugging (not directly exported). |

*Note:* The module also imports `build_graph` and `run_agent` from `agent.graph_agent`, which are part of the public API of that package but are not re‑exported here.

## Key Behaviors and Edge Cases
- **Argument validation** – `--root` and `--out` are required; the script will exit with an error message if they are missing.  
- **Default request** – If `--request` is omitted, a built‑in request string (“Check only headers and scan secrets…”) is used.  
- **Asynchronous execution** – The agent runs inside an `asyncio` event loop (`asyncio.run`). Any exception raised by `run_agent` propagates and terminates the script.  
- **Result handling** – The returned status dictionary (`st`) is expected to contain:
  - `summary` (string) – printed under “AGENT SUMMARY”.
  - `header_issues` (dict) – optional; each key/value pair is printed if present.
  - `secrets` (dict) – optional; each file path maps to a list of findings, each with `line`, `kind`, and `excerpt`.  
- **Graceful missing keys** – The script checks for the presence of `header_issues` and `secrets` before iterating, avoiding `KeyError`s.  

## Inputs / Outputs and Side Effects
| Aspect | Details |
|--------|---------|
| **Inputs** | - `--root` : path to a read‑only directory containing Python files.<br>- `--out` : path to a directory where the agent may write generated artifacts.<br>- `--request` : free‑form text describing the analysis request (defaults to a header/secret scan). |
| **Outputs** | - Console output: summary, header issues, and secret findings.<br>- Potential files written to the `--out` directory (depends on the agent’s implementation). |
| **Side Effects** | - Reads files under the root directory.<br>- May create/write files under the output directory.<br>- Logs to the console via the imported logger. |

## Usage Examples
```bash
# Basic usage – scan a codebase for header problems and secrets
python run_agent.py --root /path/to/project/src --out /tmp/agent-output
```

```bash
# Provide a custom request
python run_agent.py \
    --root ./my_code \
    --out ./agent_results \
    --request "Identify all TODO comments and any hard‑coded API keys."
```

## Risks / TODOs
- **No secrets detected in this script** – the only hard‑coded string is the default request text, which does not contain credentials.  
- **Error handling** – the script currently lets any exception from `run_agent` crash the process; consider adding try/except to present user‑friendly messages.  
- **Directory existence** – the script assumes `--out` exists or is creatable; adding a check/creation step would improve robustness.  
- **Logging level** – the logger is instantiated but never used; either integrate logging statements or remove the unused import.
