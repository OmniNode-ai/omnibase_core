"""Pydantic model for mixin property definitions.

This module provides the ModelMixinProperty class for defining
properties in mixin code patterns.
"""

from pydantic import BaseModel, Field


class ModelMixinProperty(BaseModel):
    """Property definition in code patterns.

    Attributes:
        name: Property name
        type: Property type annotation
        description: Property description
    """

    name: str = Field(..., description="Property name")
    type: str = Field(..., description="Property type annotation")
    description: str = Field("", description="Property description")
