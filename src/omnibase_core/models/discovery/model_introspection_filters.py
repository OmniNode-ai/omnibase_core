"""
Introspection Filters Model

Filters for targeting specific nodes in request-response introspection.
"""

from pydantic import BaseModel, Field


class ModelIntrospectionFilters(BaseModel):
    """Filters for targeting specific nodes in introspection requests"""

    node_type: list[str] | None = Field(
        default=None,
        description="Filter by node types (e.g., ['service', 'tool'])",
    )
    capabilities: list[str] | None = Field(
        default=None,
        description="Filter by required capabilities (e.g., ['generation', 'validation'])",
    )
    protocols: list[str] | None = Field(
        default=None,
        description="Filter by supported protocols (e.g., ['mcp', 'graphql'])",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Filter by node tags (e.g., ['production', 'mcp'])",
    )
    status: list[str] | None = Field(
        default=None,
        description="Filter by current status (e.g., ['ready', 'busy'])",
    )
    node_names: list[str] | None = Field(
        default=None,
        description="Filter by specific node names",
    )
