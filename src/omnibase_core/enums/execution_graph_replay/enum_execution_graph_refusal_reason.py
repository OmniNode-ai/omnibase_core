# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay refusal reason vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphRefusalReason(StrEnum):
    """Closed execution-graph replay refusal reason values."""

    CORRELATION_NOT_FOUND = "correlation_not_found"
    CORRELATION_AMBIGUOUS = "correlation_ambiguous"
    MULTIPLE_CHAIN_HEADS = "multiple_chain_heads"
    ENVELOPE_ID_COLLISION = "envelope_id_collision"
    PARENT_CYCLE = "parent_cycle"
    UNSUPPORTED_VERSION = "unsupported_version"
    INVALID_EVIDENCE = "invalid_evidence"


__all__ = ["EnumExecutionGraphRefusalReason"]
