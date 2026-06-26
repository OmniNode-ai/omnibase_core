# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation result wire DTO."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelDelegationResult(BaseModel):
    """Delegation outcome: content, quality status, model info, and metrics."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ...,
        description="Tracks this result back to the original request.",
    )
    task_type: str = Field(
        ..., description="The task classification from the original request."
    )
    model_used: str = Field(
        ...,
        description="Name of the LLM model that produced the response.",
    )
    endpoint_url: str = Field(..., description="URL of the LLM endpoint used.")
    content: str = Field(..., description="The LLM-generated response content.")
    quality_passed: bool = Field(
        ...,
        description="Whether the quality gate accepted the response.",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality score from 0.0 to 1.0.",
    )
    latency_ms: int = Field(
        ..., ge=0, description="End-to-end latency in milliseconds."
    )
    prompt_tokens: int = Field(
        default=0, ge=0, description="Number of tokens in the prompt."
    )
    completion_tokens: int = Field(
        default=0, ge=0, description="Number of tokens in the completion."
    )
    total_tokens: int = Field(
        default=0, ge=0, description="Total tokens used (prompt + completion)."
    )
    fallback_to_claude: bool = Field(
        ...,
        description="Whether fallback to Claude was triggered.",
    )
    failure_reason: str = Field(
        default="",
        description="Reason for failure, empty string if successful.",
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
    escalation_count: int = Field(
        default=0,
        ge=0,
        description="Number of tier-escalation attempts that occurred.",
    )
    escalation_history: tuple[dict[str, object], ...] = Field(
        default=(),
        description="Serialized per-tier escalation attempt records.",
    )
    terminal_failure_reason: str | None = Field(
        default=None,
        description="Terminal failure reason when delegation fails after escalation.",
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
    cumulative_input_tokens: int = Field(
        default=0,
        ge=0,
        description="Total input tokens across all attempts.",
    )
    cumulative_output_tokens: int = Field(
        default=0,
        ge=0,
        description="Total output tokens across all attempts.",
    )
    final_attempt_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated cost of the final attempt.",
    )
    context_pack_hash: str = Field(
        default="",
        description=(
            "Stable sha256 hash of the context pack injected into the delegated "
            "prompt, propagated onto the terminal result for ROI correlation. "
            "Empty string means the OFF arm or no context pack."
        ),
    )

    @model_validator(mode="after")
    def validate_total_tokens(self) -> Self:
        """Keep token accounting internally consistent at the wire boundary."""
        expected_total = self.prompt_tokens + self.completion_tokens
        if self.total_tokens != expected_total:
            msg = "total_tokens must equal prompt_tokens + completion_tokens"
            raise ValueError(msg)
        return self


__all__: list[str] = ["ModelDelegationResult"]
