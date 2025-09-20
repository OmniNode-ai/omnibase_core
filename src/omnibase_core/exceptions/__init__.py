"""ONEX Exception Classes."""

from .base_onex_error import OnexError
from .model_onex_error import ModelOnexError

# CLIAdapter should be imported directly from core.errors.core_errors
# Removed import to fix circular dependency


# Import error code functions
try:
    from omnibase_core.core.errors.core_errors import (
        OnexErrorCode,
        get_error_codes_for_component,
        list_registered_components,
        register_error_codes,
    )
except ImportError:

    def get_error_codes_for_component(component: str) -> type["OnexErrorCode"]:
        """Fallback implementation."""
        # Raise an error to match the actual implementation behavior
        msg = f"No error codes registered for component: {component}"
        raise RuntimeError(msg)

    def list_registered_components() -> list[str]:
        """Fallback implementation."""
        return []

    def register_error_codes(component: str, error_code_enum: type["OnexErrorCode"]) -> None:
        """Fallback implementation."""
        pass


__all__ = [
    "ModelOnexError",
    "OnexError",
    "get_error_codes_for_component",
    "list_registered_components",
    "register_error_codes",
]
