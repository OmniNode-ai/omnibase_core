# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Violation severity enumeration for corpus replay aggregation.

Defines the severity levels for invariant violations detected during
corpus replay, used by ModelEvidenceSummary for categorizing issues.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumViolationSeverity(StrValueHelper, str, Enum):
    """Severity levels for invariant violations."""

    CRITICAL = "critical"
    """Critical violations that must be addressed immediately."""

    WARNING = "warning"
    """Warning-level violations that should be reviewed."""

    INFO = "info"
    """Informational violations for awareness."""


__all__ = ["EnumViolationSeverity"]
