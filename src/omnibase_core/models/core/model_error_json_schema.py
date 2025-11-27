"""
Error JSON schema model for ONEX core.
"""

from pydantic import BaseModel, Field


class ModelErrorJsonSchema(BaseModel):
    """Strong typing for JSON schema data."""

    schema_type: str = Field(default="object", description="Schema type")
    properties: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Schema properties",
    )
    required_fields: list[str] = Field(
        default_factory=list,
        description="Required fields",
    )
    definitions: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Schema definitions",
    )
