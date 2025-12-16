"""
trst OCI OpenAI for LanGraph
"""
import asyncio
from typing import Any, Optional
from langchain_core.messages import HumanMessage

from agent.oci_models import get_llm
from agent.utils import get_console_logger
from agent.config import LLM_MODEL_ID

logger = get_console_logger()

async def _call_llm_normalized(llm: Any, prompt: str) -> tuple[str, Optional[str]]:
    """
    Call the LLM with best-effort normalization across common return shapes.
    Returns (text, model_hint).
    """
    try:
        if hasattr(llm, "ainvoke"):
            logger.info("Invoking llm.invoke...")
            resp = llm.invoke([HumanMessage(content=prompt)])
        else:
            # If llm is an awaitable callable
            resp = await llm([HumanMessage(content=prompt)])
    except Exception as e:
        raise RuntimeError(f"LLM invocation failed: {e}") from e

    return resp

llm = get_llm(LLM_MODEL_ID, max_tokens=1024)

async def main():
    resp = await _call_llm_normalized(llm, "hello")
    print("")
    print(resp)

asyncio.run(main())   