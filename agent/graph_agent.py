"""
File name: graph_agent.py
Author: Luigi Saetta
Date last modified: 2025-12-14
Python Version: 3.11

Description:
    LangGraph agent that runs a pipeline over local Python files (read-only access),
    producing outputs elsewhere.

Usage:
    from agent.graph_agent import build_graph, run_agent

    graph = build_graph()
    result = await run_agent(graph, root_dir="...", out_dir="...", request="...")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

from agent.fs_ro import ReadOnlySandboxFS
from agent.header_rules import check_header
from agent.secrets_scan import scan_for_secrets
from agent.docgen import generate_doc_for_file
from agent.oci_models import get_llm
from agent.utils import get_console_logger

from agent.config import LLM_MODEL_ID

logger = get_console_logger()


# ---- Helpers ----
def get_config_value(
    config: RunnableConfig | None,
    key: str,
    default: Any = None,
) -> Any:
    if not config:
        return default
    configurable = config.get("configurable")
    if not configurable:
        return default
    return configurable.get(key, default)

# ---- State ----
@dataclass
class AgentState:
    request: str
    root_dir: str
    out_dir: str

    file_list: list[str] = field(default_factory=list)

    header_issues: dict[str, str] = field(default_factory=dict)  # relpath -> message
    secrets: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict
    )  # relpath -> findings
    docs: dict[str, str] = field(default_factory=dict)  # relpath -> doc out path

    summary: str = ""


# ---- Nodes ----


def node_discover_files(state: AgentState) -> AgentState:
    fs = ReadOnlySandboxFS(Path(state.root_dir))
    py_files = fs.list_python_files()
    state.file_list = [str(fs.relpath(p)) for p in py_files]
    return state


def node_check_headers(state: AgentState) -> AgentState:
    fs = ReadOnlySandboxFS(Path(state.root_dir))
    issues: dict[str, str] = {}

    for rel in state.file_list:

        logger.info("Checking headers for: %s...", rel)

        src = fs.read_text(rel)
        res = check_header(src)
        if not res.ok:
            issues[rel] = res.message

    state.header_issues = issues
    return state


def node_scan_secrets(state: AgentState) -> AgentState:
    fs = ReadOnlySandboxFS(Path(state.root_dir))
    all_findings: dict[str, list[dict[str, Any]]] = {}

    for rel in state.file_list:

        logger.info("Scanning secrets for: %s...", rel)

        src = fs.read_text(rel)
        findings = scan_for_secrets(src)
        if findings:
            all_findings[rel] = [
                {"kind": f.kind, "line": f.line, "excerpt": f.excerpt} for f in findings
            ]

    state.secrets = all_findings
    return state


async def node_generate_docs(state: AgentState, *, config: RunnableConfig) -> AgentState:
    fs = ReadOnlySandboxFS(Path(state.root_dir))

    # get model_id from config
    model_id = get_config_value(config, "model_id")

    llm = get_llm(model_id=model_id)
    out_dir = Path(state.out_dir).expanduser().resolve()

    docs: dict[str, str] = {}

    for rel in state.file_list:

        logger.info("Generating doc for: %s...", rel)

        src = fs.read_text(rel)
        res = await generate_doc_for_file(
            llm=llm,
            relpath=Path(rel),
            source=src,
            out_dir=out_dir,
            # ✅ NEW: now docgen uses the request
            request=state.request,   
        )
        docs[rel] = str(res.out_path)

    state.docs = docs
    return state


def node_finalize(state: AgentState) -> AgentState:
    # A compact summary you can print/store elsewhere
    state.summary = (
        f"Processed {len(state.file_list)} files.\n"
        f"Header issues: {len(state.header_issues)} files.\n"
        f"Secret findings: {len(state.secrets)} files.\n"
        f"Docs generated: {len(state.docs)} files.\n"
        f"Output dir: {state.out_dir}\n"
    )
    return state


# ---- Graph ----


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("discover_files", node_discover_files)
    
    # sequentially here we process all the files discovered
    g.add_node("check_headers", node_check_headers)
    g.add_node("scan_secrets", node_scan_secrets)
    g.add_node("generate_docs", node_generate_docs)
    g.add_node("finalize", node_finalize)

    g.set_entry_point("discover_files")
    g.add_edge("discover_files", "check_headers")
    g.add_edge("check_headers", "scan_secrets")
    g.add_edge("scan_secrets", "generate_docs")
    g.add_edge("generate_docs", "finalize")
    g.add_edge("finalize", END)

    return g.compile()


async def run_agent(graph, *, root_dir: str, out_dir: str, request: str) -> AgentState:
    # here we define the initial state
    state = AgentState(request=request, root_dir=root_dir, out_dir=out_dir)
    
    cfg = {"configurable": {"model_id": LLM_MODEL_ID}}

    logger.info("")
    logger.info("Running agent with config: %s...", cfg)
    logger.info("")
    
    # LangGraph returns the final state
    final_state = await graph.ainvoke(state, config=cfg)
    
    return final_state
