# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumDiagnosticsMode — opt-in diagnostics behavior for unavailable skills."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDiagnosticsMode(StrValueHelper, str, Enum):
    """
    Opt-in diagnostics behavior for unavailable skills.

    When diagnostics are enabled, discovery commands (/onex:doctor or
    equivalent) list hidden/suppressed skills with structured reasons,
    giving alpha testers visibility into the scope system.

    Attributes:
        EXPLAIN: List unavailable skills with structured reasons on request.
        SILENT:  No diagnostics. Hidden skills stay invisible in all contexts.

    Example:
        >>> EnumDiagnosticsMode.EXPLAIN.value
        'explain'
    """

    EXPLAIN = "explain"
    """Emit structured reason on discovery command. Enables /onex:doctor listing."""

    SILENT = "silent"
    """No diagnostics. Suppressed skills remain invisible in all contexts."""


__all__ = ["EnumDiagnosticsMode"]
