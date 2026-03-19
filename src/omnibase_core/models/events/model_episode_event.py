# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Episode boundary event model for RL training (OMN-5559).

Defines the (state, action, reward) episode structure used by the
Learned Decision Optimization Platform. Episodes are emitted as
append-only Kafka events and materialized into the ``rl_episodes``
read-model table via omnidash projections.

Two-phase lifecycle:
    1. ``phase="started"`` — captures the pre-action observation
       (decision_snapshot, observation_timestamp, action_taken).
    2. ``phase="completed"`` — attaches outcome_metrics and
       terminal_status after execution finishes.

Topic: ``onex.evt.omniintelligence.episode-boundary.v1``
Partition key: ``episode_id``
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# JSON-safe value type for schemaless fields (decision snapshots, actions,
# outcome metrics). These vary by surface and are stored as JSONB in the
# read-model, so a recursive JSON type is the correct representation.
_JsonPrimitive = str | int | float | bool | None
_JsonValue = _JsonPrimitive | list[object] | dict[str, object]
EpisodePayload = dict[str, _JsonValue]

__all__ = [
    "EpisodePayload",
    "ModelEpisodeEvent",
    "TOPIC_EPISODE_BOUNDARY",
]

TOPIC_EPISODE_BOUNDARY = "onex.evt.omniintelligence.episode-boundary.v1"


class ModelEpisodeEvent(BaseModel):
    """Episode boundary event for RL training data collection.

    Each episode captures a single decision cycle: observation, action,
    and outcome. The ``decision_snapshot`` must contain ONLY pre-action
    state to prevent outcome leakage into the observation.

    Attributes:
        episode_id: Deduplication key. Same UUID across start and complete
            events for the same episode.
        surface: Decision surface that produced this episode.
        phase: Whether this is the start or completion of the episode.
        terminal_status: Final outcome status. None for ``started`` events;
            required for ``completed`` events.
        decision_snapshot: Pre-action observation state ONLY. Must not
            contain any outcome data.
        observation_timestamp: When the observation was frozen (decision
            time, not processing time).
        action_taken: The selected action (e.g. model choice, routing
            decision, team composition).
        outcome_metrics: Post-execution metrics. Populated only on
            ``completed`` events.
        emitted_at: When this event was emitted.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    episode_id: UUID = Field(
        default_factory=uuid4,
        description="Deduplication key for this episode.",
    )
    surface: Literal["routing", "pipeline", "team"] = Field(
        ...,
        description="Decision surface that produced this episode.",
    )
    phase: Literal["started", "completed"] = Field(
        ...,
        description="Episode lifecycle phase.",
    )
    terminal_status: Literal["success", "failure", "incomplete", "timeout"] | None = (
        Field(
            default=None,
            description=(
                "Final outcome status. None for started events; "
                "required for completed events."
            ),
        )
    )
    decision_snapshot: EpisodePayload = Field(
        default_factory=dict,
        description="Pre-action observation state ONLY (no outcome leakage).",
    )
    observation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the observation was frozen (decision time).",
    )
    action_taken: EpisodePayload = Field(
        default_factory=dict,
        description="The selected action.",
    )
    outcome_metrics: EpisodePayload = Field(
        default_factory=dict,
        description=(
            "Post-execution metrics: latency_ms, success, token_count, "
            "cost_usd, retries, fallback_used."
        ),
    )
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this event was emitted.",
    )
