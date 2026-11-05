# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One event a chain scenario expects the node to produce (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ModelChainScenarioExpectedEvent(BaseModel):
    """An expected produced event: topic in order, and the payload fields it must carry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(..., min_length=1)
    fields: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Payload fields the event must carry, with the value the author states.",
    )


__all__ = ["ModelChainScenarioExpectedEvent"]
