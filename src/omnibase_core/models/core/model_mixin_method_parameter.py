"""Pydantic model for mixin method parameter definitions.

This module provides the ModelMixinMethodParameter class for defining
method parameters in mixin code patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelMixinMethodParameter(BaseModel):
    """Method parameter definition.

    Attributes:
        name: Parameter name
        type: Parameter type annotation
        default: Default value (None indicates no default; use explicit None for parameters with None default)
        description: Parameter description
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type annotation")
    default: object = Field(
        None,
        description=(
            "Default value for the parameter. "
            "None indicates no default (parameter is required). "
            "Use explicit None in a container (e.g., [None]) to represent 'default is None'."
        ),
    )
    description: str = Field("", description="Parameter description")
