# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Normalized event-bus subscription parsed from a node contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEventBusSubscription(BaseModel):
    """A single normalized subscription parsed from an event_bus contract block.

    Carries only the topic. The former ``consumer_group`` field was parsed and never
    read; consumer group IDs are now derived from node identity by
    :mod:`omnibase_core.event_bus.util_consumer_group` so that every minted name is matched
    by the MSK IAM authorized pattern set (OMN-15639).
    """

    topic: str = Field(..., description="Topic suffix to subscribe to.")

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelEventBusSubscription"]
