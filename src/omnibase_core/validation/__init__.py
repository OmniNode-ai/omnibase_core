"""
Comprehensive validation framework for omni* ecosystem.

This module provides centralized validation tools that can be imported
by all repositories in the omni* ecosystem for ONEX compliance validation.

Key validation modules:
- architecture: ONEX one-model-per-file validation
- types: Union usage and type pattern validation
- contracts: YAML contract validation
- patterns: Code pattern and naming validation
- cli: Unified command-line interface

Usage Examples:
    # Programmatic usage
    from omnibase_core.validation import validate_architecture, validate_union_usage

    result = validate_architecture("src/")
    if not result.success:
        print("Architecture violations found!")

    # CLI usage
    python -m omnibase_core.validation architecture src/
    python -m omnibase_core.validation union-usage --strict
    python -m omnibase_core.validation all
"""

from typing import Any

# Import validation functions for easy access
from .architecture import validate_architecture_directory, validate_one_model_per_file

# Import CLI for module execution
from .cli import ValidationSuite
from .contracts import (
    validate_contracts_directory,
    validate_no_manual_yaml,
    validate_yaml_file,
)
from .patterns import validate_patterns_directory, validate_patterns_file
from .types import validate_union_usage_directory, validate_union_usage_file
from .validation_utils import ProtocolInfo, ValidationResult

# Legacy protocol validation imports for backward compatibility
try:
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
except ImportError:
    # Legacy modules may not exist in all installations
    pass


# Legacy protocol classes (placeholders for compatibility)
class AuditResult:
    def __init__(
        self, success: bool = True, message: str = "", protocols_found: int = 0
    ) -> None:
        self.success = success
        self.message = message
        self.protocols_found = protocols_found


class DuplicationReport:
    def __init__(self, duplicates: list[str] | None = None) -> None:
        self.duplicates = duplicates or []


class ProtocolAuditor:
    def __init__(self, repository_path: str = ".") -> None:
        self.repository_path = repository_path

    def check_current_repository(self) -> AuditResult:
        return AuditResult(success=True, message="Legacy protocol auditing")

    def check_against_spi(self, spi_path: str) -> DuplicationReport:
        return DuplicationReport()


class ModelMigrationPlan:
    def __init__(self) -> None:
        self.migrations: list[str] = []


class ModelMigrationResult:
    def __init__(self, success: bool = True) -> None:
        self.success = success


class ProtocolMigrator:
    def __init__(
        self, source_path: str = ".", spi_path: str = "../omnibase_spi"
    ) -> None:
        self.source_path = source_path
        self.spi_path = spi_path

    def create_migration_plan(self) -> ModelMigrationPlan:
        return ModelMigrationPlan()


# Main validation functions (recommended interface)
def validate_architecture(
    directory_path: str = "src/",
    max_violations: int = 0,
) -> ValidationResult:
    """Validate ONEX one-model-per-file architecture."""
    from pathlib import Path

    return validate_architecture_directory(Path(directory_path), max_violations)


def validate_union_usage(
    directory_path: str = "src/",
    max_unions: int = 100,
    strict: bool = False,
) -> ValidationResult:
    """Validate Union type usage patterns."""
    from pathlib import Path

    return validate_union_usage_directory(Path(directory_path), max_unions, strict)


def validate_contracts(directory_path: str = ".") -> ValidationResult:
    """Validate YAML contract files."""
    from pathlib import Path

    return validate_contracts_directory(Path(directory_path))


def validate_patterns(
    directory_path: str = "src/",
    strict: bool = False,
) -> ValidationResult:
    """Validate code patterns and conventions."""
    from pathlib import Path

    return validate_patterns_directory(Path(directory_path), strict)


def validate_all(
    directory_path: str = "src/", **kwargs: Any
) -> dict[str, ValidationResult]:
    """Run all validations and return results."""
    from pathlib import Path

    suite = ValidationSuite()
    return suite.run_all_validations(Path(directory_path), **kwargs)


# Legacy protocol functions for backward compatibility
def audit_protocols(repository_path: str = ".") -> AuditResult:
    """Quick audit of protocols in repository (legacy)."""
    try:
        auditor = ProtocolAuditor(repository_path)
        return auditor.check_current_repository()
    except (ImportError, NameError):
        raise ImportError("Legacy protocol auditing not available in this installation")


def check_against_spi(
    repository_path: str = ".", spi_path: str = "../omnibase_spi"
) -> DuplicationReport:
    """Check repository protocols against SPI for duplicates (legacy)."""
    try:
        auditor = ProtocolAuditor(repository_path)
        return auditor.check_against_spi(spi_path)
    except (ImportError, NameError):
        raise ImportError("Legacy protocol auditing not available in this installation")


def create_migration_plan(
    source_path: str = ".", spi_path: str = "../omnibase_spi"
) -> ModelMigrationPlan:
    """Create migration plan for moving protocols to SPI (legacy)."""
    try:
        migrator = ProtocolMigrator(source_path, spi_path)
        return migrator.create_migration_plan()
    except (ImportError, NameError):
        raise ImportError(
            "Legacy protocol migration not available in this installation",
        )


__all__ = [
    # Main validation functions (recommended)
    "validate_architecture",
    "validate_union_usage",
    "validate_contracts",
    "validate_patterns",
    "validate_all",
    # Individual module functions
    "validate_architecture_directory",
    "validate_one_model_per_file",
    "validate_contracts_directory",
    "validate_yaml_file",
    "validate_no_manual_yaml",
    "validate_patterns_directory",
    "validate_patterns_file",
    "validate_union_usage_directory",
    "validate_union_usage_file",
    # Core classes and types
    "ValidationResult",
    "ValidationSuite",
    "ProtocolInfo",
    # Legacy functions for backward compatibility
    "audit_protocols",
    "check_against_spi",
    "create_migration_plan",
]
