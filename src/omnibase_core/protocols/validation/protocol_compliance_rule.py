"""
Protocol definition for ONEX compliance rule definition and checking.

This module provides the ProtocolComplianceRule protocol which defines a single
compliance rule with validation logic, severity classification, and automated
fix suggestions.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProtocolComplianceRule(Protocol):
    """
    Protocol for ONEX compliance rule definition and checking.

    Defines a single compliance rule with validation logic, severity
    classification, and automated fix suggestions.
    """

    rule_id: UUID
    rule_name: str
    category: str
    severity: str
    description: str
    required_pattern: str
    violation_message: str

    async def check_compliance(self, content: str, context: str) -> bool:
        """
        Check if content complies with this rule.

        Args:
            content: The content to check
            context: Context for the check

        Returns:
            True if compliant, False otherwise
        """
        ...

    async def get_fix_suggestion(self) -> str:
        """
        Get a fix suggestion for violations.

        Returns:
            Fix suggestion string
        """
        ...


__all__ = ["ProtocolComplianceRule"]
