# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""LLM call evidence model for audit and cost tracking (OMN-10691)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.adr.enum_usage_source import EnumUsageSource


class ModelLLMCallEvidence(BaseModel):
    """Durable record of a single LLM inference call with cost and provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    model_id: str = Field(  # string-id-ok: LLM model name, not a UUID
        description="LLM model identifier"
    )
    provider: str = Field(
        description="Inference provider (e.g., vllm_local, openrouter)"
    )
    # string-id-ok: template name identifier, not a UUID
    prompt_template_id: str = Field(description="Prompt template identifier")
    prompt_template_version: str = Field(  # string-version-ok: template semver string
        description="Prompt template version"
    )
    prompt_hash: str = Field(description="SHA256 of the rendered prompt")
    input_hash: str = Field(description="SHA256 of the full input payload")
    request_timestamp: datetime = Field(
        description="UTC timestamp when request was sent"
    )
    response_hash: str = Field(description="SHA256 of the raw response body")
    raw_response_path: str | None = Field(
        default=None, description="Optional path to persisted raw response file"
    )
    usage_source: EnumUsageSource = Field(
        description="Whether token counts were measured, estimated, or unknown"
    )
    prompt_tokens: int | None = Field(default=None, description="Prompt token count")
    completion_tokens: int | None = Field(
        default=None, description="Completion token count"
    )
    total_tokens: int | None = Field(default=None, description="Total token count")
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated cost in USD"
    )
    # string-version-ok: manifest semver string
    pricing_manifest_version: str | None = Field(
        default=None, description="Version of the pricing manifest used"
    )
    error_state: str | None = Field(
        default=None, description="Error code if call failed"
    )
    success: bool = Field(description="Whether the call completed successfully")


__all__ = ["ModelLLMCallEvidence"]
