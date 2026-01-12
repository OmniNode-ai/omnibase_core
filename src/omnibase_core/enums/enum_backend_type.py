"""
EnumBackendType: Enumeration of secret backend types.

This enum defines the supported secret backend types in the system.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


@unique
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
            # Lazy import to avoid circular dependency with error_codes
            from omnibase_core.errors import ModelOnexError

            msg = f"Invalid backend type: {value}. Must be one of: {[e.value for e in cls]}"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR)
