"""
Timeout data model.

Typed data model for ModelTimeout serialization.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_runtime_category import EnumRuntimeCategory
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties


class ModelTimeoutData(BaseModel):
    """
    Typed data model for ModelTimeout serialization.

    Replaces Dict[str, Any] with proper strong typing for timeout serialization.
    """

    timeout_seconds: int = Field(..., description="Timeout duration in seconds")
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
        description="Typed custom properties instead of dict",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelTimeoutData"]
