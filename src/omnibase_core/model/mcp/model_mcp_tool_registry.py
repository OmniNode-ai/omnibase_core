"""
ONEX Model: MCP Tool Registry Model

Strongly typed model for MCP tool registry.
"""

from collections.abc import Callable

from pydantic import BaseModel, Field


class ModelMCPToolDefinition(BaseModel):
    """Model for a single MCP tool definition."""

    name: str = Field(..., description="Tool name")
    handler: Callable | None = Field(None, description="Tool handler function")
    description: str = Field("", description="Tool description")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True  # Required for Callable


class ModelMCPToolRegistry(BaseModel):
    """Strongly typed model for MCP tool registry."""

    tools: list[ModelMCPToolDefinition] = Field(
        default_factory=list,
        description="Registry of available tools",
    )

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str = "",
    ) -> None:
        """Register a new tool."""
        # Remove existing tool with same name if it exists
        self.tools = [t for t in self.tools if t.name != name]

        # Add new tool
        self.tools.append(
            ModelMCPToolDefinition(name=name, handler=handler, description=description),
        )

    def get_tool(self, name: str) -> ModelMCPToolDefinition | None:
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return [tool.name for tool in self.tools]
