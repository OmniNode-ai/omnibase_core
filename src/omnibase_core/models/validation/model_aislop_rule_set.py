# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAislopRuleSet — versioned collection of aislop detection rules (OMN-11132)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule


class ModelAislopRuleSet(BaseModel):
    """A versioned set of aislop rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: list[ModelAislopRule] = Field(default_factory=list)


__all__ = ["ModelAislopRuleSet"]
