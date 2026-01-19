"""MCP tool configuration model.

Defines the `mcp:` block schema for ONEX contract.yaml files.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.mcp.model_mcp_parameter_mapping import (
    ModelMCPParameterMapping,
)


class ModelMCPToolConfig(BaseModel):
    """Configuration for exposing an ONEX node as an MCP tool.

    This model defines the `mcp:` block in contract.yaml files, controlling
    how nodes are exposed to AI agents via the Model Context Protocol.

    Example contract.yaml usage:
        ```yaml
        mcp:
          expose: true
          tool_name: search_documents
          description: "Search documents by query and filters"
          parameter_mappings:
            - name: query
              onex_field: input.search_query
              parameter_type: STRING
              required: true
              description: "Search query string"
        ```

    Attributes:
        expose: Whether to expose this node as an MCP tool.
        tool_name: Custom tool name (defaults to node name if not set).
        description: AI-friendly description of what the tool does.
        parameter_mappings: List of parameter mapping definitions.
        tags: Categorization tags for tool discovery.
        timeout_seconds: Execution timeout for the tool.
        retry_enabled: Whether retries are allowed on failure.
        max_retries: Maximum retry attempts if retry_enabled is True.
        requires_confirmation: Whether to require user confirmation before execution.
        dangerous: Mark as dangerous operation (destructive, irreversible).
    """

    expose: bool = Field(
        default=False, description="Whether to expose this node as an MCP tool"
    )
    tool_name: str | None = Field(
        default=None,
        description="Custom tool name (defaults to node name if not set)",
    )
    description: str | None = Field(
        default=None, description="AI-friendly description of what the tool does"
    )
    parameter_mappings: list[ModelMCPParameterMapping] = Field(
        default_factory=list, description="List of parameter mapping definitions"
    )
    tags: list[str] = Field(
        default_factory=list, description="Categorization tags for tool discovery"
    )
    timeout_seconds: int = Field(
        default=30, description="Execution timeout for the tool", ge=1, le=600
    )
    retry_enabled: bool = Field(
        default=True, description="Whether retries are allowed on failure"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts if retry_enabled is True",
        ge=0,
        le=10,
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether to require user confirmation before execution",
    )
    dangerous: bool = Field(
        default=False,
        description="Mark as dangerous operation (destructive, irreversible)",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    def is_enabled(self) -> bool:
        """Check if MCP exposure is enabled.

        Returns:
            True if expose is True, False otherwise.
        """
        return self.expose

    def get_required_parameters(self) -> list[ModelMCPParameterMapping]:
        """Get all required parameters.

        Returns:
            List of parameter mappings where required is True.
        """
        return [p for p in self.parameter_mappings if p.required]

    def get_optional_parameters(self) -> list[ModelMCPParameterMapping]:
        """Get all optional parameters.

        Returns:
            List of parameter mappings where required is False.
        """
        return [p for p in self.parameter_mappings if not p.required]


__all__ = ["ModelMCPToolConfig"]
