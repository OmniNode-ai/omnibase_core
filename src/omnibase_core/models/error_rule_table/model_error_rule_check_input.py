# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dependency-injected facts for the pure rule-table checker."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.error_rule_table.model_error_action_contract import (
    ModelErrorActionContract,
)
from omnibase_core.models.error_rule_table.model_error_rule_measurement import (
    ModelErrorRuleMeasurement,
)


class ModelErrorRuleCheckInput(BaseModel):
    """Raw rows retain malformed fields for diagnostic locations; registries are trusted inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    document: dict[str, object]
    contract: ModelValidatorSubcontract
    action_contracts: dict[str, ModelErrorActionContract] = Field(default_factory=dict)
    resolved_sources: frozenset[str] = frozenset()
    measurements: dict[str, ModelErrorRuleMeasurement] = Field(default_factory=dict)
    registered_state_checks: frozenset[str] = frozenset()
    retired_ids: frozenset[str] = frozenset()
    authorized_modes: dict[str, str] = Field(default_factory=dict)
