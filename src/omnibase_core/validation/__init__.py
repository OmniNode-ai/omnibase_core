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

# Import models and enums
from omnibase_core.enums.enum_import_status import EnumImportStatus
from omnibase_core.errors.exception_base import (
    ExceptionConfigurationError,
    ExceptionInputValidationError,
    ExceptionValidationFrameworkError,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.validation.model_ambiguous_transition import (
    ModelAmbiguousTransition,
)

# Contract validation invariant checker (OMN-1146)
# Re-exports from canonical locations
from omnibase_core.models.validation.model_contract_validation_event import (
    ContractValidationEventType,
    ModelContractValidationEvent,
)

# Import model from models/validation/
from omnibase_core.models.validation.model_contract_validation_result import (
    ModelContractValidationResult,
)
from omnibase_core.models.validation.model_fsm_analysis_result import (
    ModelFSMAnalysisResult,
)

# Import the import-specific validation result class (renamed for clarity)
# - ModelImportValidationResult is for circular import validation
# - ModelValidationResult[T] (from models/common/) is for general validation
from omnibase_core.models.validation.model_import_validation_result import (
    ModelImportValidationResult,
)
from omnibase_core.models.validation.model_lint_statistics import ModelLintStatistics
from omnibase_core.models.validation.model_lint_warning import ModelLintWarning
from omnibase_core.models.validation.model_module_import_result import (
    ModelModuleImportResult,
)
from omnibase_core.services.service_contract_validation_invariant_checker import (
    ServiceContractValidationInvariantChecker,
)

# Import CLI for module execution (OMN-1071)
# ServiceValidationSuite is the canonical class (lives in services/)
# ModelValidationSuite is available via __getattr__ (emits deprecation warning)
# Import directly from source module to satisfy mypy explicit-export requirement
from omnibase_core.services.service_validation_suite import ServiceValidationSuite

# Import validation functions for easy access
# Import Architecture validator (OMN-1291)
from .validator_architecture import (
    RULE_NO_MIXED_TYPES,
    RULE_SINGLE_ENUM,
    RULE_SINGLE_MODEL,
    RULE_SINGLE_PROTOCOL,
    ModelCounter,
    ValidatorArchitecture,
    validate_architecture_directory,
    validate_one_model_per_file,
)
from .validator_circular_import import CircularImportValidator

# Import contract patch validator (OMN-1126)
from .validator_contract_patch import ContractPatchValidator

# Re-export from services (OMN-1146)
ContractValidationInvariantChecker = ServiceContractValidationInvariantChecker

# Import contract validation pipeline (OMN-1128)
from .contract_validation_pipeline import (
    ContractValidationPipeline,
    ModelExpandedContractResult,
)

# Import Any type validator (OMN-1291)
from .validator_any_type import ValidatorAnyType

# Import validator base class (OMN-1291)
from .validator_base import (
    EXIT_ERRORS,
    EXIT_SUCCESS,
    EXIT_WARNINGS,
    SEVERITY_PRIORITY,
    ValidatorBase,
)

# Import Contract Linter validator (OMN-1291)
from .validator_contract_linter import (
    CONTRACT_MODELS,
    NODE_TYPE_MAPPING,
    RULE_FINGERPRINT_FORMAT,
    RULE_FINGERPRINT_MATCH,
    RULE_MODEL_PREFIX,
    RULE_NAMING_CONVENTION,
    RULE_RECOMMENDED_FIELDS,
    RULE_REQUIRED_FIELDS,
    RULE_SCHEMA_VALIDATION,
    RULE_YAML_SYNTAX,
    ValidatorContractLinter,
)

# Import Naming Convention validator (OMN-1291)
from .validator_naming_convention import (
    RULE_CLASS_NAMING,
    RULE_FILE_NAMING,
    RULE_FUNCTION_NAMING,
    RULE_UNKNOWN_NAMING,
    ValidatorNamingConvention,
)
from .visitor_any_type import (
    EXEMPT_DECORATORS,
    RULE_ANY_ANNOTATION,
    RULE_ANY_IMPORT,
    RULE_DICT_STR_ANY,
    RULE_LIST_ANY,
    RULE_UNION_WITH_ANY,
    AnyTypeVisitor,
)

# =============================================================================
# ALIAS LOADING STRATEGY: __getattr__ vs Direct Alias
# =============================================================================
#
# This module uses TWO different strategies for deprecated aliases:
#
# 1. DIRECT ALIAS (used above for ModelValidationSuite):
#    ```python
#    from .cli import ModelValidationSuite, ServiceValidationSuite
#    ```
#    Use this when: The canonical class can be imported at module load time
#    without causing circular imports. This is simpler and provides better
#    IDE support (autocomplete, go-to-definition).
#
# 2. LAZY __getattr__ (used below for ServiceProtocolAuditor, etc.):
#    ```python
#    def __getattr__(name: str) -> type:
#        if name == "ServiceProtocolAuditor":
#            from omnibase_core.services.service_protocol_auditor import ...
#    ```
#    Use this when: Importing the canonical class at module load time would
#    cause circular imports. The service classes below live in
#    omnibase_core.services.* which may import from omnibase_core.validation,
#    creating an import cycle if we imported them eagerly here.
#
# DECISION GUIDE:
# - If adding a new backwards compat alias, first try direct import
# - If you get ImportError or circular import errors, use __getattr__
# - Document WHY __getattr__ is needed (which module causes the cycle)
#
# OMN-1071: These service classes require lazy loading because:
# - ServiceProtocolAuditor imports validation utilities that import from here
# - ServiceContractValidator has similar circular dependency chains
# - ServiceProtocolMigrator has similar circular dependency chains
# =============================================================================


# Lazy loading for service classes to avoid circular imports.
# These service classes live in omnibase_core.services.* and have transitive
# imports that eventually import from this validation module.
def __getattr__(name: str) -> type:
    """Lazy import for service classes to avoid circular imports."""
    if name == "ServiceProtocolAuditor":
        from omnibase_core.services.service_protocol_auditor import (
            ServiceProtocolAuditor,
        )

        return ServiceProtocolAuditor

    if name == "ServiceContractValidator":
        from omnibase_core.services.service_contract_validator import (
            ServiceContractValidator,
        )

        return ServiceContractValidator

    if name == "ServiceProtocolMigrator":
        from omnibase_core.services.service_protocol_migrator import (
            ServiceProtocolMigrator,
        )

        return ServiceProtocolMigrator

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )


