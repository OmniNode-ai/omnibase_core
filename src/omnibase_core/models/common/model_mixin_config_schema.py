"""
Typed configuration schema model for mixins.

This module provides strongly-typed configuration schemas for mixin patterns.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .model_config_schema_property import ModelConfigSchemaProperty


class ModelMixinConfigSchema(BaseModel):
    """
    Typed configuration schema for mixins.

    Replaces dict[str, Any] config_schema field in ModelMixinInfo
    with explicit typed fields for mixin configuration.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

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

    @model_validator(mode="after")
    def _validate_required_properties_subset(self) -> Self:
        """Validate that required_properties is a subset of properties keys."""
        if not self.required_properties:
            return self

        property_names = set(self.properties.keys())
        required_set = set(self.required_properties)
        undefined_required = required_set - property_names

        if undefined_required:
            raise ValueError(
                f"required_properties contains undefined properties: "
                f"{sorted(undefined_required)}. "
                f"Valid properties are: {sorted(property_names)}"
            )

        return self


__all__ = ["ModelMixinConfigSchema"]
