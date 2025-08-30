"""Discovery cache model for persistent tool discovery caching."""

from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field

from omnibase_core.model.discovery.model_tool_discovery_response import \
    ModelDiscoveredTool


class ModelDiscoveryCache(BaseModel):
    """Cache for discovered tools with TTL management."""

    tools: Dict[str, ModelDiscoveredTool] = Field(
        default_factory=dict, description="Cached discovered tools keyed by node_name"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When cache was last updated"
    )
    ttl_seconds: int = Field(
        default=300, description="Time-to-live for cache entries in seconds"
    )

    def is_valid(self) -> bool:
        """Check if cache is still valid based on TTL and has content."""
        if not self.timestamp:
            return False

        # Cache is only valid if it has content and is within TTL
        age_seconds = (datetime.now() - self.timestamp).total_seconds()
        return len(self.tools) > 0 and age_seconds < self.ttl_seconds

    def add_tool(self, tool: ModelDiscoveredTool) -> None:
        """Add a tool to the cache."""
        self.tools[tool.node_name] = tool
        self.timestamp = datetime.now()

    def get_tool(self, node_name: str) -> ModelDiscoveredTool:
        """Get a tool from cache by node name."""
        return self.tools.get(node_name)

    def clear(self) -> None:
        """Clear all cached tools."""
        self.tools.clear()
        self.timestamp = datetime.now()
