# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Projection exposure⇄column drift severity and kind enums (OMN-13663)."""

from __future__ import annotations

from enum import StrEnum


class EnumProjectionDriftSeverity(StrEnum):
    """Severity of a projection exposure⇄column drift finding."""

    ERROR = "error"
    WARN = "warn"


class EnumProjectionDriftKind(StrEnum):
    """Classification of a projection exposure⇄column drift finding."""

    MISSING_COLUMN = "missing_column"
    OMITTED_COLUMN = "omitted_column"
