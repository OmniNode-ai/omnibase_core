"""Pydantic model for mixin preset configurations.

This module provides the ModelMixinPreset class for defining
preset configurations for common use cases.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelMixinPreset(BaseModel):
    """Preset configuration for common use cases.

    Attributes:
        description: Preset description
        config: Configuration values
    """

    description: str = Field(..., description="Preset description")
    config: dict[str, Any] = Field(default_factory=dict, description="Config values")
