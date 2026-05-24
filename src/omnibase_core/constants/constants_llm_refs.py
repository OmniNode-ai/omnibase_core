# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# ============================================================
# AUTO-GENERATED — do not edit by hand.
# Source:
#   omnibase_infra/contracts/llm_endpoints.yaml
#   omnimarket/src/omnimarket/data/model_registry/model_registry_v1.yaml
# Generator: scripts/generate_llm_refs.py (OMN-11932)
# Regenerate: uv run python scripts/generate_llm_refs.py
# ============================================================

"""
Typed compile-time constants for LLM model keys and endpoint slot references.

Use these instead of bare string literals so that typos become import errors
and IDEs can autocomplete slot/model identifiers.

LogicalModelKey — canonical model identifiers from model_registry_v1.yaml.
EndpointRef     — canonical slot IDs from llm_endpoints.yaml (all statuses).
"""

from __future__ import annotations

from enum import StrEnum


class LogicalModelKey(StrEnum):
    """Canonical model identifiers from model_registry_v1.yaml."""

    QWEN3_CODER_30B = "qwen3-coder-30b"
    DEEPSEEK_R1_14B = "deepseek-r1-14b"
    DEEPSEEK_R1_32B = "deepseek-r1-32b"
    QWEN3_NEXT_80B = "qwen3-next-80b"
    LLAMA_3_3_70B_FREE = "llama-3.3-70b-free"
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    CLAUDE_OPUS_4_6 = "claude-opus-4-6"


class EndpointRef(StrEnum):
    """Canonical slot IDs from llm_endpoints.yaml (all statuses included)."""

    CODER_5090 = "coder-5090"
    CODER_FAST_4090 = "coder-fast-4090"
    EMBEDDINGS_201 = "embeddings-201"
    REASONING_DEEPSEEK_32B = "reasoning-deepseek-32b"
    REASONING_MOE_35B = "reasoning-moe-35b"
    EMBEDDINGS_200 = "embeddings-200"
    SECOND_OPINION_GEMMA = "second-opinion-gemma"
    VISION_PLANNED = "vision-planned"
    STT_PLANNED = "stt-planned"
    TTS_PLANNED = "tts-planned"
    RERANKER_PLANNED = "reranker-planned"
