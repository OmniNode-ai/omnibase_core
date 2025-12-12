"""Pydantic model for mixin preset configurations.

This module provides the ModelMixinPreset class for defining
preset configurations for common use cases.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelMixinPreset(BaseModel):
    """Preset configuration for common use cases.

    Attributes:
        description: Preset description
        config: Configuration values
    """

    description: str = Field(..., description="Preset description")
    config: SerializedDict = Field(default_factory=dict, description="Config values")
