# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent match event payload.

Tracks agent routing accuracy with graded scoring.

Topic Constant:
    See omnibase_core.constants.constants_topic_taxonomy:
    - TOPIC_INJECTION_AGENT_MATCH

Thread Safety:
    Model is frozen (immutable) and thread-safe for concurrent access.

Related:
    OMN-1889: Emitter implementation in omniclaude
    OMN-1890: Consumer implementation in omnibase_infra
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["ModelAgentMatchPayload"]


class ModelAgentMatchPayload(ModelEventPayloadBase):
    """Track agent routing accuracy with graded scoring.

    Measures how well the routing system selected the appropriate agent
    for a given request, supporting analysis of routing effectiveness.

    Attributes:
        session_ref: External reference for the agent session.
        requested_agent: Agent explicitly requested by user (None if auto-routed).
        routed_agent: Agent actually selected by the routing system.
        match_score: Confidence/quality of the match (0.0-1.0).
        routing_path: How the routing decision was made.
        timestamp: When the routing decision occurred (timezone-aware UTC).

    Example:
        >>> payload = ModelAgentMatchPayload(
        ...     session_ref="sess-123",
        ...     requested_agent=None,
        ...     routed_agent="code-reviewer",
        ...     match_score=0.95,
        ...     routing_path="direct",
        ...     timestamp=datetime.now(UTC),
        ... )
    """

    session_ref: str = Field(
        ...,
        min_length=1,
        description="External reference for the agent session",
    )
    requested_agent: str | None = Field(
        default=None,
        description="Agent explicitly requested by user (None if auto-routed)",
    )
    routed_agent: str = Field(
        ...,
        min_length=1,
        description="Agent actually selected by the routing system",
    )
    match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence/quality of the match (0.0-1.0)",
    )
    routing_path: Literal["direct", "fallback", "override"] = Field(
        ...,
        description="How the routing decision was made",
    )
    timestamp: datetime = Field(
        ...,
        description="When the routing decision occurred (timezone-aware UTC)",
    )

    @field_validator("timestamp")
    @classmethod
    def check_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware."""
        if v.tzinfo is None:
            # error-ok: ValueError is standard for Pydantic field validators
            raise ValueError("timestamp must be timezone-aware (got naive datetime)")
        return v
