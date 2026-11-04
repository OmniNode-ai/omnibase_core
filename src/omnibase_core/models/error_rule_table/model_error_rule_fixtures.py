# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay record identifiers for both sides of a rule."""

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorRuleFixtures(BaseModel):
    """Every rule has a positive and a negative record."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    positive: tuple[str, ...] = Field(min_length=1)
    negative: tuple[str, ...] = Field(min_length=1)
