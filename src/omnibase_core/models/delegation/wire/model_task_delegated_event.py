# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Task delegated event wire DTO."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.topics import TopicBase

TASK_DELEGATED_TOPIC_V1 = TopicBase.TASK_DELEGATED


class ModelTaskDelegatedEvent(BaseModel):
    """Durable event emitted after a task is delegated to a model endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(
        default=TASK_DELEGATED_TOPIC_V1,
        description="Kafka topic this event should be routed to.",
    )
    timestamp: str = Field(..., description="ISO-8601 timestamp.")
    correlation_id: UUID = Field(..., description="Delegation correlation ID.")
    session_id: UUID | None = Field(default=None, description="Source session ID.")
    task_type: str = Field(..., description="Task classification.")
    delegated_to: str = Field(..., description="Model/endpoint that handled the task.")
    model_name: str = Field(
        default="",
        description="LLM model name from the routing decision (e.g. Qwen3-Coder-14B).",
    )
    delegated_by: str = Field(
        default="delegation-pipeline",
        description="Source of the delegation.",
    )
    quality_gate_passed: bool = Field(
        ...,
        description="Whether the quality gate accepted the response.",
    )
    quality_gates_checked: list[str] = Field(
        default_factory=lambda: ["length", "refusal", "markers"],
        description="Names of quality gates checked.",
    )
    quality_gates_failed: list[str] = Field(
        default_factory=list,
        description="Names of quality gates that failed.",
    )
    cost_usd: float = Field(
        default=0.0,
        description="Estimated cost of local LLM inference (near-zero).",
    )
    cost_savings_usd: float = Field(
        default=0.0,
        description="Estimated savings vs Claude.",
    )
    delegation_latency_ms: int = Field(
        default=0,
        description="End-to-end delegation latency in ms.",
    )
    is_shadow: bool = Field(default=False, description="Whether this was a shadow run.")
    # string-id-ok: LLM call ID is an opaque upstream string (e.g. OpenAI "chatcmpl-..." format)
    llm_call_id: str = Field(
        default="",
        description="Upstream LLM call ID for JOIN with llm_cost_aggregates.",
    )
    tokens_to_compliance: int = Field(
        default=0,
        ge=0,
        description="Total tokens across all compliance attempts.",
    )
    compliance_attempts: int = Field(
        default=1,
        ge=1,
        description="Number of LLM invocations to reach compliance.",
    )
    prompt_text: str | None = Field(
        default=None, description="Raw prompt sent to the delegated model."
    )
    response_text: str | None = Field(
        default=None,
        description="Raw response received from the delegated model.",
    )
    pricing_manifest_version: int = Field(
        default=0,
        ge=0,
        description="Version of the pricing manifest used to compute cost_savings_usd.",
    )
    escalation_count: int = Field(
        default=0,
        ge=0,
        description="Number of tier-escalation attempts that occurred.",
    )
    escalation_history: tuple[dict[str, object], ...] = Field(
        default=(),
        description="Serialized per-tier escalation attempt records.",
    )
    routing_tiers_hash: str | None = Field(
        default=None,
        description="SHA-256 of serialized routing_tiers.yaml at execution time.",
    )
    escalation_config_hash: str | None = Field(
        default=None,
        description="SHA-256 of the escalation contract section at execution time.",
    )
    attempts_count: int = Field(
        default=1,
        ge=1,
        description="Total delegation attempts including the initial attempt.",
    )
    cumulative_attempt_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Total estimated cost across all attempts.",
    )


__all__: list[str] = ["TASK_DELEGATED_TOPIC_V1", "ModelTaskDelegatedEvent"]
