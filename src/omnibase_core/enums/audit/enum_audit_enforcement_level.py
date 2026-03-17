# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnumAuditEnforcementLevel - Enforcement level for context integrity auditing.

Determines how context integrity violations are handled during task dispatch
and execution. Four levels from permissive (log only) to paranoid (block and
rollback).

Design:
    Four enforcement levels support different deployment contexts:
    - PERMISSIVE: Log violations but take no action (development/exploration)
    - WARN: Log violations and emit alerts (staging/gradual rollout)
    - STRICT: Block violating operations (production enforcement)
    - PARANOID: Block, rollback, and alert (critical path enforcement)

Related:
    - OMN-5230: Context Integrity Audit & Enforcement
    - ModelContextIntegritySubcontract: Uses this enum for enforcement_level
    - EnumEnforcementMode: Similar pattern for replay safety

.. versionadded:: 0.29.0
"""

from __future__ import annotations

__all__ = ["EnumAuditEnforcementLevel"]

from enum import Enum


class EnumAuditEnforcementLevel(str, Enum):
    """
    Enforcement level for context integrity auditing.

    Determines how the audit system handles violations of context integrity
    constraints (budget overruns, scope violations, unauthorized tool usage).

    Values:
        PERMISSIVE: Log violations but take no action. Use in development
            or exploration where violations are informational only.
        WARN: Log violations and emit alert events. Use during gradual
            rollout or staging where visibility is needed without blocking.
        STRICT: Block operations that violate constraints. Use in production
            where enforcement is required but rollback is not needed.
        PARANOID: Block violations, trigger rollback, and emit alerts. Use
            for critical path enforcement where violations must be fully
            undone and escalated.

    Example:
        >>> from omnibase_core.enums.audit import EnumAuditEnforcementLevel
        >>> level = EnumAuditEnforcementLevel.STRICT
        >>> level.is_blocking
        True
        >>> level.should_rollback
        False
        >>> EnumAuditEnforcementLevel.PARANOID.should_rollback
        True
    """

    PERMISSIVE = "permissive"
    WARN = "warn"
    STRICT = "strict"
    PARANOID = "paranoid"

    @property
    def is_blocking(self) -> bool:
        """Whether this level blocks violating operations.

        Returns:
            True for STRICT and PARANOID levels.
        """
        return self in (
            EnumAuditEnforcementLevel.STRICT,
            EnumAuditEnforcementLevel.PARANOID,
        )

    @property
    def should_rollback(self) -> bool:
        """Whether this level triggers rollback on violation.

        Returns:
            True for PARANOID level only.
        """
        return self == EnumAuditEnforcementLevel.PARANOID

    @property
    def should_alert(self) -> bool:
        """Whether this level emits alert events on violation.

        Returns:
            True for WARN and PARANOID levels.
        """
        return self in (
            EnumAuditEnforcementLevel.WARN,
            EnumAuditEnforcementLevel.PARANOID,
        )
