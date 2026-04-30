# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""AST diff severity and change-kind enums (OMN-10371)."""

from __future__ import annotations

from enum import StrEnum


class EnumDiffSeverity(StrEnum):
    """Risk severity for a code-symbol change detected by AST diff."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnumChangeKind(StrEnum):
    """Classifier for the kind of change made to a symbol."""

    SIGNATURE_CHANGE = "signature_change"
    API_CHANGE = "api_change"
    GUARD_REMOVED = "guard_removed"
    DELETED_FUNCTION = "deleted_function"
    LOGIC_CHANGE = "logic_change"
    NEW_FUNCTION = "new_function"
    REFACTOR = "refactor"
    COSMETIC = "cosmetic"
