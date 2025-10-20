from pathlib import Path
from typing import Any, Union

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
        print("ModelArchitecture violations found!")

    # CLI usage
    python -m omnibase_core.validation architecture src/
    python -m omnibase_core.validation union-usage --strict
    python -m omnibase_core.validation all
"""

# Import validation functions for easy access
from .architecture import validate_architecture_directory, validate_one_model_per_file
from .auditor_protocol import ModelProtocolAuditor

# Import CLI for module execution
from .cli import ModelValidationSuite
from .contract_validator import ModelContractValidationResult, ProtocolContractValidator
from .contracts import (
    validate_contracts_directory,
    validate_no_manual_yaml,
    validate_yaml_file,
)
from .exceptions import (
    ConfigurationError,
    InputValidationError,
    ValidationFrameworkError,
)
from .model_audit_result import ModelAuditResult
from .model_duplication_report import ModelDuplicationReport
from .patterns import validate_patterns_directory, validate_patterns_file
from .types import validate_union_usage_directory, validate_union_usage_file
from .validation_utils import ModelProtocolInfo, ValidationResult


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

    return validate_union_usage_directory(Path(directory_path), max_unions, strict)


def validate_contracts(directory_path: str = ".") -> ValidationResult:
    """Validate YAML contract files."""

    return validate_contracts_directory(Path(directory_path))


def validate_patterns(
    directory_path: str = "src/",
    strict: bool = False,
) -> ValidationResult:
    """Validate code patterns and conventions."""

    return validate_patterns_directory(Path(directory_path), strict)


def validate_all(
    directory_path: str = "src/",
    **kwargs: object,
) -> dict[str, ValidationResult]:
    """Run all validations and return results."""

    suite = ModelValidationSuite()
    return suite.run_all_validations(Path(directory_path), **kwargs)


__all__ = [
    # Core classes and types
    "ConfigurationError",
    "ModelContractValidationResult",
    "ProtocolContractValidator",
    "InputValidationError",
    "ModelProtocolAuditor",
    "ModelProtocolInfo",
    "ValidationFrameworkError",
    "ValidationResult",
    "ModelValidationSuite",
    "ModelAuditResult",
    "ModelDuplicationReport",
    "validate_all",
    # Main validation functions (recommended)
    "validate_architecture",
    # Individual module functions
    "validate_architecture_directory",
    "validate_contracts",
    "validate_contracts_directory",
    "validate_no_manual_yaml",
    "validate_one_model_per_file",
    "validate_patterns",
    "validate_patterns_directory",
    "validate_patterns_file",
    "validate_union_usage",
    "validate_union_usage_directory",
    "validate_union_usage_file",
    "validate_yaml_file",
]
