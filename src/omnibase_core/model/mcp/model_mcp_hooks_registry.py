"""Strongly typed model for MCP tool hooks registry."""

from typing import Callable, Dict, List

from pydantic import BaseModel, Field


class ModelMCPHookDefinition(BaseModel):
    """Model for a single MCP hook definition."""

    tool_name: str = Field(..., description="Name of the tool to hook")
    original_function: Callable = Field(..., description="Original tool function")
    hook_function: Callable = Field(..., description="Hooked version of the function")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True  # Required for Callable


class ModelMCPHooksRegistry(BaseModel):
    """Strongly typed model for MCP tool hooks registry."""

    hooks: Dict[str, ModelMCPHookDefinition] = Field(
        default_factory=dict, description="Registry of tool hooks"
    )

    def register_hook(
        self, tool_name: str, original_function: Callable, hook_function: Callable
    ) -> None:
        """Register a new tool hook."""
        self.hooks[tool_name] = ModelMCPHookDefinition(
            tool_name=tool_name,
            original_function=original_function,
            hook_function=hook_function,
        )

    def get_hook(self, tool_name: str) -> ModelMCPHookDefinition:
        """Get a hook by tool name."""
        return self.hooks.get(tool_name)

    def list_hooked_tools(self) -> List[str]:
        """List all hooked tool names."""
        return list(self.hooks.keys())

    def has_hook(self, tool_name: str) -> bool:
        """Check if a tool has a registered hook."""
        return tool_name in self.hooks
