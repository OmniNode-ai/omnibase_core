# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Event bus readiness status model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEventBusReadiness(BaseModel):
    """Structured readiness status for an event bus instance."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    is_ready: bool = Field(
        ...,
        description="Overall readiness: True only when all required topics are ready.",
    )
    consumers_started: bool = Field(
        ...,
        description="Whether the event bus has been started and consumers are running.",
    )
    assignments: dict[str, list[int]] = Field(  # dict-str-any-ok: partition map
        default_factory=dict,
        description="Current partition assignments per topic.",
    )
    consume_tasks_alive: dict[str, bool] = Field(  # dict-str-any-ok: task status map
        default_factory=dict,
        description="Whether the consume loop task is alive per topic.",
    )
    required_topics: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Topics marked as required_for_readiness at subscribe time.",
    )
    required_topics_ready: bool = Field(
        ...,
        description="Whether all required topics have active partition assignments.",
    )
    last_error: str = Field(
        default="",
        description="Last error encountered during readiness evaluation.",
    )


__all__: list[str] = ["ModelEventBusReadiness"]
