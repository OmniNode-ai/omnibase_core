"""
MCP Tool Input Schema Model.

Model for MCP tool input schema.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.decorators.pattern_exclusions import allow_dict_str_any


@allow_dict_str_any("json_schema_properties_for_mcp_protocol")
class ModelMCPToolInputSchema(BaseModel):
    """
    MCP tool input schema model.
    """

    type: str = Field(default="object", description="Schema type")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Schema properties",
    )
    required: list[str] = Field(default_factory=list, description="Required properties")
