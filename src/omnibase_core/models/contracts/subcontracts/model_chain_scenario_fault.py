# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fault an error chain scenario injects (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_chain_scenario_fault_kind import (
    EnumChainScenarioFaultKind,
)


class ModelChainScenarioFault(BaseModel):
    """A defined fault: bad payload, handler error, dependency down or missed deadline.

    ``boundary`` names the binding the fault is injected through. A bare retry is
    not a defence: ``max_dependency_calls`` bounds the attempts and the typed failure
    still has to appear.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumChainScenarioFaultKind
    boundary: str | None = Field(
        default=None, min_length=1, description="Binding the fault is injected through."
    )
    deadline_ms: int | None = Field(
        default=None,
        gt=0,
        description="Deadline the typed failure must beat (MISSED_DEADLINE).",
    )
    max_dependency_calls: int = Field(
        default=1, ge=1, description="Most calls the faulty dependency may receive."
    )


__all__ = ["ModelChainScenarioFault"]
