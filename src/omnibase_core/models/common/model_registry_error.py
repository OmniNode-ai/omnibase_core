"""
Canonical error model for registry errors (tool/handler registries).
Use this for all structured registry error reporting.
"""

from __future__ import annotations

from typing import Any

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.enums.enum_registry_error_code import EnumRegistryErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelRegistryError(ModelOnexError):
    """
    Canonical error model for registry errors (tool/handler registries).
    Use this for all structured registry error reporting.
    """

    def __init__(
        self,
        message: str,
        error_code: EnumRegistryErrorCode,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        **context: Any,
    ) -> None:
        """
        Initialize a registry error with structured error code.

        Args:
            message: Human-readable error message
            error_code: Canonical registry error code
            status: EnumOnexStatus for this error (default: ERROR)
            **context: Additional context information
        """
        super().__init__(
            message=message,
            error_code=error_code,
            status=status,
            **context,
        )


# Export for use
__all__ = [
    "ModelRegistryError",
]
