"""
Typed configuration schema model for mixins.

This module provides strongly-typed configuration schemas for mixin patterns.
"""

from pydantic import BaseModel, Field

from .model_config_schema_property import ModelConfigSchemaProperty


class ModelMixinConfigSchema(BaseModel):
    """
    Typed configuration schema for mixins.

    Replaces dict[str, Any] config_schema field in ModelMixinInfo
    with explicit typed fields for mixin configuration.
    """

    properties: dict[str, ModelConfigSchemaProperty] = Field(
        default_factory=dict,
        description="Schema properties mapped by name",
    )
    required_properties: list[str] = Field(
        default_factory=list,
        description="List of required property names",
    )
    additional_properties_allowed: bool = Field(
        default=True,
        description="Whether additional properties are allowed",
    )


__all__ = ["ModelMixinConfigSchema"]
