# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Drift type enumeration for the Intent Intelligence Framework.

Defines the canonical set of drift types used by the drift detection
subsystem to categorize observed divergence from classified session intent.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDriftType(StrValueHelper, str, Enum):
    """Canonical drift type categories for intent drift detection.

    Values:
        TOOL_MISMATCH: Tools used do not match the expected pattern for the intent class.
        FILE_SURFACE: File access pattern diverged from the declared intent.
        SCOPE_EXPANSION: Scope has grown beyond the original intent boundary.
    """

    TOOL_MISMATCH = "tool_mismatch"
    """Tools used do not match expected pattern for the intent class."""

    FILE_SURFACE = "file_surface"
    """File access pattern diverged from intent."""

    SCOPE_EXPANSION = "scope_expansion"
    """Scope has grown beyond original intent boundary."""


__all__ = ["EnumDriftType"]
