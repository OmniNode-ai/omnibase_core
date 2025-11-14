from typing import Any

from pydantic import Field

"""
Model for YAML schema object representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed YAML schema object definitions.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict

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
