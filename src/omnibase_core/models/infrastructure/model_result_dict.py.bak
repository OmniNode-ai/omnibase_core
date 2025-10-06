from __future__ import annotations

from typing import Dict

from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
Result Dictionary Model.

Clean Pydantic model for Result serialization following ONEX one-model-per-file architecture.
"""


from typing import Any, Dict

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError

from .model_cli_value import ModelCliValue
from .model_error_value import ModelErrorValue


class ModelResultDict(BaseModel):
    """
    Clean Pydantic model for Result serialization.

    Represents the dict[str, Any]ionary structure when converting Results
    to/from dict[str, Any]ionary format with proper type safety.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    value: ModelCliValue | None = Field(
        None,
        description="Success value (if success=True)",
    )
    error: ModelErrorValue | None = Field(
        None,
        description="Error value (if success=False)",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations
    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Type alias for dict[str, Any]ionary-based data structures
ModelResultData = dict[
    str, ModelCliValue
]  # Strongly-typed dict[str, Any]for common data


# Export for use
__all__ = ["ModelResultData", "ModelResultDict"]
