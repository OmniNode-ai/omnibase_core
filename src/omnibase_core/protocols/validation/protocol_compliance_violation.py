"""
Protocol definition for representing a detected compliance violation.

This module provides the ProtocolComplianceViolation protocol which captures
complete violation information including the violated rule, location, severity,
and automated fix capabilities.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.validation.protocol_compliance_rule import (
        ProtocolComplianceRule,
    )


@runtime_checkable
class ProtocolComplianceViolation(Protocol):
    """
    Protocol for representing a detected compliance violation.

    Captures complete violation information including the violated rule,
    location, severity, and automated fix capabilities.
    """

    rule: ProtocolComplianceRule
    file_path: str
    line_number: int
    violation_text: str
    severity: str
    fix_suggestion: str
    auto_fixable: bool

    async def get_violation_summary(self) -> str:
        """
        Get a summary of the violation.

        Returns:
            Summary string
        """
        ...

    async def get_compliance_impact(self) -> str:
        """
        Get the impact of this violation on compliance.

        Returns:
            Impact description
        """
        ...


__all__ = ["ProtocolComplianceViolation"]
