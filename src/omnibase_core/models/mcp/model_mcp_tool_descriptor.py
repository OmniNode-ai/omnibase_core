"""MCP tool descriptor model.

Generated tool definition for MCP protocol registration.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_mcp_tool_type import EnumMCPToolType
from omnibase_core.models.mcp.model_mcp_parameter_mapping import (
    ModelMCPParameterMapping,
)
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)


class ModelMCPToolDescriptor(BaseModel):
    """Complete MCP tool definition for registration.

    This model represents a fully-formed tool definition that can be
    registered with an MCP server for AI agent discovery and invocation.

    Attributes:
        name: Unique tool identifier.
        tool_type: Type of MCP tool (function, resource, etc.).
        description: Human-readable description for AI agents.
        version: Semantic version of the tool.
        parameters: List of parameter definitions.
        return_schema: JSON Schema for the return value.
        input_schema: Full JSON Schema for input validation.
        timeout_seconds: Execution timeout.
        retry_count: Number of retry attempts on failure.
        requires_auth: Whether authentication is required.
        tags: Categorization tags for discovery.
        metadata: Additional tool metadata.
        node_name: Source ONEX node name (if generated from contract).
        node_version: Source ONEX node version (ModelSemVer).
        dangerous: Whether this tool performs dangerous operations.
        requires_confirmation: Whether user confirmation is required.
    """

    name: str = Field(..., description="Unique tool identifier")
    tool_type: EnumMCPToolType = Field(
        default=EnumMCPToolType.FUNCTION,
        description="Type of MCP tool (function, resource, etc.)",
    )
    description: str = Field(
        ..., description="Human-readable description for AI agents"
    )
    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Semantic version of the tool",
    )
    parameters: list[ModelMCPParameterMapping] = Field(
        default_factory=list, description="List of parameter definitions"
    )
    return_schema: dict[str, object] | None = Field(
        default=None, description="JSON Schema for the return value"
    )
    input_schema: dict[str, object] | None = Field(
        default=None, description="Full JSON Schema for input validation"
    )
    timeout_seconds: int = Field(
        default=30, description="Execution timeout", ge=1, le=600
    )
    retry_count: int = Field(
        default=3, description="Number of retry attempts on failure", ge=0, le=10
    )
    requires_auth: bool = Field(
        default=False, description="Whether authentication is required"
    )
    tags: list[str] = Field(
        default_factory=list, description="Categorization tags for discovery"
    )
    metadata: dict[str, object] = Field(
        default_factory=dict, description="Additional tool metadata"
    )
    node_name: str | None = Field(
        default=None, description="Source ONEX node name (if generated from contract)"
    )
    node_version: ModelSemVer | None = Field(
        default=None, description="Source ONEX node version"
    )
    dangerous: bool = Field(
        default=False, description="Whether this tool performs dangerous operations"
    )
    requires_confirmation: bool = Field(
        default=False, description="Whether user confirmation is required"
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    def get_required_parameters(self) -> list[ModelMCPParameterMapping]:
        """Get all required parameters.

        Returns:
            List of parameter mappings where required is True.
        """
        return [p for p in self.parameters if p.required]

    def get_optional_parameters(self) -> list[ModelMCPParameterMapping]:
        """Get all optional parameters.

        Returns:
            List of parameter mappings where required is False.
        """
        return [p for p in self.parameters if not p.required]

    def to_input_schema(self) -> dict[str, object]:
        """Generate JSON Schema for tool input.

        If input_schema is already set, returns it. Otherwise generates
        from parameters.

        Returns:
            JSON Schema dict for tool input.
        """
        if self.input_schema is not None:
            return self.input_schema

        properties: dict[str, object] = {}
        required: list[str] = []

        for param in self.parameters:
            effective_name = param.get_effective_name()
            properties[effective_name] = param.to_json_schema()
            if param.required:
                required.append(effective_name)

        schema: dict[str, object] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        return schema

    def has_tag(self, tag: str) -> bool:
        """Check if the tool has a specific tag.

        Args:
            tag: Tag to check for.

        Returns:
            True if tag is present (case-insensitive).
        """
        return tag.lower() in [t.lower() for t in self.tags]

    def is_from_onex_node(self) -> bool:
        """Check if this tool was generated from an ONEX node.

        Returns:
            True if node_name is set.
        """
        return self.node_name is not None


__all__ = ["ModelMCPToolDescriptor"]
