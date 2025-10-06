from __future__ import annotations

from typing import Dict

from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
Timeout data model.

Typed data model for ModelTimeout serialization.
Follows ONEX one-model-per-file naming conventions.
"""


from typing import Any, Dict

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_runtime_category import EnumRuntimeCategory
from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties


class ModelTimeoutData(BaseModel):
    """
    Typed data model for ModelTimeout serialization.

    Replaces Dict[str, Any] with proper strong typing for timeout serialization.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    timeout_seconds: int = Field(default=..., description="Timeout duration in seconds")
    warning_threshold_seconds: int = Field(
        default=0,
        description="Warning threshold in seconds",
    )
    is_strict: bool = Field(
        default=True,
        description="Whether timeout is strictly enforced",
    )
    allow_extension: bool = Field(
        default=False,
        description="Whether timeout can be extended",
    )
    extension_limit_seconds: int = Field(
        default=0,
        description="Maximum extension time in seconds",
    )
    runtime_category: EnumRuntimeCategory = Field(
        default=EnumRuntimeCategory.FAST,
        description="Runtime category for this timeout",
    )
    description: str = Field(default="", description="Timeout description")
    custom_properties: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
        description="Typed custom properties instead of dict[str, Any]",
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


# Export for use
__all__ = ["ModelTimeoutData"]
