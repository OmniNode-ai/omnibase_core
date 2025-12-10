from typing import TYPE_CHECKING, Any

# TYPE_CHECKING imports for IDE support and type hints.
# These symbols are re-exported via __all__ and resolved at runtime
# through __getattr__ to avoid circular import dependencies.
if TYPE_CHECKING:
    from omnibase_core.errors.declarative_errors import (
        AdapterBindingError,
        NodeExecutionError,
        PurityViolationError,
        UnsupportedCapabilityError,
    )
    from omnibase_core.errors.exception_compute_pipeline_error import (
        ComputePipelineError,
    )
    from omnibase_core.errors.runtime_errors import (
        ContractValidationError,
        EventBusError,
        HandlerExecutionError,
        InvalidOperationError,
        RuntimeHostError,
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

# ModelOnexError is imported via lazy import to avoid circular dependency
# It's available as: from omnibase_core.models.errors.model_onex_error import ModelOnexError


# ModelOnexWarning, ModelRegistryError, and ModelCLIAdapter are imported via lazy import
# to avoid circular dependencies

__all__ = [
    "AdapterBindingError",
    "ComputePipelineError",
    "ContractValidationError",
    "EnumCLIExitCode",
    "EnumCoreErrorCode",
    "EnumRegistryErrorCode",
    "EventBusError",
    "HandlerExecutionError",
    "InvalidOperationError",
    "ModelCLIAdapter",
    "ModelOnexError",
    "ModelOnexWarning",
    "ModelRegistryError",
    "NodeExecutionError",
    "OnexError",
    "PurityViolationError",
    "RuntimeHostError",
    "UnsupportedCapabilityError",
    "get_core_error_description",
    "get_error_codes_for_component",
    "get_exit_code_for_core_error",
    "get_exit_code_for_status",
    "list_registered_components",
    "register_error_codes",
]


# Lazy import to avoid circular dependencies
def __getattr__(name: str) -> Any:
    """Lazy import mechanism to avoid circular dependencies."""
    if name == "ModelOnexError" or name == "OnexError":
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        return ModelOnexError
    if name == "ModelOnexWarning":
        from omnibase_core.models.common.model_onex_warning import ModelOnexWarning

        return ModelOnexWarning
    if name == "ModelRegistryError":
        from omnibase_core.models.common.model_registry_error import ModelRegistryError

        return ModelRegistryError
    if name == "ModelCLIAdapter":
        from omnibase_core.models.core.model_cli_adapter import ModelCLIAdapter

        return ModelCLIAdapter
    # Runtime host errors ()
    if name == "RuntimeHostError":
        from omnibase_core.errors.runtime_errors import RuntimeHostError

        return RuntimeHostError
    if name == "HandlerExecutionError":
        from omnibase_core.errors.runtime_errors import HandlerExecutionError

        return HandlerExecutionError
    if name == "EventBusError":
        from omnibase_core.errors.runtime_errors import EventBusError

        return EventBusError
    if name == "InvalidOperationError":
        from omnibase_core.errors.runtime_errors import InvalidOperationError

        return InvalidOperationError
    if name == "ContractValidationError":
        from omnibase_core.errors.runtime_errors import ContractValidationError

        return ContractValidationError
    # Compute pipeline errors ()
    if name == "ComputePipelineError":
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        return ComputePipelineError
    # -------------------------------------------------------------------------
    # Declarative node errors (OMN-177)
    # Canonical error classes for declarative node validation:
    # - AdapterBindingError: Adapter binding failures
    # - PurityViolationError: Pure function constraint violations
    # - NodeExecutionError: Node execution failures
    # - UnsupportedCapabilityError: Unsupported capability requests
    # -------------------------------------------------------------------------
    if name == "AdapterBindingError":
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        return AdapterBindingError
    if name == "PurityViolationError":
        from omnibase_core.errors.declarative_errors import PurityViolationError

        return PurityViolationError
    if name == "NodeExecutionError":
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        return NodeExecutionError
    if name == "UnsupportedCapabilityError":
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        return UnsupportedCapabilityError
    # Raise standard AttributeError for unknown attributes
    # Cannot use ModelOnexError here as it would cause circular import
    raise AttributeError(  # error-ok: avoid circular import in lazy loader
        f"module '{__name__}' has no attribute '{name}'"
    )
