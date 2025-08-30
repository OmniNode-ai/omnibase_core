"""Strongly typed model for conversation capture tool registry."""

from typing import Callable, Dict, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.mcp.model_tool_definition import ModelToolDefinition


class ModelConversationToolRegistry(BaseModel):
    """Strongly typed registry for conversation capture tools."""

    tools: Dict[str, ModelToolDefinition] = Field(
        default_factory=dict, description="Registry of conversation capture tools"
    )

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True  # Allow Callable type

    def register_tool(
        self, name: str, description: str, handler: Callable, parameters: dict
    ) -> None:
        """Register a new tool."""
        self.tools[name] = ModelToolDefinition(
            name=name, description=description, handler=handler, parameters=parameters
        )

    def get_tool(self, name: str) -> Optional[ModelToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self.tools.keys())

    def get_all_tools(self) -> Dict[str, ModelToolDefinition]:
        """Get all tools as a dictionary."""
        return self.tools
