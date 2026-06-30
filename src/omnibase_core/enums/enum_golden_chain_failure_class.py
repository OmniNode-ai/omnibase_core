# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Formal golden-chain replay failure classes (OMN-13499)."""

from __future__ import annotations

from enum import Enum


class EnumGoldenChainFailureClass(str, Enum):
    """Named failure classes raised by the canonical golden-chain replay harness."""

    INVALID_FIXTURE = "INVALID_FIXTURE"
    EMPTY_COMPLETION = "EMPTY_COMPLETION"
    ECHO_COMPLETION = "ECHO_COMPLETION"
    ROUTE_NOT_RESOLVED = "ROUTE_NOT_RESOLVED"
    REQUEST_HASH_MISMATCH = "REQUEST_HASH_MISMATCH"


__all__ = ["EnumGoldenChainFailureClass"]
