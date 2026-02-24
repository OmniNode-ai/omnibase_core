# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Command Risk Level Enum.

Defines risk levels for CLI commands in the registry-driven CLI system.
Risk level governs HITL (human-in-the-loop) enforcement and audit requirements.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliCommandRisk(StrValueHelper, str, Enum):
    """
    Risk classifications for CLI commands advertised via cli.contribution.v1.

    Controls whether a command requires human confirmation before execution
    and what level of audit logging is applied.

    Values:
        LOW: Safe, read-only operations. No HITL required.
        MEDIUM: State-modifying but reversible. HITL optional.
        HIGH: Destructive or irreversible operations. HITL recommended.
        CRITICAL: High-impact system operations. HITL required.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def requires_hitl_by_default(cls, risk: "EnumCliCommandRisk") -> bool:
        """Return True if this risk level requires HITL by default."""
        return risk == cls.CRITICAL

    @classmethod
    def is_destructive(cls, risk: "EnumCliCommandRisk") -> bool:
        """Return True if this risk level is considered destructive."""
        return risk in {cls.HIGH, cls.CRITICAL}


__all__ = ["EnumCliCommandRisk"]
