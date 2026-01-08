"""
File name: config.py
Author: Luigi Saetta
Date last modified: 2025-07-02
Python Version: 3.11

Description:
    This module provides general configurations


Usage:
    Import this module into other scripts to use its functions.
    Example:
        import config

License:
    This code is released under the MIT License.

Notes:
    This is a part of a demo showing how to implement an advanced
    RAG solution as a LangGraph agent.

Warnings:
    This module is in development, may change in future versions.
"""

DEBUG = False
STREAMING = False

# OCI general

# type of OCI auth
AUTH = "API_KEY"

REGION = "eu-frankfurt-1"
SERVICE_ENDPOINT = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com"

# LLM
# this is the default model
# LLM_MODEL_ID = "xai.grok-code-fast-1"
# LLM_MODEL_ID = "xai.grok-4"
LLM_MODEL_ID = "openai.gpt-oss-120b"

TEMPERATURE = 0.0
TOP_P = 1
MAX_TOKENS = 4000

# specific configs for the Code Quality Agent

# Accepted license identifiers (you decide the vocabulary)
# Examples: "MIT", "Apache-2.0", "BSD-3-Clause"
ACCEPTED_LICENSE_TYPES = [
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
]

ENABLE_DOC_GENERATION = False
