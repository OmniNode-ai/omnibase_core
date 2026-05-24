# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRouteResolved — emitted on successful model key resolution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRouteResolved(BaseModel):
    """Event payload for onex.evt.omnimarket.model-route-resolved.v1.

    Emitted when a logical model key is successfully resolved to a
    concrete endpoint URL and model ID.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    logical_model_key: str = Field(
        ...,
        description="The logical model key that was resolved.",
    )
    model_key: str = Field(
        ...,
        description="Registry model_id key used (may differ when CI override is active).",
    )
    endpoint_url: str = Field(
        ...,
        description="Resolved concrete endpoint base URL.",
    )
    model_id: str = Field(
        ...,
        description="Model identifier to pass to the API (e.g. HuggingFace model ID).",
    )
    protocol: str = Field(
        default="openai_compatible",
        description="Transport protocol: openai_compatible | anthropic.",
    )
    provider: str = Field(
        ...,
        description="Provider category: local | anthropic | openrouter | cloud.",
    )
    correlation_id: str = Field(
        ...,
        description="Correlation ID from the originating route request.",
    )
    was_fallback: bool = Field(
        default=False,
        description="True when primary was degraded and fallback endpoint was selected.",
    )
    context_window: int = Field(
        default=0,
        description="Context window size from the model registry.",
        ge=0,
    )


__all__: list[str] = ["ModelRouteResolved"]
