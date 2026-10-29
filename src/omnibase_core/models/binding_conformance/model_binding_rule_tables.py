# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-supplied rule settings and literal detection patterns."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_binding_rule import EnumBindingRule
from omnibase_core.models.binding_conformance.model_binding_rule_setting import (
    ModelBindingRuleSetting,
)


class ModelBindingRuleTables(BaseModel):
    """Immutable rule data consumed by the pure binding checker."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    environment_names: tuple[str, ...] = ()
    url_pattern: str = ""
    absolute_path_pattern: str = ""
    settings: tuple[ModelBindingRuleSetting, ...] = ()

    def is_enabled(self, rule: EnumBindingRule) -> bool:
        """Return whether the contract supplied a setting for this rule."""
        return any(setting.rule is rule for setting in self.settings)

    def severity_of(self, rule: EnumBindingRule) -> EnumSeverity:
        """Return the configured severity, or ERROR for an absent rule."""
        return next(
            (setting.severity for setting in self.settings if setting.rule is rule),
            EnumSeverity.ERROR,
        )
