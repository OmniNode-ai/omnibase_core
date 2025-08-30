"""
EnumBackendType: Enumeration of secret backend types.

This enum defines the supported secret backend types in the system.
"""

from enum import Enum


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
            raise ValueError(
                f"Invalid backend type: {value}. Must be one of: {[e.value for e in cls]}"
            )
