# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of parsing an event_bus contract block into normalized subscriptions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_event_bus_subscription import (
    ModelEventBusSubscription,
)


class ModelEventBusParseResult(BaseModel):
    """Result of parsing an ``event_bus`` contract block."""

    subscriptions: list[ModelEventBusSubscription] = Field(
        default_factory=list,
        description="Normalized subscriptions from classic and nested shapes (in that order).",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelEventBusParseResult"]
