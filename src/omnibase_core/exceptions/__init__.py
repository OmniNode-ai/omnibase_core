"""ONEX Exception Classes."""

from .base_onex_error import OnexError
from .model_onex_error import ModelOnexError

# Import CLIAdapter from model_core_errors
try:
    from omnibase_core.model.core.model_core_errors import CLIAdapter
except ImportError:
    # Fallback minimal CLIAdapter if import fails
    class CLIAdapter:
        """Minimal CLI adapter for exit code handling."""


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
        return None

    def list_registered_components():
        """Fallback implementation."""
        return []

    def register_error_codes(component: str, error_code_enum):
        """Fallback implementation."""
        pass


__all__ = [
    "CLIAdapter",
    "ModelOnexError",
    "OnexError",
    "get_error_codes_for_component",
    "list_registered_components",
    "register_error_codes",
]
