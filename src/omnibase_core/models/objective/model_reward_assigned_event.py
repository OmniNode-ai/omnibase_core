# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical ModelRewardAssignedEvent — the cross-repo contract for reward signals.

Published to: ``onex.evt.omnimemory.reward-assigned.v1``

This model is the single source of truth shared between:
  - Producer: ``omnibase_infra/NodeRewardBinderEffect``
  - Consumer: ``omniintelligence/NodePolicyStateReducer``

Design (OMN-2928 — gap:164320af):
  Bridges the producer's run-level canonical score vector with the consumer's
  policy-centric signal fields. All identifier fields use UUID types for
  type safety across the wire; consumers parse UUIDs to strings where needed.

Fields:
  Run-level (producer-owned):
    event_id, run_id, evidence_refs, emitted_at,
    correctness, safety, cost, latency, maintainability, human_time

  Policy signal (consumer-owned):
    policy_id, policy_type, reward_delta,
    objective_id, idempotency_key, occurred_at_utc
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_policy_type import EnumPolicyType

__all__ = ["ModelRewardAssignedEvent"]


class ModelRewardAssignedEvent(BaseModel):
    """Canonical reward-assigned event bridging producer and consumer schemas.

    Published to: ``onex.evt.omnimemory.reward-assigned.v1``

    Run-level fields (from ModelScoreVector — producer fills these):
        correctness, safety, cost, latency, maintainability, human_time

    Policy signal fields (consumer-centric — producer derives from evaluation):
        policy_id, policy_type, reward_delta, objective_id,
        idempotency_key, occurred_at_utc

    All identifier fields are UUID for type safety; serialise via
    ``model_dump_json()`` which renders UUIDs as strings.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ------------------------------------------------------------------
    # Identifiers
    # ------------------------------------------------------------------
    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique event identifier.",
    )
    run_id: UUID = Field(
        ...,
        description="Evaluation run ID that produced this reward.",
    )

    # ------------------------------------------------------------------
    # Run-level canonical score vector fields (from ModelScoreVector)
    # ------------------------------------------------------------------
    correctness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Gate-derived correctness: 1.0 if all gates pass, 0.0 if any fail.",
    )
    safety: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Security, PII, and blacklist gate composite score.",
    )
    cost: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Inverted cost score: lower cost = higher score.",
    )
    latency: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Inverted latency score: lower latency = higher score.",
    )
    maintainability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cyclomatic complexity delta and test coverage composite score.",
    )
    human_time: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Inverted human intervention score: fewer retries/reviews = higher score.",
    )

    # ------------------------------------------------------------------
    # Evidence traceability
    # ------------------------------------------------------------------
    evidence_refs: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="ModelEvidenceItem.item_id values supporting this reward.",
    )

    # ------------------------------------------------------------------
    # Policy signal fields (consumer-centric)
    # ------------------------------------------------------------------
    policy_id: UUID = Field(
        ...,
        description=(
            "The policy entity ID receiving the reward "
            "(maps to tool_id, pattern_id, model_id, or agent_id)."
        ),
    )
    policy_type: EnumPolicyType = Field(
        ...,
        description="Which policy type this reward applies to.",
    )
    reward_delta: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description=(
            "Signed reward delta [-1.0, +1.0]. "
            "Positive = improvement, negative = degradation."
        ),
    )
    objective_id: UUID = Field(
        ...,
        description="The ObjectiveSpec ID used to compute this reward.",
    )
    idempotency_key: str = Field(
        ...,
        description=(
            "Deterministic hash of (event_id, policy_id, run_id) for idempotency. "
            "Replaying the same event must produce no double-update."
        ),
    )
    occurred_at_utc: str = Field(
        ...,
        description="ISO-8601 UTC timestamp when the reward was computed.",
    )

    # ------------------------------------------------------------------
    # Emission metadata
    # ------------------------------------------------------------------
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of event emission.",
    )
