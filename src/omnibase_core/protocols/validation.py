"""
Core-native validation protocols.

This module provides protocol definitions for validation operations
including compliance validation and validation results. These are
Core-native equivalents of the SPI validation protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

from omnibase_core.protocols.base import ContextValue

if TYPE_CHECKING:
    pass


# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
P = TypeVar("P")


# =============================================================================
# Validation Error Protocol
# =============================================================================


@runtime_checkable
class ProtocolValidationError(Protocol):
    """
    Protocol for validation error objects.

    Represents a single validation error with type, message, context,
    and severity information.
    """

    error_type: str
    message: str
    context: dict[str, ContextValue]
    severity: str

    def __str__(self) -> str:
        """Return string representation of the error."""
        ...


# =============================================================================
# Validation Result Protocol
# =============================================================================


@runtime_checkable
class ProtocolValidationResult(Protocol):
    """
    Protocol for validation result objects.

    Contains the overall validation status, errors, and warnings.
    """

    is_valid: bool
    protocol_name: str
    implementation_name: str
    errors: list[ProtocolValidationError]
    warnings: list[ProtocolValidationError]

    def add_error(
        self,
        error_type: str,
        message: str,
        context: dict[str, ContextValue] | None = None,
        severity: str | None = None,
    ) -> None:
        """
        Add an error to the result.

        Args:
            error_type: Type of the error
            message: Error message
            context: Optional context data
            severity: Optional severity level
        """
        ...

    def add_warning(
        self,
        error_type: str,
        message: str,
        context: dict[str, ContextValue] | None = None,
    ) -> None:
        """
        Add a warning to the result.

        Args:
            error_type: Type of the warning
            message: Warning message
            context: Optional context data
        """
        ...

    async def get_summary(self) -> str:
        """
        Get a summary of the validation result.

        Returns:
            Summary string
        """
        ...


# =============================================================================
# Validator Protocol
# =============================================================================


@runtime_checkable
class ProtocolValidator(Protocol):
    """
    Protocol for protocol validation functionality.

    Validates that implementations conform to their protocol interfaces.
    """

    strict_mode: bool

    async def validate_implementation(
        self, implementation: T, protocol: type[P]
    ) -> ProtocolValidationResult:
        """
        Validate that an implementation conforms to a protocol.

        Args:
            implementation: The implementation to validate
            protocol: The protocol type to validate against

        Returns:
            Validation result
        """
        ...


# =============================================================================
# Validation Decorator Protocol
# =============================================================================


@runtime_checkable
class ProtocolValidationDecorator(Protocol):
    """
    Protocol for validation decorator functionality.

    Provides decorator-based validation for protocol implementations.
    """

    async def validate_protocol_implementation(
        self, implementation: T, protocol: type[P], strict: bool | None = None
    ) -> ProtocolValidationResult:
        """
        Validate a protocol implementation.

        Args:
            implementation: The implementation to validate
            protocol: The protocol type
            strict: Optional strict mode override

        Returns:
            Validation result
        """
        ...

    def validation_decorator(self, protocol: type[P]) -> object:
        """
        Create a validation decorator for a protocol.

        Args:
            protocol: The protocol type

        Returns:
            Decorator function
        """
        ...


# =============================================================================
# Compliance Rule Protocol
# =============================================================================


@runtime_checkable
class ProtocolComplianceRule(Protocol):
    """
    Protocol for ONEX compliance rule definition and checking.

    Defines a single compliance rule with validation logic, severity
    classification, and automated fix suggestions.
    """

    rule_id: str
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


# =============================================================================
# Compliance Violation Protocol
# =============================================================================


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


# =============================================================================
# ONEX Standards Protocol
# =============================================================================


@runtime_checkable
class ProtocolONEXStandards(Protocol):
    """
    Protocol for ONEX ecosystem architectural standards and conventions.

    Defines and validates ONEX naming conventions, directory structure
    requirements, and forbidden patterns.
    """

    enum_naming_pattern: str
    model_naming_pattern: str
    protocol_naming_pattern: str
    node_naming_pattern: str
    required_directories: list[str]
    forbidden_patterns: list[str]

    async def validate_enum_naming(self, name: str) -> bool:
        """Validate enum naming convention."""
        ...

    async def validate_model_naming(self, name: str) -> bool:
        """Validate model naming convention."""
        ...

    async def validate_protocol_naming(self, name: str) -> bool:
        """Validate protocol naming convention."""
        ...

    async def validate_node_naming(self, name: str) -> bool:
        """Validate node naming convention."""
        ...


# =============================================================================
# Architecture Compliance Protocol
# =============================================================================


@runtime_checkable
class ProtocolArchitectureCompliance(Protocol):
    """
    Protocol for architectural compliance checking.

    Validates dependency compliance and layer separation.
    """

    allowed_dependencies: list[str]
    forbidden_dependencies: list[str]
    required_patterns: list[str]
    layer_violations: list[str]

    async def check_dependency_compliance(self, imports: list[str]) -> list[str]:
        """
        Check if imports comply with dependency rules.

        Args:
            imports: List of import statements

        Returns:
            List of violations
        """
        ...

    async def validate_layer_separation(
        self, file_path: str, imports: list[str]
    ) -> list[str]:
        """
        Validate layer separation for a file.

        Args:
            file_path: Path to the file
            imports: List of imports in the file

        Returns:
            List of layer violations
        """
        ...


# =============================================================================
# Compliance Report Protocol
# =============================================================================


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


# =============================================================================
# Compliance Validator Protocol
# =============================================================================


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


# =============================================================================
# Quality Validator Protocol (simplified - based on SPI)
# =============================================================================


@runtime_checkable
class ProtocolQualityValidator(Protocol):
    """
    Protocol for quality validation operations.

    Validates code quality including metrics, issues, and standards.
    """

    async def validate_quality(
        self, file_path: str, content: str | None = None
    ) -> ProtocolValidationResult:
        """
        Validate quality for a file.

        Args:
            file_path: Path to the file
            content: Optional content override

        Returns:
            Validation result
        """
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core Validation
    "ProtocolValidationError",
    "ProtocolValidationResult",
    "ProtocolValidator",
    "ProtocolValidationDecorator",
    # Compliance
    "ProtocolComplianceRule",
    "ProtocolComplianceViolation",
    "ProtocolONEXStandards",
    "ProtocolArchitectureCompliance",
    "ProtocolComplianceReport",
    "ProtocolComplianceValidator",
    # Quality
    "ProtocolQualityValidator",
]
