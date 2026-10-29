# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict, typed interpretation of the generic validation subcontract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.precommit_pins.model_precommit_older_pin_parameters import (
    ModelPrecommitOlderPinParameters,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time_parameters import (
    ModelPrecommitRevTimeParameters,
)
from omnibase_core.models.precommit_pins.model_precommit_unresolved_pin_parameters import (
    ModelPrecommitUnresolvedPinParameters,
)


class ModelPrecommitPinRules(BaseModel):
    """All rule parameters must validate before a file can pass."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    older_rule: ModelValidatorRule
    unresolved_rule: ModelValidatorRule
    lookup_rule: ModelValidatorRule
    older: ModelPrecommitOlderPinParameters
    unresolved: ModelPrecommitUnresolvedPinParameters
    lookup: ModelPrecommitRevTimeParameters

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelPrecommitPinRules:
        """Reject missing/unknown rules and malformed parameters, even if disabled."""
        rows = {row.rule_id: row for row in contract.rules}
        expected = {"older_than_newest_pin", "unresolved_rev_time", "rev_time_lookup"}
        if set(rows) != expected or len(rows) != len(contract.rules):
            raise ModelOnexError(
                message="pin parity requires exactly the three declared rules",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        older, unresolved, lookup = (
            rows[key]
            for key in (
                "older_than_newest_pin",
                "unresolved_rev_time",
                "rev_time_lookup",
            )
        )
        if not lookup.enabled:
            raise ModelOnexError(
                message="rev_time_lookup must be enabled",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return cls(
            older_rule=older,
            unresolved_rule=unresolved,
            lookup_rule=lookup,
            older=ModelPrecommitOlderPinParameters.model_validate(older.parameters),
            unresolved=ModelPrecommitUnresolvedPinParameters.model_validate(
                unresolved.parameters
            ),
            lookup=ModelPrecommitRevTimeParameters.model_validate(lookup.parameters),
        )
