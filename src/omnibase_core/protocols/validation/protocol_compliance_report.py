"""
Protocol definition for comprehensive compliance report.

This module provides the ProtocolComplianceReport protocol which contains
all violations and compliance scores for a file or project.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.validation.protocol_compliance_violation import (
        ProtocolComplianceViolation,
    )


@runtime_checkable
class ProtocolComplianceReport(Protocol):
    """
    Protocol for comprehensive compliance report.

    Contains all violations and compliance scores for a file or project.
    """

    file_path: str
    violations: list[ProtocolComplianceViolation]
    onex_compliance_score: float
    architecture_compliance_score: float
    overall_compliance: bool
    critical_violations: int
    recommendations: list[str]

    async def get_compliance_summary(self) -> str:
        """
        Get a summary of the compliance report.

        Returns:
            Summary string
        """
        ...

    async def get_priority_fixes(self) -> list[ProtocolComplianceViolation]:
        """
        Get violations prioritized for fixing.

        Returns:
            List of priority violations
        """
        ...


__all__ = ["ProtocolComplianceReport"]
