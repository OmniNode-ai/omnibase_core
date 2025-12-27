"""
Model for YAML schema object representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed YAML schema object definitions.

"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.core.model_yaml_schema_property import ModelYamlSchemaProperty


class ModelYamlSchemaObject(BaseModel):
    """Model representing a YAML schema object definition."""

    model_config = ConfigDict(extra="ignore")

    object_type: str = Field(
        default=...,
        description="Object type (always 'object' for schema objects)",
    )
    properties: dict[str, ModelYamlSchemaProperty] = Field(
        default_factory=dict,
        description="Object properties",
    )
    required_properties: list[str] = Field(
        default_factory=list,
        description="Required property names",
    )
    description: str = Field(default="", description="Object description")

    @model_validator(mode="after")
    def _validate_required_properties_subset(self) -> "ModelYamlSchemaObject":
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
