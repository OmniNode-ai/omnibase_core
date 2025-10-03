"""YAML schema object model for ContractLoader."""

from typing import Any

from pydantic import BaseModel, Field


class ModelYamlSchemaObject(BaseModel):
    """YAML schema object representation."""

    object_type: str = Field(default="object", description="Schema type")
    description: str = Field(default="", description="Schema description")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Schema properties"
    )
    required: list[str] = Field(default_factory=list, description="Required properties")

    model_config = {
        "extra": "allow",
    }
