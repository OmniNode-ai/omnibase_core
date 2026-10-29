# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The severity of one enabled binding conformance rule."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_binding_rule import EnumBindingRule


class ModelBindingRuleSetting(BaseModel):
    """One rule enabled by the validator contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rule: EnumBindingRule
    severity: EnumSeverity
