from pydantic import Field

"\nModelSessionAffinityMetadata - Session affinity configuration for load balancing\n\nSession affinity model for configuring sticky sessions and client-to-node\nrouting persistence in load balancing systems.\n"

from pydantic import BaseModel


class ModelSessionAffinityMetadata(BaseModel):
    """Metadata for session affinity configuration."""

    session_id_format: str = Field(
        default="uuid",
        description="Format for session IDs",
        pattern="^(uuid|ulid|nanoid|custom)$",
    )
    include_timestamp: bool = Field(
        default=True, description="Include timestamp in session metadata"
    )
    include_user_agent: bool = Field(
        default=True, description="Include user agent in affinity calculation"
    )
    include_accept_language: bool = Field(
        default=False, description="Include accept-language header in affinity"
    )
    include_geo_location: bool = Field(
        default=False, description="Include geo-location in affinity calculation"
    )
    persist_across_restarts: bool = Field(
        default=False, description="Persist affinity data across server restarts"
    )
    storage_backend: str | None = Field(
        default=None,
        description="Storage backend for persistent affinity",
        pattern="^(redis|memcached|dynamodb|custom)$",
    )
    preferred_node_tags: list[str] = Field(
        default_factory=list, description="Preferred node tags for affinity"
    )
    excluded_node_tags: list[str] = Field(
        default_factory=list, description="Node tags to exclude from affinity"
    )
    failover_priority: list[str] = Field(
        default_factory=list, description="Failover node priority order"
    )
    preserve_session_data: bool = Field(
        default=True, description="Preserve session data during failover"
    )
    track_session_metrics: bool = Field(
        default=True, description="Track session-level metrics"
    )
    metrics_sampling_rate: float = Field(
        default=1.0, description="Sampling rate for session metrics", ge=0.0, le=1.0
    )
    custom_extractors: dict[str, str] = Field(
        default_factory=dict, description="Custom field extractors (name: regex)"
    )
