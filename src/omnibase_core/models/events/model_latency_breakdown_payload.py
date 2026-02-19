# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Latency breakdown event payload.

Provides detailed timing including user-perceived latency.

Topic Constant:
    See omnibase_core.constants.constants_topic_taxonomy:
    - TOPIC_INJECTION_LATENCY_BREAKDOWN

Thread Safety:
    Model is frozen (immutable) and thread-safe for concurrent access.

Related:
    OMN-1889: Emitter implementation in omniclaude
    OMN-1890: Consumer implementation in omnibase_infra
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["ModelLatencyBreakdownPayload"]


class ModelLatencyBreakdownPayload(ModelEventPayloadBase):
    """Detailed timing including user-perceived latency.

    Breaks down the total latency into component phases to identify
    bottlenecks and optimization opportunities in the injection pipeline.

    Attributes:
        session_ref: External reference for the agent session.
        prompt_index: Which prompt in the session (0-indexed).
        routing_ms: Time spent on agent routing decision.
        retrieval_ms: Time spent retrieving context from stores.
        injection_ms: Time spent assembling and injecting context.
        user_visible_latency_ms: Total user-perceived delay.
        cohort: Experiment cohort for A/B testing.
        cache_hit: Whether context was served from cache.
        timestamp: When the timing was recorded (timezone-aware UTC).

    Example:
        >>> payload = ModelLatencyBreakdownPayload(
        ...     session_ref="sess-123",
        ...     prompt_index=0,
        ...     routing_ms=15,
        ...     retrieval_ms=45,
        ...     injection_ms=10,
        ...     user_visible_latency_ms=120,
        ...     cohort="control",
        ...     cache_hit=True,
        ...     timestamp=datetime.now(UTC),
        ... )
    """

    session_ref: str = Field(
        ...,
        min_length=1,
        description="External reference for the agent session",
    )
    prompt_index: int = Field(
        ...,
        ge=0,
        description="Which prompt in the session (0-indexed)",
    )
    routing_ms: int = Field(
        ...,
        ge=0,
        description="Time spent on agent routing decision (milliseconds)",
    )
    retrieval_ms: int = Field(
        ...,
        ge=0,
        description="Time spent retrieving context from stores (milliseconds)",
    )
    injection_ms: int = Field(
        ...,
        ge=0,
        description="Time spent assembling and injecting context (milliseconds)",
    )
    user_visible_latency_ms: int = Field(
        ...,
        ge=0,
        description="Total user-perceived delay (milliseconds)",
    )
    cohort: str = Field(
        ...,
        min_length=1,
        description="Experiment cohort for A/B testing",
    )
    cache_hit: bool = Field(
        ...,
        description="Whether context was served from cache",
    )
    timestamp: datetime = Field(
        ...,
        description="When the timing was recorded (timezone-aware UTC)",
    )

    @field_validator("timestamp")
    @classmethod
    def check_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware."""
        if v.tzinfo is None:
            # error-ok: ValueError is standard for Pydantic field validators
            raise ValueError("timestamp must be timezone-aware (got naive datetime)")
        return v
