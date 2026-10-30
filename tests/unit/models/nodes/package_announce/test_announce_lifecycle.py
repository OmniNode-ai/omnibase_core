# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The announce lifecycle loads through ModelFSMSubcontract (OMN-21589, A1 AC9)."""

from pathlib import Path

import pytest
import yaml

import omnibase_core
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.nodes.fsm_mermaid_render.model_fsm_mermaid_diagram import (
    ModelFsmMermaidDiagram,
)
from omnibase_core.utils.util_fsm_executor import execute_transition
from omnibase_core.validation.validator_fsm_analysis import analyze_fsm

LIFECYCLE = (
    Path(omnibase_core.__file__).parent
    / "contracts"
    / "node_announce"
    / "node_announce_lifecycle.yaml"
)

# The plan's announce-lifecycle diagram (section 3.11.9), which was itself generated
# from this block; the renderer must reproduce it byte for byte.
PLAN_DIAGRAM = """\
stateDiagram-v2
    [*] --> package_found
    package_found --> contract_read: contract_file_read
    contract_read --> announce_refused: contract_invalid
    contract_read --> hashed: content_hash_computed
    hashed --> announced: announcement_published
    announced --> acknowledged: catalog_acknowledged
    announced --> hashed: acknowledgement_timeout
    announced --> announce_refused: catalog_refused
    acknowledged --> hashed: package_version_changed
    acknowledged --> withdrawn: package_removed
    withdrawn --> [*]
"""


def load_lifecycle() -> ModelFSMSubcontract:
    raw = yaml.safe_load(LIFECYCLE.read_text(encoding="utf-8"))
    return ModelFSMSubcontract.model_validate(raw["state_transitions"])


def assert_every_state_reachable(fsm: ModelFSMSubcontract) -> None:
    """Fail when a declared state is unreachable, or the initial state has an inbound edge."""
    unreachable = analyze_fsm(fsm).unreachable_states
    assert not unreachable, f"unreachable states: {unreachable}"
    inbound = [
        t.transition_name for t in fsm.transitions if t.to_state == fsm.initial_state
    ]
    assert not inbound, f"the initial state has inbound edges: {inbound}"


@pytest.mark.unit
def test_the_lifecycle_loads_through_the_fsm_subcontract_model() -> None:
    fsm = load_lifecycle()
    assert fsm.initial_state == "package_found"
    assert [s.state_name for s in fsm.states] == [
        "package_found",
        "contract_read",
        "hashed",
        "announced",
        "acknowledged",
        "announce_refused",
        "withdrawn",
    ]


@pytest.mark.unit
def test_every_declared_state_is_reachable_from_the_initial_state() -> None:
    assert_every_state_reachable(load_lifecycle())


@pytest.mark.unit
def test_planted_unreachable_state_is_caught() -> None:
    """Planted violation: a state no transition leads to must fail the check."""
    fsm = load_lifecycle()
    orphan = fsm.states[0].model_copy(
        update={
            "state_name": "planted_orphan",
            "description": "no transition reaches me",
        }
    )
    planted = ModelFSMSubcontract.model_validate(
        fsm.model_dump(mode="json") | {"states": [*fsm.states, orphan]}
    )
    with pytest.raises(AssertionError, match="planted_orphan"):
        assert_every_state_reachable(planted)


@pytest.mark.unit
def test_planted_inbound_edge_to_the_initial_state_is_caught() -> None:
    fsm = load_lifecycle()
    loop_back = fsm.transitions[0].model_copy(
        update={
            "transition_name": "planted_loop_back",
            "from_state": "hashed",
            "to_state": fsm.initial_state,
            "trigger": "planted",
        }
    )
    planted = ModelFSMSubcontract.model_validate(
        fsm.model_dump(mode="json") | {"transitions": [*fsm.transitions, loop_back]}
    )
    with pytest.raises(AssertionError, match="initial state has inbound edges"):
        assert_every_state_reachable(planted)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_every_transition_fires_through_the_real_executor() -> None:
    fsm = load_lifecycle()
    for transition in fsm.transitions:
        result = await execute_transition(
            fsm, transition.from_state, transition.trigger, {}
        )
        assert result.success, transition.transition_name
        assert result.new_state == transition.to_state, transition.transition_name


@pytest.mark.unit
def test_the_acknowledgement_timeout_transition_allows_three_retries() -> None:
    retry = next(
        t
        for t in load_lifecycle().transitions
        if t.trigger == "acknowledgement_timeout"
    )
    assert retry.retry_enabled and retry.max_retries == 3


@pytest.mark.unit
def test_the_diagram_is_generated_from_the_contract_and_matches_the_plan() -> None:
    assert ModelFsmMermaidDiagram.from_machine(load_lifecycle()).text == PLAN_DIAGRAM


@pytest.mark.unit
def test_a_changed_transition_changes_the_diagram() -> None:
    fsm = load_lifecycle()
    edited = ModelFSMSubcontract.model_validate(
        fsm.model_dump(mode="json")
        | {
            "transitions": [
                t.model_dump(mode="json")
                | (
                    {"trigger": "renamed_trigger"}
                    if t.trigger == "package_removed"
                    else {}
                )
                for t in fsm.transitions
            ]
        }
    )
    text = ModelFsmMermaidDiagram.from_machine(edited).text
    assert "acknowledged --> withdrawn: renamed_trigger" in text
    assert text != PLAN_DIAGRAM
