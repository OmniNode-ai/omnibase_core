"""Strongly typed model for MCP tool collections."""

from pydantic import BaseModel, Field

from omnibase_core.model.mcp.model_tool_definition import ModelToolDefinition


class ModelMCPToolCollection(BaseModel):
    """Strongly typed model for external tool collections."""

    tools: dict[str, ModelToolDefinition] = Field(
        default_factory=dict,
        description="Collection of MCP tools",
    )

    def add_tool(self, name: str, tool_definition: ModelToolDefinition) -> None:
        """Add a tool to the collection."""
        self.tools[name] = tool_definition

    def get_tool(self, name: str) -> ModelToolDefinition:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tool_names(self) -> list[str]:
        """List all tool names in the collection."""
        return list(self.tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool exists in the collection."""
        return name in self.tools
