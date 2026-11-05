# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One golden or error case of a node's chain scenarios (OMN-22478)."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_chain_scenario_break import EnumChainScenarioBreak
from omnibase_core.enums.enum_chain_scenario_kind import EnumChainScenarioKind
from omnibase_core.enums.enum_chain_scenario_reading import EnumChainScenarioReading
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_expected_event import (
    ModelChainScenarioExpectedEvent,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_fault import (
    ModelChainScenarioFault,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_input import (
    ModelChainScenarioInput,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_ledger_row import (
    ModelChainScenarioLedgerRow,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_oracle import (
    ModelChainScenarioOracle,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_state_update import (
    ModelChainScenarioStateUpdate,
)


class ModelChainScenarioCase(BaseModel):
    """A case: input, optional fault, independent expectations and the breaks it must survive.

    A golden case publishes the input and asserts every produced event in order under one
    correlation id, ending in the success event. An error case injects a defined fault and
    asserts the typed failure event, a ledger failure row and the reading; silence fails it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_name: str = Field(..., min_length=1)
    kind: EnumChainScenarioKind
    input: ModelChainScenarioInput
    expected_events: tuple[ModelChainScenarioExpectedEvent, ...] = Field(
        default=(), description="Every event produced after the input, in order."
    )
    state_updates: tuple[ModelChainScenarioStateUpdate, ...] = ()
    fault: ModelChainScenarioFault | None = None
    failure: str | None = Field(
        default=None,
        min_length=1,
        description="Name of the declared failure the case ends in.",
    )
    ledger_failure_row: ModelChainScenarioLedgerRow | None = None
    reading: EnumChainScenarioReading | None = None
    oracle: ModelChainScenarioOracle
    breaks: tuple[EnumChainScenarioBreak, ...] = ()

    @model_validator(mode="after")
    def _shape_follows_kind(self) -> ModelChainScenarioCase:
        error_only = (self.fault, self.failure, self.ledger_failure_row, self.reading)
        if self.kind is EnumChainScenarioKind.GOLDEN and any(
            part is not None for part in error_only
        ):
            raise ValueError(
                f"{self.case_name}: a golden case declares no fault, failure, ledger row or reading"
            )
        if self.kind is EnumChainScenarioKind.ERROR and any(
            part is None for part in error_only
        ):
            raise ValueError(
                f"{self.case_name}: an error case declares a fault, a failure, a ledger failure row and a reading"
            )
        return self

    def case_hash(self) -> str:
        """Hash that pins a mutation receipt to exactly this case."""
        canonical = json.dumps(
            self.model_dump(mode="json", exclude={"breaks"}),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["ModelChainScenarioCase"]
