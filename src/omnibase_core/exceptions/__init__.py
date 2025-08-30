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

        pass


__all__ = ["OnexError", "ModelOnexError", "CLIAdapter"]
