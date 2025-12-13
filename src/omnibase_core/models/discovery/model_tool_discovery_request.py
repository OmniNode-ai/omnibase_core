"""
Tool Discovery Request Event Model

Event published by services to request discovery of available tools.
The registry responds with a TOOL_DISCOVERY_RESPONSE event.
"""

from pydantic import BaseModel, Field


class ModelDiscoveryFilters(BaseModel):
    """Filters for tool discovery requests"""

    tags: list[str] | None = Field(
        default=None,
        description="Filter by node tags (e.g. ['generator', 'validated'])",
    )
    protocols: list[str] | None = Field(
        default=None,
        description="Filter by supported protocols (e.g. ['mcp', 'graphql'])",
    )
    actions: list[str] | None = Field(
        default=None,
        description="Filter by supported actions (e.g. ['health_check'])",
    )
    node_names: list[str] | None = Field(
        default=None,
        description="Filter by specific node names (e.g. ['node_generator'])",
    )
    exclude_nodes: list[str] | None = Field(
        default=None,
        description="Exclude specific node IDs from results",
    )
    min_trust_score: float | None = Field(
        default=None,
        description="Minimum trust score required (0.0-1.0)",
    )
    datacenter: str | None = Field(
        default=None,
        description="Filter by datacenter (future Consul support)",
    )
    health_status: str | None = Field(
        default=None,
        description="Filter by health status ('healthy', 'warning', 'critical')",
    )
