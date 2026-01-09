"""
File name: graph_agent.py
Author: Luigi Saetta
Date last modified: 2025-12-14
Python Version: 3.11

License:
    MIT

Description:
    LangGraph agent that runs a pipeline over local Python files (read-only access),
    producing outputs elsewhere.

Usage:
    from agent.graph_agent import build_graph, run_agent

    graph = build_graph()
    result = await run_agent(graph, root_dir="...", out_dir="...", request="...")
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

from agent.fs_ro import ReadOnlySandboxFS
from agent.header_rules import check_header
from agent.secrets_scan import scan_for_secrets
from agent.docgen import generate_doc_for_file
from agent.docgen_utils import call_llm_normalized
from agent.oci_models import get_llm
from agent.docgen_prompt import REPORT_PROMPT
from agent.license_check import check_license
from agent.pii_scan import scan_for_pii
from agent.header_fix import generate_header_snippet
from agent.config import ACCEPTED_LICENSE_TYPES

from agent.utils import get_console_logger

from agent.config import LLM_MODEL_ID, ENABLE_DOC_GENERATION

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

    license_ok: bool = True
    license_info: dict[str, Any] = field(default_factory=dict)  # details of check

    # PII
    # relpath -> findings
    pii_findings: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    pii_failures: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict
    )  # subset severity=fail
    pii_warnings: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict
    )  # subset severity=warn

    header_fixes: dict[str, str] = field(default_factory=dict)  # relpath -> header snippet file path


# ---- Nodes ----


def node_discover_files(state: AgentState) -> AgentState:
    """
    Discover all source files under the root directory.

    Modified to use ReadOnlySandboxFS.
    """
    fs = ReadOnlySandboxFS(Path(state.root_dir))
    source_files = fs.list_source_files()
    state.file_list = [str(fs.relpath(p)) for p in source_files]

    logger.info("")
    logger.info("Discovered %d source files.", len(state.file_list))
    logger.info(state.file_list)
    logger.info("")

    return state


def node_check_headers(state: AgentState) -> AgentState:
    fs = ReadOnlySandboxFS(Path(state.root_dir))
    issues: dict[str, str] = {}

    for rel in state.file_list:

        logger.info("Checking headers for: %s...", rel)

        src = fs.read_text(rel)
        res = check_header(src, path=fs._resolve_under_root(Path(rel)))
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


def node_scan_pii(state: AgentState) -> AgentState:
    fs = ReadOnlySandboxFS(Path(state.root_dir))

    all_findings: dict[str, list[dict[str, Any]]] = {}
    failures: dict[str, list[dict[str, Any]]] = {}
    warnings: dict[str, list[dict[str, Any]]] = {}

    for rel in state.file_list:
        logger.info("Scanning PII for: %s...", rel)
        src = fs.read_text(rel)

        found = scan_for_pii(src)
        if not found:
            continue

        payload = [
            {
                "kind": f.kind,
                "severity": f.severity,
                "line": f.line,
                "excerpt": f.excerpt,  # already masked
                "confidence": f.confidence,
            }
            for f in found
        ]
        all_findings[rel] = payload

        fail_payload = [p for p in payload if p["severity"] == "fail"]
        warn_payload = [p for p in payload if p["severity"] == "warn"]

        if fail_payload:
            failures[rel] = fail_payload
        if warn_payload:
            warnings[rel] = warn_payload

    state.pii_findings = all_findings
    state.pii_failures = failures
    state.pii_warnings = warnings

    return state


async def node_generate_docs(
    state: AgentState, *, config: RunnableConfig
) -> AgentState:
    if not ENABLE_DOC_GENERATION:
        # doc generation disabled
        logger.info("Document generation is disabled. Skipping this step.")
        return state

    fs = ReadOnlySandboxFS(Path(state.root_dir))

    # get model_id from config
    model_id = get_config_value(config, "model_id")

    llm = get_llm(model_id=model_id)
    out_dir = Path(state.out_dir).expanduser().resolve()

    docs: dict[str, str] = {}

    for rel in state.file_list:

        # added this try-except to avoid stopping the whole process if one file fails
        # one situation where it fails is where the file contains secret info
        # that the LLM refuses to process
        try:
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
        except Exception as e:
            logger.error("Doc generation failed for %s: %s", rel, e)
            docs[rel] = ""

    state.docs = docs
    return state


def node_check_license(state: AgentState) -> AgentState:
    """
    Check that a license file exists and the license type is accepted.
    """
    fs = ReadOnlySandboxFS(Path(state.root_dir))

    # We want a list of all repo files (not just python source files).
    # If your ReadOnlySandboxFS doesn't expose this, see note below.
    def _list_all_files() -> list[str]:
        return [str(fs.relpath(p)).replace("\\", "/") for p in fs.list_all_files()]

    res = check_license(
        list_files=_list_all_files,
        read_text=fs.read_text,
        accepted_types=ACCEPTED_LICENSE_TYPES,
    )

    state.license_ok = res.ok
    state.license_info = {
        "ok": res.ok,
        "found_file": res.found_file,
        "detected_type": res.detected_type,
        "message": res.message,
    }

    if res.ok:
        logger.info("License check OK: %s", res.message)
    else:
        logger.warning("License check FAILED: %s", res.message)

    return state

async def node_generate_header_fixes(
    state: AgentState, *, config: RunnableConfig
) -> AgentState:
    if not state.header_issues:
        return state

    fs = ReadOnlySandboxFS(Path(state.root_dir))

    model_id = get_config_value(config, "model_id")
    llm = get_llm(model_id=model_id)

    out_dir = Path(state.out_dir).expanduser().resolve()
    fixes_dir = out_dir / "header_fixes"
    fixes_dir.mkdir(parents=True, exist_ok=True)

    fixes: dict[str, str] = {}

    for rel in state.header_issues.keys():
        logger.info("Generating header snippet for: %s...", rel)

        try:
            detected_license = (getattr(state, "license_info", {}) or {}).get("detected_type") or "Unknown"

            header = await generate_header_snippet(
                llm=llm,
                relpath=Path(rel),
                license_hint=detected_license,
                pyver="3.11",
            )

            # Create a mirrored directory structure under header_fixes
            target = fixes_dir / (Path(rel).as_posix() + ".header.py")
            target.parent.mkdir(parents=True, exist_ok=True)

            # File contains ONLY the header docstring
            target.write_text(header, encoding="utf-8")

            fixes[rel] = str(target)

        except Exception as e:
            logger.error("Header snippet generation failed for %s: %s", rel, e)
            fixes[rel] = ""

    state.header_fixes = fixes
    return state



async def node_finalize(state: AgentState, *, config: RunnableConfig) -> AgentState:
    # A compact summary you can print/store elsewhere
    hard_pii = sum(len(v) for v in state.pii_failures.values())
    warn_pii = sum(len(v) for v in state.pii_warnings.values())

    state.summary = (
        f"Processed {len(state.file_list)} files.\n"
        f"License: {'OK' if state.license_ok else 'FAILED'}\n"
        f"Header issues: {len(state.header_issues)} files.\n"
        f"Secret findings: {len(state.secrets)} files.\n"
        f"PII hard failures: {hard_pii} findings in {len(state.pii_failures)} files.\n"
        f"PII warnings: {warn_pii} findings in {len(state.pii_warnings)} files.\n"
        f"Docs generated: {len(state.docs)} files.\n"
        f"Output dir: {state.out_dir}\n"
    )

    # generate a report in markdown format
    model_id = get_config_value(config, "model_id")
    llm = get_llm(model_id=model_id)

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    prompt_template = REPORT_PROMPT
    prompt = prompt_template.format(
        now_datetime=now_iso,
        num_files=len(state.file_list),
        header_issues=state.header_issues,
        secret_issues=state.secrets,
        license_check=getattr(state, "license_info", {}),
        pii_hard_failures=getattr(state, "pii_failures", {}),
        pii_warnings=getattr(state, "pii_warnings", {}),
    )

    text, _ = await call_llm_normalized(llm, prompt)

    logger.info("")
    logger.info("Final report: %s", text)

    # save to file
    current_day = now_iso[:10]
    out_dir = Path(state.out_dir)
    out_path = out_dir / f"report_{current_day}.md"
    data = (text.rstrip() + "\n").encode("utf-8")
    out_path.write_bytes(data)

    return state


# ---- Graph ----


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("discover_files", node_discover_files)

    # sequentially here we process all the files discovered
    g.add_node("check_headers", node_check_headers)
    g.add_node("scan_secrets", node_scan_secrets)
    g.add_node("generate_docs", node_generate_docs)
    g.add_node("check_license", node_check_license)
    g.add_node("scan_pii", node_scan_pii)
    g.add_node("generate_header_fixes", node_generate_header_fixes)
    g.add_node("finalize", node_finalize)

    g.set_entry_point("discover_files")
    g.add_edge("discover_files", "check_license")
    g.add_edge("check_license", "check_headers")
    g.add_edge("check_headers", "generate_header_fixes")
    g.add_edge("generate_header_fixes", "scan_secrets")
    g.add_edge("scan_secrets", "scan_pii")
    g.add_edge("scan_pii", "generate_docs")
    g.add_edge("generate_docs", "finalize")
    g.add_edge("finalize", END)

    return g.compile()


async def run_agent(graph, *, root_dir: str, out_dir: str, request: str) -> AgentState:
    # here we define the initial state
    state = AgentState(request=request, root_dir=root_dir, out_dir=out_dir)

    # here we define the config for the run of the agent
    cfg = {"configurable": {"model_id": LLM_MODEL_ID}}

    logger.info("")
    logger.info("Running agent with config: %s...", cfg)
    logger.info("")

    # LangGraph returns the final state
    final_state = await graph.ainvoke(state, config=cfg)

    return final_state
