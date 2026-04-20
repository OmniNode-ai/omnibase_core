# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Probe status enum (OMN-9322)."""

from __future__ import annotations

from enum import StrEnum


class EnumProbeStatus(StrEnum):
    """Outcome of a single probe execution."""

    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    SKIPPED = "SKIPPED"
