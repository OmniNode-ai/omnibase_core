"""
Protocol definition for compliance validation in ONEX systems.

This module provides the ProtocolComplianceValidator protocol which validates
compliance with ONEX standards, architectural patterns, and ecosystem requirements.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.validation.protocol_architecture_compliance import (
        ProtocolArchitectureCompliance,
    )
    from omnibase_core.protocols.validation.protocol_compliance_report import (
        ProtocolComplianceReport,
    )
    from omnibase_core.protocols.validation.protocol_compliance_rule import (
        ProtocolComplianceRule,
    )
    from omnibase_core.protocols.validation.protocol_compliance_violation import (
        ProtocolComplianceViolation,
    )
    from omnibase_core.protocols.validation.protocol_onex_standards import (
        ProtocolONEXStandards,
    )
    from omnibase_core.protocols.validation.protocol_validation_result import (
        ProtocolValidationResult,
    )


@runtime_checkable
class ProtocolComplianceValidator(Protocol):
    """
    Protocol interface for compliance validation in ONEX systems.

    Validates compliance with ONEX standards, architectural patterns,
    and ecosystem requirements.
    """

    onex_standards: ProtocolONEXStandards
    architecture_rules: ProtocolArchitectureCompliance
    custom_rules: list[ProtocolComplianceRule]
    strict_mode: bool

    async def validate_file_compliance(
        self, file_path: str, content: str | None = None
    ) -> ProtocolComplianceReport:
        """Validate a file for compliance."""
        ...

    async def validate_repository_compliance(
        self, repository_path: str, file_patterns: list[str] | None = None
    ) -> list[ProtocolComplianceReport]:
        """Validate a repository for compliance."""
        ...

    async def validate_onex_naming(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolComplianceViolation]:
        """Validate ONEX naming conventions."""
        ...

    async def validate_architecture_compliance(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolComplianceViolation]:
        """Validate architecture compliance."""
        ...

    async def validate_directory_structure(
        self, repository_path: str
    ) -> list[ProtocolComplianceViolation]:
        """Validate directory structure."""
        ...

    async def validate_dependency_compliance(
        self, file_path: str, imports: list[str]
    ) -> list[ProtocolComplianceViolation]:
        """Validate dependency compliance."""
        ...

    async def aggregate_compliance_results(
        self, reports: list[ProtocolComplianceReport]
    ) -> ProtocolValidationResult:
        """Aggregate compliance results into a validation result."""
        ...

    def add_custom_rule(self, rule: ProtocolComplianceRule) -> None:
        """Add a custom compliance rule."""
        ...

    def configure_onex_standards(self, standards: ProtocolONEXStandards) -> None:
        """Configure ONEX standards."""
        ...

    async def get_compliance_summary(
        self, reports: list[ProtocolComplianceReport]
    ) -> str:
        """Get a summary of compliance reports."""
        ...


__all__ = ["ProtocolComplianceValidator"]
