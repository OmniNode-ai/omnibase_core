"""
Protocol validation framework for omni* ecosystem.

This module provides centralized protocol validation that can be imported
by all repositories in the omni* ecosystem (except omnibase_spi which gets copies).

Key classes:
- ProtocolAuditor: Audit protocols for duplicates and violations
- ProtocolMigrator: Safe migration of protocols to omnibase_spi
- EcosystemValidator: Cross-repository validation

Usage:
    from omnibase_core.validation import ProtocolAuditor

    auditor = ProtocolAuditor()
    result = auditor.check_current_repository()
    if not result.success:
        print("Protocol violations found!")
"""

from .ecosystem_validators import (
    ValidationResponse,
    validate_naming_conventions,
    validate_no_legacy_patterns,
    validate_no_manual_yaml,
    validate_no_string_versions,
    validate_repository_structure,
)
from .exceptions import (
    AuditError,
    ConfigurationError,
    FileProcessingError,
    InputValidationError,
    MigrationError,
    PathTraversalError,
    ProtocolParsingError,
    ValidationFrameworkError,
)
from .protocol_auditor import AuditResult, DuplicationReport, ProtocolAuditor
from .protocol_migrator import MigrationPlan, MigrationResult, ProtocolMigrator
from .validation_utils import ProtocolInfo, ValidationResult


# Convenience functions for simple usage
def audit_protocols(repository_path: str = ".") -> AuditResult:
    """Quick audit of protocols in repository."""
    auditor = ProtocolAuditor(repository_path)
    return auditor.check_current_repository()


def check_against_spi(
    repository_path: str = ".", spi_path: str = "../omnibase_spi"
) -> DuplicationReport:
    """Check repository protocols against SPI for duplicates."""
    auditor = ProtocolAuditor(repository_path)
    return auditor.check_against_spi(spi_path)


def create_migration_plan(
    source_path: str = ".", spi_path: str = "../omnibase_spi"
) -> MigrationPlan:
    """Create migration plan for moving protocols to SPI."""
    migrator = ProtocolMigrator(source_path, spi_path)
    return migrator.create_migration_plan()


__all__ = [
    # Core classes
    "ProtocolAuditor",
    "ProtocolMigrator",
    # Result types
    "AuditResult",
    "DuplicationReport",
    "MigrationPlan",
    "MigrationResult",
    "ProtocolInfo",
    "ValidationResult",
    "ValidationResponse",
    # Exceptions
    "ValidationFrameworkError",
    "ConfigurationError",
    "FileProcessingError",
    "ProtocolParsingError",
    "AuditError",
    "MigrationError",
    "InputValidationError",
    "PathTraversalError",
    # Convenience functions
    "audit_protocols",
    "check_against_spi",
    "create_migration_plan",
    # Ecosystem validation functions
    "validate_repository_structure",
    "validate_naming_conventions",
    "validate_no_string_versions",
    "validate_no_legacy_patterns",
    "validate_no_manual_yaml",
]
