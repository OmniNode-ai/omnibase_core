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
from omnibase_core.errors.exceptions import (
    ExceptionConfigurationError,
    ExceptionInputValidationError,
    ExceptionValidationFrameworkError,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.validation.model_ambiguous_transition import (
    ModelAmbiguousTransition,
)

# Import model from models/validation/
from omnibase_core.models.validation.model_contract_validation_result import (
    ModelContractValidationResult,
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
from .circular_import_validator import CircularImportValidator

# Import CLI for module execution (OMN-1071)
# ServiceValidationSuite is the canonical class (lives in services/)
# ModelValidationSuite is available via __getattr__ (emits deprecation warning)
from .cli import ServiceValidationSuite

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


def __getattr__(name: str) -> type:
    """
    Lazy import for service classes to avoid circular imports.

    This function is called when an attribute is not found in the module's
    namespace. We use it to defer imports of service classes that would
    otherwise cause circular import errors.

    Why not direct imports?
    -----------------------
    The service classes (ServiceProtocolAuditor, ServiceContractValidator,
    ServiceProtocolMigrator) live in omnibase_core.services.* and have
    transitive imports that eventually import from this validation module.
    Importing them eagerly at module load time would create:

        validation/__init__.py
            -> services/service_protocol_auditor.py
                -> validation/some_validator.py
                    -> validation/__init__.py  (CIRCULAR!)

    By using __getattr__, we defer the import until the class is actually
    accessed, breaking the cycle.

    Deprecated Aliases (OMN-1071):
    ------------------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ModelProtocolAuditor -> ServiceProtocolAuditor
    - ProtocolContractValidator -> ServiceContractValidator
    - ProtocolMigrator -> ServiceProtocolMigrator
    - ModelValidationSuite -> ServiceValidationSuite
    """
    import warnings

    # -------------------------------------------------------------------------
    # Consolidated imports: Map deprecated aliases to canonical service classes
    # Each entry: deprecated_alias -> (module_path, canonical_name)
    # -------------------------------------------------------------------------
    _deprecated_aliases: dict[str, tuple[str, str]] = {
        "ModelProtocolAuditor": (
            "omnibase_core.services.service_protocol_auditor",
            "ServiceProtocolAuditor",
        ),
        "ProtocolContractValidator": (
            "omnibase_core.services.service_contract_validator",
            "ServiceContractValidator",
        ),
        "ProtocolMigrator": (
            "omnibase_core.services.service_protocol_migrator",
            "ServiceProtocolMigrator",
        ),
        "ModelValidationSuite": (
            "omnibase_core.services.service_validation_suite",
            "ServiceValidationSuite",
        ),
    }

    # Emit deprecation warning for deprecated aliases
    if name in _deprecated_aliases:
        module_path, new_name = _deprecated_aliases[name]
        warnings.warn(
            f"'{name}' is deprecated, use '{new_name}' from '{module_path}' instead",
            DeprecationWarning,
            stacklevel=2,
        )

    # -------------------------------------------------------------------------
    # Consolidated lazy imports: Canonical names and deprecated aliases
    # grouped by source module to avoid duplicate import statements
    # -------------------------------------------------------------------------

    # ServiceProtocolAuditor and its alias ModelProtocolAuditor
    if name in {"ServiceProtocolAuditor", "ModelProtocolAuditor"}:
        from omnibase_core.services.service_protocol_auditor import (
            ServiceProtocolAuditor,
        )

        return ServiceProtocolAuditor

    # ServiceContractValidator and its alias ProtocolContractValidator
    if name in {"ServiceContractValidator", "ProtocolContractValidator"}:
        from omnibase_core.services.service_contract_validator import (
            ServiceContractValidator,
        )

        return ServiceContractValidator

    # ServiceProtocolMigrator and its alias ProtocolMigrator
    if name in {"ServiceProtocolMigrator", "ProtocolMigrator"}:
        from omnibase_core.services.service_protocol_migrator import (
            ServiceProtocolMigrator,
        )

        return ServiceProtocolMigrator

    # ModelValidationSuite (alias) - ServiceValidationSuite already imported at top
    if name == "ModelValidationSuite":
        return ServiceValidationSuite

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )


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

# Import workflow constants (OMN-PR255)
from .workflow_constants import (
    MAX_TIMEOUT_MS,
    MIN_TIMEOUT_MS,
    RESERVED_STEP_TYPES,
    VALID_STEP_TYPES,
)

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

    suite = ServiceValidationSuite()
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
    # OMN-1071: Canonical service classes (in services/)
    "ServiceContractValidator",
    "ServiceProtocolAuditor",
    "ServiceProtocolMigrator",
    "ServiceValidationSuite",
    # OMN-1071: Deprecated aliases (will be removed in future version)
    "ProtocolContractValidator",  # Alias for ServiceContractValidator
    "ModelProtocolAuditor",  # Alias for ServiceProtocolAuditor
    "ProtocolMigrator",  # Alias for ServiceProtocolMigrator
    "ModelValidationSuite",  # Alias for ServiceValidationSuite
    # Other exports
    "ExceptionInputValidationError",
    "ModelProtocolInfo",
    "ExceptionValidationFrameworkError",
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
