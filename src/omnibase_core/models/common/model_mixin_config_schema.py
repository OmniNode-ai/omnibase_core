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

    Supports two input formats:
    1. Structured format (explicit):
       ```yaml
       config_schema:
         properties:
           max_retries:
             type: integer
             default: 3
         required_properties: []
       ```

    2. Flat format (JSON Schema style, from YAML):
       ```yaml
       config_schema:
         max_retries:
           type: integer
           default: 3
       ```

    The flat format is automatically converted to structured format during validation.
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

    @model_validator(mode="before")
    @classmethod
    def convert_flat_format(
        cls, values: dict[str, object] | object
    ) -> dict[str, object] | object:
        """Convert flat JSON Schema format to structured format.

        The YAML mixin_metadata.yaml uses a flat format where property names
        are directly under config_schema, each with their schema definition.
        This validator converts that to our structured format with an explicit
        'properties' key.

        Flat format (input):
            max_retries:
              type: integer
              default: 3
            base_delay:
              type: float
              default: 1.0

        Structured format (output):
            properties:
              max_retries:
                type: integer
                default: 3
              base_delay:
                type: float
                default: 1.0
            required_properties: []
            additional_properties_allowed: true
        """
        if not isinstance(values, dict):
            return values

        # If 'properties' key exists, assume it's already structured format
        if "properties" in values:
            return values

        # Check if this looks like flat format (dict values that are dicts with 'type' key)
        # vs empty dict or already structured format
        flat_properties: dict[str, object] = {}
        remaining: dict[str, object] = {}

        for key, value in values.items():
            # Reserved keys for structured format
            if key in ("required_properties", "additional_properties_allowed"):
                remaining[key] = value
            # Check if value looks like a JSON Schema property definition
            elif isinstance(value, dict) and "type" in value:
                flat_properties[key] = value
            else:
                # Unknown key, keep it (will be rejected by extra="forbid" if invalid)
                remaining[key] = value

        # If we found flat properties, convert to structured format
        if flat_properties:
            return {
                "properties": flat_properties,
                **remaining,
            }

        # No flat properties found, return as-is (empty or already structured)
        return values

    @model_validator(mode="after")
    def _validate_required_properties_subset(self) -> Self:
        """Validate that required_properties is a subset of properties keys."""
        if not self.required_properties:
            return self

        property_names = set(self.properties.keys())
        required_set = set(self.required_properties)
        undefined_required = required_set - property_names

        if undefined_required:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                f"required_properties contains undefined properties: "
                f"{sorted(undefined_required)}. "
                f"Valid properties are: {sorted(property_names)}"
            )

        return self


__all__ = ["ModelMixinConfigSchema"]
