"""Pydantic model for mixin method definitions.

This module provides the ModelMixinMethod class for defining
methods in mixin code patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelMixinMethod(BaseModel):
    """Method definition in code patterns.

    Attributes:
        name: Method name
        signature: Full method signature
        description: Method description
        example: Usage example code
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Method name")
    signature: str = Field(..., description="Full method signature")
    description: str = Field("", description="Method description")
    example: str = Field("", description="Usage example code")
