"""Pydantic model for mixin method parameter definitions.

This module provides the ModelMixinMethodParameter class for defining
method parameters in mixin code patterns.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelMixinMethodParameter(BaseModel):
    """Method parameter definition.

    Attributes:
        name: Parameter name
        type: Parameter type annotation
        default: Default value (if optional)
        description: Parameter description
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type annotation")
    default: Any = Field(None, description="Default value")
    description: str = Field("", description="Parameter description")
