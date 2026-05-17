# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAislopConfig — per-repo aislop configuration (OMN-11132)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule
from omnibase_core.models.validation.model_aislop_rule_override import (
    ModelAislopRuleOverride,
)


class ModelAislopConfig(BaseModel):
    """Per-repo aislop configuration read from .onex/aislop-rules.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    overrides: list[ModelAislopRuleOverride] = Field(default_factory=list)
    custom_rules: list[ModelAislopRule] = Field(
        default_factory=list,
        description="New rules not in the default set; requires allow_new=True in the matching override",
    )

    @model_validator(mode="after")
    def _validate_no_orphan_custom_rules(self) -> ModelAislopConfig:
        """Every custom_rule must have a matching override with allow_new=True."""
        allowed_new = {o.name for o in self.overrides if o.allow_new}
        for rule in self.custom_rules:
            if rule.name not in allowed_new:
                raise ValueError(
                    f"custom_rule '{rule.name}' has no matching override with allow_new=True"
                )
        return self


__all__ = ["ModelAislopConfig"]
