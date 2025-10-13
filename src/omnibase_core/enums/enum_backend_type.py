from omnibase_core.errors.model_onex_error import ModelOnexError

"""
EnumBackendType: Enumeration of secret backend types.

This enum defines the supported secret backend types in the system.
"""

from enum import Enum

from omnibase_core.errors.error_codes import EnumCoreErrorCode


class EnumBackendType(Enum):
    """Supported secret backend types."""

    ENVIRONMENT = "environment"
    DOTENV = "dotenv"
    VAULT = "vault"
    KUBERNETES = "kubernetes"
    FILE = "file"

    @classmethod
    def from_string(cls, value: str) -> "EnumBackendType":
        """Convert string to backend type."""
        try:
            return cls(value.lower())
        except ValueError:
            msg = f"Invalid backend type: {value}. Must be one of: {[e.value for e in cls]}"
            raise ModelOnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR)
