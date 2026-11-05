# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A named typed failure a node declares for its chain scenarios (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ModelChainScenarioFailureEvent(BaseModel):
    """A named failure and the typed event that reports it.

    ``discriminators`` are the payload fields that tell this failure from a success
    when both travel on one topic; a failure that shares the success topic must
    declare at least one.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ..., min_length=1, description="Failure name an error case answers to."
    )
    topic: str = Field(
        ..., min_length=1, description="Topic the typed failure is published on."
    )
    discriminators: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Payload fields that make an event on this topic this failure.",
    )


__all__ = ["ModelChainScenarioFailureEvent"]
