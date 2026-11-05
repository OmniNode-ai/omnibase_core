# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Input event of a contract-declared chain scenario case (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ModelChainScenarioInput(BaseModel):
    """The event a scenario publishes: its topic, its fixture and the correlation field.

    ``correlation_field`` names the payload field the runner stamps the scenario's
    one correlation id into; ``None`` means the input model carries none and the
    runtime envelope is the only carrier.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(
        ..., min_length=1, description="Subscribed topic the input is published on."
    )
    payload: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Fixture payload, stated by the scenario author.",
    )
    correlation_field: str | None = Field(
        default=None,
        min_length=1,
        description="Payload field that carries the scenario correlation id.",
    )


__all__ = ["ModelChainScenarioInput"]
