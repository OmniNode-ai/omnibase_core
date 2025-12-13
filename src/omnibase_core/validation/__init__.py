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

from pathlib import Path
from typing import Any, Union

# Import models and enums
from omnibase_core.enums.enum_import_status import EnumImportStatus
from omnibase_core.errors.exceptions import (
    ExceptionConfigurationError,
    ExceptionInputValidationError,
    ExceptionValidationFrameworkError,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.validation.model_ambiguous_transition import (
    ModelAmbiguousTransition,
)
from omnibase_core.models.validation.model_fsm_analysis_result import (
    ModelFSMAnalysisResult,
)

# Import BOTH validation result classes (different purposes!)
# - ModelValidationResult (from models/) is for circular import validation
# - ModelValidationResult (from models/validation/) is for general validation
from omnibase_core.models.validation.model_import_validation_result import (
    ModelValidationResult as CircularImportValidationResult,
)
from omnibase_core.models.validation.model_lint_statistics import ModelLintStatistics
from omnibase_core.models.validation.model_lint_warning import ModelLintWarning
from omnibase_core.models.validation.model_module_import_result import (
    ModelModuleImportResult,
)

# Import validation functions for easy access
from .architecture import validate_architecture_directory, validate_one_model_per_file
from .auditor_protocol import ModelProtocolAuditor
from .circular_import_validator import CircularImportValidator

# Import CLI for module execution
from .cli import ModelValidationSuite
from .contract_validator import ModelContractValidationResult, ProtocolContractValidator
from .contracts import (
    validate_contracts_directory,
    validate_no_manual_yaml,
    validate_yaml_file,
)

# Import FSM analysis
from .fsm_analysis import analyze_fsm
from .patterns import validate_patterns_directory, validate_patterns_file

# Import reserved enum validator (OMN-669, OMN-675)
# - validate_execution_mode takes EnumExecutionMode (type-safe, for validated enum values)
# - Rejects CONDITIONAL/STREAMING modes reserved for future versions
# - For string input (e.g., YAML config), use validate_execution_mode_string instead
from .reserved_enum_validator import RESERVED_EXECUTION_MODES, validate_execution_mode
from .types import validate_union_usage_directory, validate_union_usage_file
from .validation_utils import ModelProtocolInfo

# Import workflow linter
from .workflow_linter import WorkflowLinter
from .workflow_validator import (
    ModelCycleDetectionResult,
    ModelDependencyValidationResult,
    ModelIsolatedStepResult,
    ModelUniqueNameResult,
    ModelWorkflowValidationResult,
    WorkflowValidator,
    validate_dag_with_disabled_steps,
    validate_execution_mode_string,
    validate_unique_step_ids,
    validate_workflow_definition,
)


# Main validation functions (recommended interface)
def validate_architecture(
    directory_path: str = "src/",
    max_violations: int = 0,
) -> ModelValidationResult[None]:
    """Validate ONEX one-model-per-file architecture."""
    from pathlib import Path

    return validate_architecture_directory(Path(directory_path), max_violations)


def validate_union_usage(
    directory_path: str = "src/",
    max_unions: int = 100,
    strict: bool = False,
) -> ModelValidationResult[None]:
    """Validate Union type usage patterns."""

    return validate_union_usage_directory(Path(directory_path), max_unions, strict)


def validate_contracts(directory_path: str = ".") -> ModelValidationResult[None]:
    """Validate YAML contract files."""

    return validate_contracts_directory(Path(directory_path))


def validate_patterns(
    directory_path: str = "src/",
    strict: bool = False,
) -> ModelValidationResult[None]:
    """Validate code patterns and conventions."""

    return validate_patterns_directory(Path(directory_path), strict)


def validate_all(
    directory_path: str = "src/",
    **kwargs: object,
) -> dict[str, ModelValidationResult[None]]:
    """Run all validations and return results."""

    suite = ModelValidationSuite()
    return suite.run_all_validations(Path(directory_path), **kwargs)


__all__ = [
    # Core classes and types
    "CircularImportValidator",
    "CircularImportValidationResult",
    "ExceptionConfigurationError",
    "EnumImportStatus",
    "ModelContractValidationResult",
    "ModelModuleImportResult",
    "ModelValidationResult",
    "ProtocolContractValidator",
    "ExceptionInputValidationError",
    "ModelProtocolAuditor",
    "ModelProtocolInfo",
    "ExceptionValidationFrameworkError",
    "ModelValidationSuite",
    "validate_all",
    # Workflow linter (OMN-655)
    "ModelLintStatistics",
    "ModelLintWarning",
    "WorkflowLinter",
    # FSM analysis
    "ModelAmbiguousTransition",
    "ModelFSMAnalysisResult",
    "analyze_fsm",
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
    # Workflow validation (OMN-176, OMN-655)
    "ModelCycleDetectionResult",
    "ModelDependencyValidationResult",
    "ModelIsolatedStepResult",
    "ModelUniqueNameResult",
    "ModelWorkflowValidationResult",
    "WorkflowValidator",
    "validate_dag_with_disabled_steps",
    "validate_execution_mode_string",
    "validate_unique_step_ids",
    "validate_workflow_definition",
    # Reserved enum validation (OMN-669, OMN-675)
    # NOTE: validate_execution_mode takes EnumExecutionMode (type-safe)
    # while validate_execution_mode_string takes str (for YAML/config parsing)
    "RESERVED_EXECUTION_MODES",
    "validate_execution_mode",
]
