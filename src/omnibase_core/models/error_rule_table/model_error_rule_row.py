# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Error-rule row schema; policy and cross-row predicates live in the checker."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.error_rule_table.model_error_rule_action import (
    ModelErrorRuleAction,
)
from omnibase_core.models.error_rule_table.model_error_rule_conditions import (
    ModelErrorRuleConditions,
)
from omnibase_core.models.error_rule_table.model_error_rule_fixtures import (
    ModelErrorRuleFixtures,
)
from omnibase_core.models.error_rule_table.model_error_rule_measurement import (
    ModelErrorRuleMeasurement,
)
from omnibase_core.models.error_rule_table.model_error_rule_read_back import (
    ModelErrorRuleReadBack,
)
from omnibase_core.models.error_rule_table.model_error_rule_trigger import (
    ModelErrorRuleTrigger,
)


class ModelErrorRuleRow(BaseModel):
    """One stable rule id and the exact versioned normalizer keys it covers."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str = Field(min_length=1)
    class_keys: tuple[str, ...] = Field(min_length=1)
    key_version: int = Field(gt=0, strict=True)
    trigger: ModelErrorRuleTrigger
    break_class: str
    sources: tuple[str, ...] = ()
    source_state: str | None = None
    applies_if: ModelErrorRuleConditions
    action: ModelErrorRuleAction
    read_back: ModelErrorRuleReadBack | None = None
    subject_kind: str
    budget: int = Field(gt=0, strict=True)
    lease_s: int = Field(gt=0, strict=True)
    lane_kinds: tuple[str, ...] = Field(min_length=1)
    mode: str
    fixtures: ModelErrorRuleFixtures
    measured: ModelErrorRuleMeasurement | None = None
    removal_ticket: str = Field(min_length=1)
