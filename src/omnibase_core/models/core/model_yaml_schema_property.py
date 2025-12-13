"""
Model for YAML schema property representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed YAML schema property definitions.

"""

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlSchemaProperty(BaseModel):
    """Model representing a YAML schema property definition."""

    model_config = ConfigDict(extra="ignore")

    property_type: str = Field(
        default=...,
        description="Property type (string, integer, object, array, etc.)",
    )
    description: str = Field(default="", description="Property description")
    required: bool = Field(
        default=False,
        description="Whether this property is required",
    )
    default_value: str = Field(default="", description="Default value as string")
    enum_values: list[str] = Field(
        default_factory=list,
        description="Enum values if applicable",
    )
    ref_path: str = Field(default="", description="Reference path if this is a $ref")
    format_type: str = Field(default="", description="Format type (path, uuid, etc.)")
    min_value: int = Field(default=0, description="Minimum value for numeric types")
    max_value: int = Field(default=0, description="Maximum value for numeric types")
