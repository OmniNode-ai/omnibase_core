# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import pytest

from omnibase_core.enums import EnumNodeArchetype, EnumNodeKind, EnumNodeType
from omnibase_core.factories import (
    get_default_compute_profile,
    get_default_effect_profile,
    get_default_orchestrator_profile,
    get_default_reducer_profile,
)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("node_type", "node_kind"),
    [
        (EnumNodeType.COMPUTE_GENERIC, EnumNodeKind.COMPUTE),
        (EnumNodeType.EFFECT_GENERIC, EnumNodeKind.EFFECT),
        (EnumNodeType.REDUCER_GENERIC, EnumNodeKind.REDUCER),
        (EnumNodeType.ORCHESTRATOR_GENERIC, EnumNodeKind.ORCHESTRATOR),
        (EnumNodeType.RUNTIME_HOST_GENERIC, EnumNodeKind.RUNTIME_HOST),
    ],
)
def test_all_five_generic_node_patterns_have_kind_mappings(
    node_type: EnumNodeType,
    node_kind: EnumNodeKind,
) -> None:
    assert EnumNodeType.has_node_kind(node_type)
    assert EnumNodeType.get_node_kind(node_type) == node_kind


@pytest.mark.integration
def test_compute_profile_is_pure_compute_contract() -> None:
    contract = get_default_compute_profile("compute_pure")

    assert contract.node_type == EnumNodeType.COMPUTE_GENERIC
    assert contract.behavior.node_archetype == EnumNodeArchetype.COMPUTE
    assert contract.behavior.purity == "pure"
    assert contract.deterministic_execution is True


@pytest.mark.integration
def test_effect_profile_is_idempotent_effect_contract() -> None:
    contract = get_default_effect_profile("effect_idempotent")

    assert contract.node_type == EnumNodeType.EFFECT_GENERIC
    assert contract.behavior.node_archetype == EnumNodeArchetype.EFFECT
    assert contract.behavior.idempotent is True
    assert contract.retry_policies.max_attempts == 3


@pytest.mark.integration
def test_reducer_profile_is_fsm_reducer_contract() -> None:
    contract = get_default_reducer_profile("reducer_fsm_basic")

    assert contract.node_type == EnumNodeType.REDUCER_GENERIC
    assert contract.behavior.node_archetype == EnumNodeArchetype.REDUCER
    assert contract.state_machine is not None
    assert contract.state_machine.initial_state == "idle"
    assert "completed" in contract.state_machine.terminal_states


@pytest.mark.integration
def test_orchestrator_profile_is_serial_orchestrator_contract() -> None:
    contract = get_default_orchestrator_profile("orchestrator_safe")

    assert contract.node_type == EnumNodeType.ORCHESTRATOR_GENERIC
    assert contract.behavior.node_archetype == EnumNodeArchetype.ORCHESTRATOR
    assert contract.workflow_coordination.execution_mode == "serial"
    assert contract.action_emission.emission_strategy == "sequential"
