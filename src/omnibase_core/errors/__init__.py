from typing import TYPE_CHECKING, Any

# TYPE_CHECKING imports for IDE support and type hints.
# These symbols are re-exported via __all__ and resolved at runtime
# through __getattr__ to avoid circular import dependencies.
if TYPE_CHECKING:
    from omnibase_core.errors.error_callable_not_found import CallableNotFoundError
    from omnibase_core.errors.error_declarative import (
        AdapterBindingError,
        NodeExecutionError,
        PurityViolationError,
        UnsupportedCapabilityError,
    )
    from omnibase_core.errors.error_dependency_cycle import DependencyCycleError
    from omnibase_core.errors.error_duplicate_hook import DuplicateHookError
    from omnibase_core.errors.error_hook_registry_frozen import HookRegistryFrozenError
    from omnibase_core.errors.error_hook_timeout import HookTimeoutError
    from omnibase_core.errors.error_hook_type_mismatch import HookTypeMismatchError
    from omnibase_core.errors.error_pipeline import PipelineError
    from omnibase_core.errors.error_runtime import (
        ContractValidationError,
        EventBusError,
        HandlerExecutionError,
        InvalidOperationError,
        RuntimeHostError,
    )
    from omnibase_core.errors.error_unknown_dependency import UnknownDependencyError
    from omnibase_core.errors.exception_compute_pipeline_error import (
        ComputePipelineError,
    )
    from omnibase_core.models.common.model_onex_warning import ModelOnexWarning
    from omnibase_core.models.common.model_registry_error import ModelRegistryError
    from omnibase_core.models.core.model_cli_adapter import ModelCLIAdapter
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""Core error handling for ONEX framework."""

# Core error system - comprehensive implementation
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_core_error_code import (
    EnumCoreErrorCode,
    get_core_error_description,
    get_exit_code_for_core_error,
)
from omnibase_core.enums.enum_registry_error_code import EnumRegistryErrorCode
from omnibase_core.errors.error_codes import (
    get_error_codes_for_component,
    get_exit_code_for_status,
    list_registered_components,
    register_error_codes,
)
from omnibase_core.errors.exception_groups import (
    ASYNC_ERRORS,
    ATTRIBUTE_ACCESS_ERRORS,
    FILE_IO_ERRORS,
    JSON_PARSING_ERRORS,
    NETWORK_ERRORS,
    PYDANTIC_MODEL_ERRORS,
    VALIDATION_ERRORS,
    YAML_PARSING_ERRORS,
)

# ModelOnexError is imported via lazy import to avoid circular dependency
# It's available as: from omnibase_core.models.errors.model_onex_error import ModelOnexError


# ModelOnexWarning, ModelRegistryError, and ModelCLIAdapter are imported via lazy import
# to avoid circular dependencies

__all__ = [
    # Exception Groups (centralized exception type tuples)
    "ASYNC_ERRORS",
    "ATTRIBUTE_ACCESS_ERRORS",
    "FILE_IO_ERRORS",
    "JSON_PARSING_ERRORS",
    "NETWORK_ERRORS",
    "PYDANTIC_MODEL_ERRORS",
    "VALIDATION_ERRORS",
    "YAML_PARSING_ERRORS",
    # Error Classes
    "AdapterBindingError",
    "CallableNotFoundError",
    "ComputePipelineError",
    "ContractValidationError",
    "DependencyCycleError",
    "DuplicateHookError",
    "EnumCLIExitCode",
    "EnumCoreErrorCode",
    "EnumRegistryErrorCode",
    "EventBusError",
    "HandlerExecutionError",
    "HookRegistryFrozenError",
    "HookTimeoutError",
    "HookTypeMismatchError",
    "InvalidOperationError",
    "ModelCLIAdapter",
    "ModelOnexError",
    "ModelOnexWarning",
    "ModelRegistryError",
    "NodeExecutionError",
    "OnexError",
    "PipelineError",
    "PurityViolationError",
    "RuntimeHostError",
    "UnknownDependencyError",
    "UnsupportedCapabilityError",
    # Functions
    "get_core_error_description",
    "get_error_codes_for_component",
    "get_exit_code_for_core_error",
    "get_exit_code_for_status",
    "list_registered_components",
    "register_error_codes",
]


# =============================================================================
# Lazy loading: Avoid circular imports during module initialization.
# This defers imports of error classes and model classes that would cause
# circular dependency chains if imported at module load time.
#
# Classes loaded lazily:
# - ModelOnexError, OnexError (alias) - from models.errors
# - ModelOnexWarning, ModelRegistryError - from models.common
# - ModelCLIAdapter - from models.core
# - RuntimeHostError, HandlerExecutionError, etc. - from errors.error_runtime
# - AdapterBindingError, PurityViolationError, etc. - from errors.error_declarative
# - PipelineError, CallableNotFoundError, etc. - from errors.error_* modules
# =============================================================================
def __getattr__(name: str) -> Any:
    """
    Lazy import mechanism to avoid circular dependencies.

    This function defers the import of error and model classes until they are
    actually accessed, preventing circular import chains that would otherwise
    occur at module load time.

    Note: The OnexError alias to ModelOnexError is for convenience, not
    deprecation - both names are valid.
    """
    # -------------------------------------------------------------------------
    # Consolidated imports: Group related classes by source module to avoid
    # duplicate import statements. Each group imports from one module.
    # -------------------------------------------------------------------------

    # Model error classes from models.errors
    if name in {"ModelOnexError", "OnexError"}:
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        return ModelOnexError

    # Model classes from models.common
    _common_model_classes = {"ModelOnexWarning", "ModelRegistryError"}
    if name in _common_model_classes:
        from omnibase_core.models.common import model_onex_warning, model_registry_error

        _common_exports = {
            "ModelOnexWarning": model_onex_warning.ModelOnexWarning,
            "ModelRegistryError": model_registry_error.ModelRegistryError,
        }
        return _common_exports[name]

    # CLI adapter from models.core
    if name == "ModelCLIAdapter":
        from omnibase_core.models.core.model_cli_adapter import ModelCLIAdapter

        return ModelCLIAdapter

    # -------------------------------------------------------------------------
    # Runtime host errors - consolidated import from runtime_errors module
    # -------------------------------------------------------------------------
    _runtime_error_classes = {
        "RuntimeHostError",
        "HandlerExecutionError",
        "EventBusError",
        "InvalidOperationError",
        "ContractValidationError",
    }
    if name in _runtime_error_classes:
        from omnibase_core.errors import error_runtime

        return getattr(error_runtime, name)

    # Compute pipeline errors
    if name == "ComputePipelineError":
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        return ComputePipelineError

    # -------------------------------------------------------------------------
    # Declarative node errors (OMN-177) - consolidated import
    # Canonical error classes for declarative node validation:
    # - AdapterBindingError: Adapter binding failures
    # - PurityViolationError: Pure function constraint violations
    # - NodeExecutionError: Node execution failures
    # - UnsupportedCapabilityError: Unsupported capability requests
    # -------------------------------------------------------------------------
    _declarative_error_classes = {
        "AdapterBindingError",
        "PurityViolationError",
        "NodeExecutionError",
        "UnsupportedCapabilityError",
    }
    if name in _declarative_error_classes:
        from omnibase_core.errors import error_declarative

        return getattr(error_declarative, name)

    # -------------------------------------------------------------------------
    # Pipeline errors - consolidated import from individual modules
    # These errors were moved from pipeline/ to errors/ per ONEX file location
    # convention (error_*.py files must be in errors/ directory)
    # -------------------------------------------------------------------------
    _pipeline_error_classes = {
        "PipelineError": "error_pipeline",
        "CallableNotFoundError": "error_callable_not_found",
        "DependencyCycleError": "error_dependency_cycle",
        "DuplicateHookError": "error_duplicate_hook",
        "HookRegistryFrozenError": "error_hook_registry_frozen",
        "HookTimeoutError": "error_hook_timeout",
        "HookTypeMismatchError": "error_hook_type_mismatch",
        "UnknownDependencyError": "error_unknown_dependency",
    }
    if name in _pipeline_error_classes:
        import importlib

        module = importlib.import_module(
            f"omnibase_core.errors.{_pipeline_error_classes[name]}"
        )
        return getattr(module, name)

    # Raise standard AttributeError for unknown attributes
    # Cannot use ModelOnexError here as it would cause circular import
    raise AttributeError(  # error-ok: avoid circular import in lazy loader
        f"module '{__name__}' has no attribute '{name}'"
    )
