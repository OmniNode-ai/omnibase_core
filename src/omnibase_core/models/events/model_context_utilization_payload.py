"""Context utilization event payload.

Tracks whether injected context was actually used by the agent.

Topic Constant:
    See omnibase_core.constants.constants_topic_taxonomy:
    - TOPIC_INJECTION_CONTEXT_UTILIZATION

Thread Safety:
    Model is frozen (immutable) and thread-safe for concurrent access.

Related:
    OMN-1889: Emitter implementation in omniclaude
    OMN-1890: Consumer implementation in omnibase_infra
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["ModelContextUtilizationPayload"]


class ModelContextUtilizationPayload(ModelEventPayloadBase):
    """Track whether injected context was actually used by the agent.

    Measures the effectiveness of context injection by comparing what was
    injected versus what the agent actually referenced or utilized.

    Attributes:
        session_ref: External reference for the agent session.
        utilization_score: Ratio of utilized context (0.0 = none used, 1.0 = all used).
        utilization_method: How utilization was measured.
        injected_count: Number of context items/tokens injected.
        reused_count: Number of injected items actually referenced.
        timestamp: When the measurement was taken (timezone-aware UTC).

    Example:
        >>> payload = ModelContextUtilizationPayload(
        ...     session_ref="sess-123",
        ...     utilization_score=0.75,
        ...     utilization_method="identifier_match",
        ...     injected_count=10,
        ...     reused_count=7,
        ...     timestamp=datetime.now(UTC),
        ... )
    """

    session_ref: str = Field(
        ...,
        min_length=1,
        description="External reference for the agent session",
    )
    utilization_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of utilized context (0.0-1.0)",
    )
    utilization_method: Literal["identifier_match", "semantic", "heuristic"] = Field(
        ...,
        description="Method used to measure utilization",
    )
    injected_count: int = Field(
        ...,
        ge=0,
        description="Number of context items/tokens injected",
    )
    reused_count: int = Field(
        ...,
        ge=0,
        description="Number of injected items actually referenced",
    )
    timestamp: datetime = Field(
        ...,
        description="When the measurement was taken (timezone-aware UTC)",
    )
