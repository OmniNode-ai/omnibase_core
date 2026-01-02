"""
Tools by Type Collection Model for ONEX Configuration System.

Strongly typed model for tools filtered by type.
"""

from pydantic import BaseModel, Field


class ModelToolsByType(BaseModel):
    """
    Strongly typed model for tools filtered by type.

    Represents a collection of tools of a specific type with proper type safety.
    """

    tools: dict[str, str] = Field(
        default_factory=dict,
        description="Tools by name with their type information",
    )

    def get_tool(self, tool_name: str) -> str:
        """Get a tool type by name."""
        return self.tools.get(tool_name, "")

    def has_tool(self, tool_name: str) -> bool:
        """Check if tool exists in collection."""
        return tool_name in self.tools

    def add_tool(self, tool_name: str, tool_type: str) -> None:
        """Add a tool with its type."""
        self.tools[tool_name] = tool_type

    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from collection."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            return True
        return False

    def get_tool_count(self) -> int:
        """Get total count of tools."""
        return len(self.tools)

    def get_tool_names(self) -> list[str]:
        """Get list of all tool names."""
        return list(self.tools.keys())
