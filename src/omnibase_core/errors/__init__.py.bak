from typing import Any

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
    # Base error classes
    "ModelOnexError",
    "OnexError",  # Alias for ModelOnexError
    "ModelOnexWarning",
    # Error codes and enums
    "EnumCoreErrorCode",
    "EnumCLIExitCode",
    "EnumRegistryErrorCode",
    # CLI adapter and utilities
    "ModelCLIAdapter",
    "get_exit_code_for_status",
    "get_exit_code_for_core_error",
    "get_core_error_description",
    # Error code registration
    "register_error_codes",
    "get_error_codes_for_component",
    "list_registered_components",
    # Registry errors
    "ModelRegistryError",
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
    # Raise standard AttributeError for unknown attributes
    # Cannot use ModelOnexError here as it would cause circular import
    raise AttributeError(  # error-ok: avoid circular import in lazy loader
        f"module '{__name__}' has no attribute '{name}'"
    )
