"""
Model for YAML schema object representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed YAML schema object definitions.

Author: ONEX Framework Team
"""

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.models.model_yaml_schema_property import \
    ModelYamlSchemaProperty


class ModelYamlSchemaObject(BaseModel):
    """Model representing a YAML schema object definition."""

    model_config = ConfigDict(extra="ignore")

    object_type: str = Field(
        ..., description="Object type (always 'object' for schema objects)"
    )
    properties: Dict[str, ModelYamlSchemaProperty] = Field(
        default_factory=dict, description="Object properties"
    )
    required_properties: List[str] = Field(
        default_factory=list, description="Required property names"
    )
    description: str = Field(default="", description="Object description")
