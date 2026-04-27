# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Normalized event-bus subscription parsed from a node contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEventBusSubscription(BaseModel):
    """A single normalized subscription parsed from an event_bus contract block."""

    topic: str = Field(..., description="Topic suffix to subscribe to.")
    consumer_group: str | None = Field(
        default=None,
        description="Optional consumer group; only present in the nested shape.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelEventBusSubscription"]