# Import FSM analysis
# Import workflow linter
from .checker_workflow_linter import WorkflowLinter
from .validator_contracts import (
    validate_contracts_directory,
    validate_no_manual_yaml,
    validate_yaml_file,
)
from .validator_fsm_analysis import analyze_fsm
from .validator_patterns import (
    RULE_UNKNOWN,
    ValidatorPatterns,
    validate_patterns_directory,
    validate_patterns_file,
)

# Import reserved enum validator (OMN-669, OMN-675)
# - validate_execution_mode takes EnumExecutionMode (type-safe, for validated enum values)
# - Rejects CONDITIONAL/STREAMING modes reserved for future versions
# - For string input (e.g., YAML config), use validate_execution_mode_string instead
from .validator_reserved_enum import RESERVED_EXECUTION_MODES, validate_execution_mode

# Import Union Usage validator (OMN-1291)
from .validator_types import (
    ValidatorUnionUsage,
    validate_union_usage_cli,
    validate_union_usage_directory,
    validate_union_usage_file,
)
from .validator_utils import ModelProtocolInfo, validate_protocol_compliance
from .validator_workflow import (
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

# Import workflow constants (OMN-PR255)
from .validator_workflow_constants import (
    MAX_TIMEOUT_MS,
    MIN_TIMEOUT_MS,
    RESERVED_STEP_TYPES,
    VALID_STEP_TYPES,
)

# Import common validators (OMN-1054)
from .validators import (
    BCP47Locale,
    Duration,
    ErrorCode,
    SemanticVersion,
    UUIDString,
    create_enum_normalizer,
    validate_bcp47_locale,
    validate_duration,
    validate_error_code,
    validate_semantic_version,
    validate_uuid,
)


# Main validation functions (recommended interface)
def validate_architecture(
    directory_path: str = "src/",
    max_violations: int = 0,
) -> ModelValidationResult[None]:
    """Validate ONEX one-model-per-file architecture."""
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

    suite = ServiceValidationSuite()
    return suite.run_all_validations(Path(directory_path), **kwargs)


__all__ = [
    # Core classes and types
    "CircularImportValidator",
    "ModelImportValidationResult",
    "ExceptionConfigurationError",
    "EnumImportStatus",
    "ModelContractValidationResult",
    "ModelModuleImportResult",
    "ModelValidationResult",
    # Service classes (lazy-loaded to avoid circular imports)
    "ServiceContractValidator",
    "ServiceProtocolAuditor",
    "ServiceProtocolMigrator",
    "ServiceValidationSuite",
    # Other exports
    "ExceptionInputValidationError",
    "ModelProtocolInfo",
    "ExceptionValidationFrameworkError",
    "validate_all",
    # Protocol compliance validation
    "validate_protocol_compliance",
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
    # Contract patch validator (OMN-1126)
    "ContractPatchValidator",
    # Contract validation invariant checker (OMN-1146)
    "ServiceContractValidationInvariantChecker",
    "ModelContractValidationEvent",
    "ContractValidationEventType",
    "ContractValidationInvariantChecker",
    # Contract validation pipeline (OMN-1128)
    "ContractValidationPipeline",
    "ModelExpandedContractResult",
    # Validator base class (OMN-1291)
    "ValidatorBase",
    "EXIT_SUCCESS",
    "EXIT_ERRORS",
    "EXIT_WARNINGS",
    "SEVERITY_PRIORITY",
    # Any type validator (OMN-1291)
    "ValidatorAnyType",
    "AnyTypeVisitor",
    "RULE_ANY_IMPORT",
    "RULE_ANY_ANNOTATION",
    "RULE_DICT_STR_ANY",
    "RULE_LIST_ANY",
    "RULE_UNION_WITH_ANY",
    "EXEMPT_DECORATORS",
    # Contract Linter validator (OMN-1291)
    "ValidatorContractLinter",
    "CONTRACT_MODELS",
    "NODE_TYPE_MAPPING",
    "RULE_YAML_SYNTAX",
    "RULE_REQUIRED_FIELDS",
    "RULE_RECOMMENDED_FIELDS",
    "RULE_NAMING_CONVENTION",
    "RULE_MODEL_PREFIX",
    "RULE_FINGERPRINT_FORMAT",
    "RULE_FINGERPRINT_MATCH",
    "RULE_SCHEMA_VALIDATION",
    # Naming Convention validator (OMN-1291)
    "ValidatorNamingConvention",
    "RULE_FILE_NAMING",
    "RULE_CLASS_NAMING",
    "RULE_FUNCTION_NAMING",
    "RULE_UNKNOWN_NAMING",
    # Architecture validator (OMN-1291)
    "ValidatorArchitecture",
    "ModelCounter",
    "RULE_SINGLE_MODEL",
    "RULE_SINGLE_ENUM",
    "RULE_SINGLE_PROTOCOL",
    "RULE_NO_MIXED_TYPES",
    # Union Usage validator (OMN-1291)
    "ValidatorUnionUsage",
    "validate_union_usage_cli",
    # Patterns validator (OMN-1291)
    "ValidatorPatterns",
    "RULE_UNKNOWN",
    # Reserved enum validation (OMN-669, OMN-675)
    # NOTE: validate_execution_mode takes EnumExecutionMode (type-safe)
    # while validate_execution_mode_string takes str (for YAML/config parsing)
    "RESERVED_EXECUTION_MODES",
    "validate_execution_mode",
    # Workflow constants (OMN-PR255)
    "MAX_TIMEOUT_MS",
    "MIN_TIMEOUT_MS",
    "RESERVED_STEP_TYPES",
    "VALID_STEP_TYPES",
    # Common validators (OMN-1054)
    # Validator functions
    "validate_duration",
    "validate_bcp47_locale",
    "validate_uuid",
    "validate_semantic_version",
    "validate_error_code",
    # Enum normalizer factory
    "create_enum_normalizer",
    # Pydantic Annotated types
    "Duration",
    "BCP47Locale",
    "UUIDString",
    "SemanticVersion",
    "ErrorCode",
]
