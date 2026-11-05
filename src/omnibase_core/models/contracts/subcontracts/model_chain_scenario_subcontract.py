# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed chain scenario subcontract of a node contract (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.contracts.subcontracts.model_chain_scenario_binding import (
    ModelChainScenarioBinding,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_case import (
    ModelChainScenarioCase,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_failure_event import (
    ModelChainScenarioFailureEvent,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_refusal import (
    ModelChainScenarioRefusal,
)


class ModelChainScenarioSubcontract(BaseModel):
    """What a node's golden and error chain tests are generated from.

    ``success_topic`` is the success terminal; ``failures`` are the named typed failures.
    Every success terminal needs a golden case and every failure an error case, or a
    refusal that says why.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = Field(..., ge=1)
    success_topic: str = Field(..., min_length=1)
    failures: tuple[ModelChainScenarioFailureEvent, ...] = ()
    bindings: tuple[ModelChainScenarioBinding, ...] = ()
    cases: tuple[ModelChainScenarioCase, ...] = ()
    refusals: tuple[ModelChainScenarioRefusal, ...] = ()

    @model_validator(mode="after")
    def _names_resolve(self) -> ModelChainScenarioSubcontract:
        case_names = [case.case_name for case in self.cases]
        if len(set(case_names)) != len(case_names):
            raise ValueError("case_name values must be unique within a node")
        failure_names = {failure.name for failure in self.failures}
        binding_names = {binding.name for binding in self.bindings}
        for case in self.cases:
            if case.failure is not None and case.failure not in failure_names:
                raise ValueError(
                    f"{case.case_name}: failure {case.failure!r} is not declared"
                )
            if case.fault is not None and case.fault.boundary not in (
                None,
                *binding_names,
            ):
                raise ValueError(
                    f"{case.case_name}: fault boundary {case.fault.boundary!r} is not a binding"
                )
            for update in case.state_updates:
                if update.binding not in binding_names:
                    raise ValueError(
                        f"{case.case_name}: state update binding {update.binding!r} is not a binding"
                    )
        for failure in self.failures:
            if failure.topic == self.success_topic and not failure.discriminators:
                raise ValueError(
                    f"failure {failure.name!r} shares the success topic and declares no discriminators"
                )
        return self


__all__ = ["ModelChainScenarioSubcontract"]
