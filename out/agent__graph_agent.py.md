# `agent/graph_agent.py`

## Overview
- Implements a **LangGraph** agent that processes a directory of Python files in a read‑only sandbox.
- The pipeline discovers `.py` files, validates file headers, scans for potential secrets, and generates documentation using an LLM.
- Results (header issues, secret findings, generated docs) are collected in an `AgentState` dataclass and summarized at the end.
- All filesystem interactions are performed through `ReadOnlySandboxFS`, guaranteeing no write access to the source tree.
- The LLM model ID is injected via a `RunnableConfig` (default taken from `agent.config.LLM_MODEL_ID`).

## Public API
| Symbol | Type | Description |
|--------|------|-------------|
| `AgentState` | `@dataclass` | Holds the mutable state passed between graph nodes (request, paths, file list, findings, docs, summary). |
| `build_graph()` | `() -> StateGraph` | Constructs and returns a compiled LangGraph representing the processing pipeline. |
| `run_agent(graph, *, root_dir: str, out_dir: str, request: str) -> Awaitable[AgentState]` | Async function | Executes the compiled graph with the supplied directories and user request, returning the final `AgentState`. |
| Helper nodes (`node_discover_files`, `node_check_headers`, `node_scan_secrets`, `node_generate_docs`, `node_finalize`) | Internal | Functions that operate on `AgentState`; they are wired into the graph but can be imported for testing. |
| `get_config_value(config, key, default=None)` | Utility | Safely extracts a configurable value from a `RunnableConfig`. |

## Key Behaviors and Edge Cases
- **Read‑only sandbox**: `ReadOnlySandboxFS` prevents accidental modification of source files; any attempt to write will raise an exception.
- **Header validation**: If `check_header` returns `ok=False`, the file path and message are stored in `state.header_issues`. No early termination – the pipeline continues for all files.
- **Secret scanning**: `scan_for_secrets` returns a list of finding objects; each is reduced to a dict (`kind`, `line`, `excerpt`). Empty results are ignored.
- **Doc generation**: Uses the LLM obtained via `get_llm`. The request string (`state.request`) is now passed to `generate_doc_for_file`, allowing context‑aware documentation.
- **Config handling**: If the `config` argument lacks a `model_id`, `get_llm` receives `None`, which should fall back to a default model inside `get_llm`.
- **Asynchronous node**: `node_generate_docs` is async; the graph compilation automatically handles the await.
- **Final summary**: Always produced, even if earlier steps found no issues; counts may be zero.

## Inputs / Outputs / Side Effects
| Component | Input | Output | Side Effects |
|-----------|-------|--------|--------------|
| `run_agent` | `root_dir`, `out_dir`, `request` (strings) | Final `AgentState` with populated fields | Logs to console; writes generated documentation files under `out_dir`. |
| `node_discover_files` | `AgentState.root_dir` | `state.file_list` (list of relative paths) | Reads directory structure via sandbox FS. |
| `node_check_headers` | `state.file_list` | `state.header_issues` (dict) | Reads each file's text; logs per file. |
| `node_scan_secrets` | `state.file_list` | `state.secrets` (dict) | Reads each file's text; logs per file. |
| `node_generate_docs` | `state.file_list`, `state.request`, `config.model_id` | `state.docs` (dict of relpath → generated doc path) | Calls LLM, writes doc files to `out_dir`. |
| `node_finalize` | All previous state fields | `state.summary` (string) | None (purely computational). |

## Usage Examples
```python
import asyncio
from agent.graph_agent import build_graph, run_agent

async def main():
    # Build the processing graph once
    graph = build_graph()

    # Run the agent on a project directory
    final_state = await run_agent(
        graph,
        root_dir="~/my_project/src",
        out_dir="~/my_project/docs",
        request="Create concise API documentation for the public functions."
    )

    # Quick inspection of results
    print(final_state.summary)
    if final_state.header_issues:
        print("Header problems:", final_state.header_issues)
    if final_state.secrets:
        print("Potential secrets found:", final_state.secrets)

asyncio.run(main())
```

## Risks / TODOs
- **Secret false positives**: The `scan_for_secrets` heuristic may flag benign strings; downstream handling should verify findings before remediation.
- **LLM cost & latency**: Documentation generation invokes an external LLM per file; large codebases could incur significant runtime and API costs.
- **Config robustness**: Missing or malformed `model_id` in the config currently defaults to `None`; consider explicit validation and fallback handling.
- **Error propagation**: Node functions currently propagate exceptions (e.g., I/O errors) which abort the whole graph. Adding graceful degradation (e.g., continue on read errors) could improve resilience.
- **Testing of sandbox FS**: Ensure `ReadOnlySandboxFS` correctly mirrors permission semantics across platforms.
