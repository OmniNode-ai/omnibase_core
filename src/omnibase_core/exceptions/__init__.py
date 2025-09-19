"""ONEX Exception Classes."""

from .base_onex_error import OnexError
from .model_onex_error import ModelOnexError

# CLIAdapter should be imported directly from core.errors.core_errors
# Removed import to fix circular dependency


# Import error code functions
try:
    from omnibase_core.core.errors.core_errors import (
        get_error_codes_for_component,
        list_registered_components,
        register_error_codes,
    )
except ImportError:

    def get_error_codes_for_component(component: str):
        """Fallback implementation."""
        return

    def list_registered_components():
        """Fallback implementation."""
        return []

    def register_error_codes(component: str, error_code_enum):
        """Fallback implementation."""


__all__ = [
    "ModelOnexError",
    "OnexError",
    "get_error_codes_for_component",
    "list_registered_components",
    "register_error_codes",
]
