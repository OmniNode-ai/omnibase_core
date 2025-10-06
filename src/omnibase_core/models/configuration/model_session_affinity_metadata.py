import uuid

from pydantic import Field

"""
ModelSessionAffinityMetadata - Session affinity configuration for load balancing

Session affinity model for configuring sticky sessions and client-to-node
routing persistence in load balancing systems.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelSessionAffinityMetadata(BaseModel):
    """Metadata for session affinity configuration."""

    # Session tracking
    session_id_format: str = Field(
        "uuid",
        description="Format for session IDs",
        pattern="^(uuid|ulid|nanoid|custom)$",
    )
    include_timestamp: bool = Field(
        True,
        description="Include timestamp in session metadata",
    )

    # Client identification
    include_user_agent: bool = Field(
        True,
        description="Include user agent in affinity calculation",
    )
    include_accept_language: bool = Field(
        False,
        description="Include accept-language header in affinity",
    )
    include_geo_location: bool = Field(
        False,
        description="Include geo-location in affinity calculation",
    )

    # Session persistence
    persist_across_restarts: bool = Field(
        False,
        description="Persist affinity data across server restarts",
    )
    storage_backend: str | None = Field(
        default=None,
        description="Storage backend for persistent affinity",
        pattern="^(redis|memcached|dynamodb|custom)$",
    )

    # Load balancing hints
    preferred_node_tags: list[str] = Field(
        default_factory=list,
        description="Preferred node tags for affinity",
    )
    excluded_node_tags: list[str] = Field(
        default_factory=list,
        description="Node tags to exclude from affinity",
    )

    # Failover behavior
    failover_priority: list[str] = Field(
        default_factory=list,
        description="Failover node priority order",
    )
    preserve_session_data: bool = Field(
        True,
        description="Preserve session data during failover",
    )

    # Monitoring
    track_session_metrics: bool = Field(
        default=True, description="Track session-level metrics"
    )
    metrics_sampling_rate: float = Field(
        1.0,
        description="Sampling rate for session metrics",
        ge=0.0,
        le=1.0,
    )

    # Custom extensions
    custom_extractors: dict[str, str] = Field(
        default_factory=dict,
        description="Custom field extractors (name: regex)",
    )
