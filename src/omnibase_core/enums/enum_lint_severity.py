# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Lint severity levels emitted by mypy and ruff.

Narrower than `EnumSeverity` (which spans DEBUG..FATAL for logging);
`EnumLintSeverity` matches the severity vocabulary that static-analysis
tools actually emit.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumLintSeverity(StrValueHelper, str, Enum):
    """Severity as reported by static analysis tools (mypy, ruff)."""

    ERROR = "error"
    NOTE = "note"
    WARNING = "warning"


__all__ = ["EnumLintSeverity"]
