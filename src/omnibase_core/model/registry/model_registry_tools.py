#!/usr/bin/env python3
"""
ModelRegistryTools - Registry tool storage model.

Strongly typed Pydantic model for tool registration and instance management.
Replaces Dict[str, Type] and Dict[str, object] patterns.
"""


from pydantic import BaseModel, Field


class ModelRegistryTools(BaseModel):
    """
    Strongly typed model for registry tool storage.

    Replaces Dict[str, Type] and Dict[str, object] patterns with proper validation.
    """

    registered_tools: dict[str, str] = Field(
        default_factory=dict,
        description="Map of tool names to their class names (for serialization)",
    )

    tool_instances_active: dict[str, bool] = Field(
        default_factory=dict,
        description="Track which tool instances are currently active",
    )

    tool_validation_status: dict[str, bool] = Field(
        default_factory=dict,
        description="Track validation status for each registered tool",
    )

    def register_tool(self, name: str, tool_class: type) -> None:
        """Register a tool class by name."""
        self.registered_tools[name] = tool_class.__name__
        self.tool_instances_active[name] = False
        self.tool_validation_status[name] = False

    def is_tool_registered(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self.registered_tools

    def mark_instance_active(self, name: str) -> None:
        """Mark a tool instance as active."""
        if name in self.registered_tools:
            self.tool_instances_active[name] = True

    def mark_tool_validated(self, name: str) -> None:
        """Mark a tool as validated."""
        if name in self.registered_tools:
            self.tool_validation_status[name] = True

    def get_registered_tool_names(self) -> list[str]:
        """Get list of all registered tool names."""
        return list(self.registered_tools.keys())

    def get_tool_count(self) -> int:
        """Get count of registered tools."""
        return len(self.registered_tools)
