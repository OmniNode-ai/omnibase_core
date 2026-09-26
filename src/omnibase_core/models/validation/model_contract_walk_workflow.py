# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The walk of one workflow: an owner machine plus linked reducers (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_contract_walk_component import (
    ModelContractWalkComponent,
)
from omnibase_core.models.validation.model_contract_walk_illegal_pair import (
    ModelContractWalkIllegalPair,
)
from omnibase_core.models.validation.model_contract_walk_path import (
    ModelContractWalkPath,
)
from omnibase_core.models.validation.model_contract_walk_state_ref import (
    ModelContractWalkStateRef,
)
from omnibase_core.models.validation.model_contract_walk_transition_ref import (
    ModelContractWalkTransitionRef,
)


class ModelContractWalkWorkflow(BaseModel):
    """Report for one workflow.

    The first component owns the workflow (an orchestrator, or a reducer no
    orchestrator links). A product state is terminal when the owner's state is
    terminal. Components synchronise on trigger names they share; the rest
    interleave. The cover criterion is all-edges with loop bound 1; the
    selected path count is reported next to the edge count and the cyclomatic
    number (edges - states + 1), never asserted as a property."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_owner: str = Field(description="Owner node name")
    components: tuple[ModelContractWalkComponent, ...] = Field(
        description="Owner first"
    )
    sync_triggers: tuple[str, ...] = Field(
        default=(), description="Trigger names shared by two or more components"
    )
    cover_criterion: str = Field(
        default="all-edges", description="Path cover criterion"
    )
    loop_bound: int = Field(default=1, description="Times each cycle is traversed")
    product_state_count: int = Field(description="Reachable product states")
    product_edge_count: int = Field(description="Reachable product edges")
    cyclomatic_bound: int = Field(description="Reachable edges - reachable states + 1")
    truncated: bool = Field(
        default=False, description="True when the state cap stopped the walk"
    )
    selected_path_count: int = Field(description="Paths selected by the cover")
    paths: tuple[ModelContractWalkPath, ...] = Field(
        default=(), description="Selected paths"
    )
    error_edges: tuple[ModelContractWalkTransitionRef, ...] = Field(
        default=(), description="Declared transitions into an error state that fire"
    )
    illegal_pairs: tuple[ModelContractWalkIllegalPair, ...] = Field(
        default=(), description="Events each component must reject in a reached state"
    )
    unreachable_states: tuple[ModelContractWalkStateRef, ...] = Field(
        default=(), description="Declared states no reachable product state holds"
    )
    dead_states: tuple[tuple[str, ...], ...] = Field(
        default=(), description="Reached product states with no path to a terminal"
    )
    no_golden_exit_states: tuple[tuple[str, ...], ...] = Field(
        default=(),
        description=(
            "Reached, non-terminal product states from which a terminal is reachable "
            "but only a declared error terminal"
        ),
    )
    uncovered_transitions: tuple[ModelContractWalkTransitionRef, ...] = Field(
        default=(), description="Declared transitions no reachable edge fires"
    )
