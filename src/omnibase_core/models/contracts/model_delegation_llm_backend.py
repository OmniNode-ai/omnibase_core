# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""LLM backend contract model for delegation runtime configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDelegationLlmBackend(BaseModel):
    """LLM backend configuration for delegation task routing."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    bifrost_endpoint_ref: str = Field(
        ...,
        description="Env var reference for the bifrost/LLM endpoint URL",
    )
    default_task_model_ref: str = Field(
        ...,
        description="Default model identifier for task classification",
    )
    max_tokens_default: int = Field(
        ..., ge=1, description="Default max tokens per request"
    )
    max_tokens_hard_limit: int = Field(
        ..., ge=1, description="Hard cap on tokens; cannot exceed"
    )
    timeout_ms: int = Field(..., ge=1000, description="Request timeout in milliseconds")
    task_model_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Per-task-type model override map",
    )
