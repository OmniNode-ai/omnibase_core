"""
Typed schema property model for mixin configuration.

This module provides strongly-typed schema properties for configuration patterns.
"""

from pydantic import BaseModel, Field


class ModelConfigSchemaProperty(BaseModel):
    """
    Typed schema property for mixin configuration.

    Replaces nested dict[str, Any] in config_schema field
    with explicit typed fields for JSON Schema properties.
    """

    type: str = Field(
        default="string",
        description="Property type (string, number, boolean, array, object)",
    )
    description: str | None = Field(
        default=None,
        description="Property description",
    )
    default: str | None = Field(
        default=None,
        description="Default value as string",
    )
    enum: list[str] | None = Field(
        default=None,
        description="Allowed values for enum types",
    )
    required: bool = Field(
        default=False,
        description="Whether this property is required",
    )
    min_value: float | None = Field(
        default=None,
        description="Minimum value for numeric types",
    )
    max_value: float | None = Field(
        default=None,
        description="Maximum value for numeric types",
    )


__all__ = ["ModelConfigSchemaProperty"]
