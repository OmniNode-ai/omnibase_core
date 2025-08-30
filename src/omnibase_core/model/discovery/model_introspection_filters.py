"""
Introspection Filters Model

Filters for targeting specific nodes in request-response introspection.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelIntrospectionFilters(BaseModel):
    """Filters for targeting specific nodes in introspection requests"""

    node_type: Optional[List[str]] = Field(
        None, description="Filter by node types (e.g., ['service', 'tool'])"
    )
    capabilities: Optional[List[str]] = Field(
        None,
        description="Filter by required capabilities (e.g., ['generation', 'validation'])",
    )
    protocols: Optional[List[str]] = Field(
        None, description="Filter by supported protocols (e.g., ['mcp', 'graphql'])"
    )
    tags: Optional[List[str]] = Field(
        None, description="Filter by node tags (e.g., ['production', 'mcp'])"
    )
    status: Optional[List[str]] = Field(
        None, description="Filter by current status (e.g., ['ready', 'busy'])"
    )
    node_names: Optional[List[str]] = Field(
        None, description="Filter by specific node names"
    )
