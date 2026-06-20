# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-dialect round-trip proof tests for the Contract Graph IR (OMN-13223).

Proves that the single ``node`` adapter in
``omnibase_core.contract_graph.adapter_node_contract`` losslessly imports
a REAL contract of each of the four structural dialect variants found in
this repository, and that a no-op round-trip produces zero semantic diff
through the shipped ``cli_contract_diff`` spine.

Four dialects, four proofs (option b — single adapter, not four separate
adapters, per OMN-13223 acceptance criteria):

1. ``descriptor``  — canonical lowercase node_type + top-level topics +
   ``descriptor:`` metadata section (intentionally dropped by IR projection).
   Contract: ``node_compliance_evidence_effect/contract.yaml`` (effect).

2. ``event_bus``   — topics nested inside ``event_bus: { publish_topics: [...],
   subscribe_topics: [...] }`` instead of at the top level.
   Contract: ``node_compliance_orchestrator/contract.yaml`` (orchestrator).

3. ``state_machine`` — ``REDUCER_GENERIC`` node_type + ``state_transitions:``
   FSM section (dropped by IR projection; only the archetype role is captured).
   Contract: ``contracts/runtime/contract_registry_reducer.yaml``.

4. ``workflow_coordination`` — ``ORCHESTRATOR_GENERIC`` node_type +
   ``workflow_coordination:`` section (dropped by IR projection).
   Contract: ``contracts/runtime/runtime_orchestrator.yaml``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.contract_graph.adapter_node_contract import (
    supports_node_contract,
)
from omnibase_core.contract_graph.importer import (
    _load_yaml,
    import_paths,
    normalize_node_contract,
    round_trip_node_diff,
    round_trip_zero_diff,
)
from omnibase_core.enums.enum_contract_graph_edge_kind import EnumContractGraphEdgeKind
from omnibase_core.enums.enum_contract_graph_node_role import EnumContractGraphNodeRole
from omnibase_core.models.contract_graph.model_contract_graph_ir import (
    ModelContractGraphIr,
)
from omnibase_core.types.type_json import JsonType

_REPO_ROOT = Path(__file__).resolve().parents[3]

# --------------------------------------------------------------------------- #
# Real per-dialect contract paths
# --------------------------------------------------------------------------- #

# 1. descriptor dialect: effect node with descriptor: section + top-level topics
_DESCRIPTOR_CONTRACT = (
    "src/omnibase_core/nodes/node_compliance_evidence_effect/contract.yaml"
)

# 2. event_bus dialect: orchestrator node with event_bus: { publish_topics, subscribe_topics }
_EVENT_BUS_CONTRACT = (
    "src/omnibase_core/nodes/node_compliance_orchestrator/contract.yaml"
)

# 3. state_machine dialect: REDUCER_GENERIC + state_transitions: FSM section
_STATE_MACHINE_CONTRACT = "contracts/runtime/contract_registry_reducer.yaml"

# 4. workflow_coordination dialect: ORCHESTRATOR_GENERIC + workflow_coordination: section
_WORKFLOW_COORD_CONTRACT = "contracts/runtime/runtime_orchestrator.yaml"


# --------------------------------------------------------------------------- #
# Helper: import a single real contract into an IR
# --------------------------------------------------------------------------- #


def _import_single(
    repo_relative: str,
) -> tuple[ModelContractGraphIr, dict[str, JsonType]]:
    """Load + import one real contract; return (ir, raw_data)."""
    fs_path = _REPO_ROOT / repo_relative
    data = _load_yaml(fs_path)
    ir: ModelContractGraphIr = import_paths(
        discovery_roots=(str(Path(repo_relative).parent),),
        node_paths=((fs_path, repo_relative),),
        ui_components=(),
    )
    return ir, data


# --------------------------------------------------------------------------- #
# Dialect 1: descriptor
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_descriptor_dialect_is_supported() -> None:
    """descriptor dialect contract is detected by the node adapter."""
    data = _load_yaml(_REPO_ROOT / _DESCRIPTOR_CONTRACT)
    assert data.get("node_type") == "effect"
    assert "descriptor" in data, "descriptor section must be present"
    assert supports_node_contract(data) is True


@pytest.mark.unit
def test_descriptor_dialect_import_role_and_edges() -> None:
    """descriptor dialect contract imports to EFFECT role with correct topic edges."""
    ir, _ = _import_single(_DESCRIPTOR_CONTRACT)
    assert len(ir.nodes) == 1
    node = ir.nodes[0]
    assert node.role is EnumContractGraphNodeRole.EFFECT
    kinds = {e.kind for e in ir.edges}
    assert EnumContractGraphEdgeKind.PUBLISHES in kinds
    assert EnumContractGraphEdgeKind.SUBSCRIBES in kinds


@pytest.mark.unit
def test_descriptor_dialect_zero_diff_round_trip() -> None:
    """descriptor dialect: no-op round-trip == zero semantic diff (descriptor section dropped)."""
    ir, data = _import_single(_DESCRIPTOR_CONTRACT)
    node_id = ir.nodes[0].node_id
    result = round_trip_node_diff(ir, node_id, data)
    assert round_trip_zero_diff(result) is True, (
        f"descriptor dialect round-trip has semantic diff: {result}"
    )
    assert result.total_changes == 0


@pytest.mark.unit
def test_descriptor_dialect_deterministic_ir() -> None:
    """descriptor dialect IR is deterministic across two identical imports."""
    ir1, _ = _import_single(_DESCRIPTOR_CONTRACT)
    ir2, _ = _import_single(_DESCRIPTOR_CONTRACT)
    assert ir1.model_dump_json() == ir2.model_dump_json()


# --------------------------------------------------------------------------- #
# Dialect 2: event_bus
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_event_bus_dialect_is_supported() -> None:
    """event_bus dialect contract is detected (orchestrator with event_bus: section)."""
    data = _load_yaml(_REPO_ROOT / _EVENT_BUS_CONTRACT)
    assert data.get("node_type") == "orchestrator"
    event_bus = data.get("event_bus")
    assert isinstance(event_bus, dict), "event_bus section must be present"
    assert "publish_topics" in event_bus or "subscribe_topics" in event_bus
    assert supports_node_contract(data) is True


@pytest.mark.unit
def test_event_bus_dialect_topics_extracted_from_nested_section() -> None:
    """event_bus dialect: topics nested under event_bus: are extracted as IR edges."""
    ir, data = _import_single(_EVENT_BUS_CONTRACT)
    assert len(ir.nodes) == 1
    node = ir.nodes[0]
    assert node.role is EnumContractGraphNodeRole.ORCHESTRATOR

    # Topics must appear as edges even though they live in event_bus:, not top-level
    event_bus_raw = data.get("event_bus")
    assert isinstance(event_bus_raw, dict), "event_bus section must be a dict"
    pub_raw = event_bus_raw.get("publish_topics")
    sub_raw = event_bus_raw.get("subscribe_topics")
    expected_pub: set[str] = (
        {str(t) for t in pub_raw} if isinstance(pub_raw, list) else set()
    )
    expected_sub: set[str] = (
        {str(t) for t in sub_raw} if isinstance(sub_raw, list) else set()
    )

    actual_pub = {
        e.topic for e in ir.edges if e.kind is EnumContractGraphEdgeKind.PUBLISHES
    }
    actual_sub = {
        e.topic for e in ir.edges if e.kind is EnumContractGraphEdgeKind.SUBSCRIBES
    }

    assert expected_pub <= actual_pub, (
        f"event_bus publish topics not in IR edges: missing {expected_pub - actual_pub}"
    )
    assert expected_sub <= actual_sub, (
        f"event_bus subscribe topics not in IR edges: missing {expected_sub - actual_sub}"
    )


@pytest.mark.unit
def test_event_bus_dialect_zero_diff_round_trip() -> None:
    """event_bus dialect: no-op round-trip == zero semantic diff (topics from event_bus: survive)."""
    ir, data = _import_single(_EVENT_BUS_CONTRACT)
    node_id = ir.nodes[0].node_id
    result = round_trip_node_diff(ir, node_id, data)
    assert round_trip_zero_diff(result) is True, (
        f"event_bus dialect round-trip has semantic diff: {result}"
    )
    assert result.total_changes == 0


@pytest.mark.unit
def test_event_bus_dialect_deterministic_ir() -> None:
    """event_bus dialect IR is deterministic across two identical imports."""
    ir1, _ = _import_single(_EVENT_BUS_CONTRACT)
    ir2, _ = _import_single(_EVENT_BUS_CONTRACT)
    assert ir1.model_dump_json() == ir2.model_dump_json()


# --------------------------------------------------------------------------- #
# Dialect 3: state_machine
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_state_machine_dialect_is_supported() -> None:
    """state_machine dialect contract is detected (REDUCER_GENERIC + state_transitions:)."""
    data = _load_yaml(_REPO_ROOT / _STATE_MACHINE_CONTRACT)
    assert data.get("node_type") == "REDUCER_GENERIC"
    assert "state_transitions" in data, "state_transitions section must be present"
    assert supports_node_contract(data) is True


@pytest.mark.unit
def test_state_machine_dialect_maps_to_reducer_role() -> None:
    """state_machine dialect: REDUCER_GENERIC maps to REDUCER role in the IR."""
    ir, _ = _import_single(_STATE_MACHINE_CONTRACT)
    assert len(ir.nodes) == 1
    node = ir.nodes[0]
    assert node.role is EnumContractGraphNodeRole.REDUCER
    # node_id derived from source_path stem (no handler_id or name in this contract)
    assert node.node_id == "contract_registry_reducer"


@pytest.mark.unit
def test_state_machine_dialect_zero_diff_round_trip() -> None:
    """state_machine dialect: no-op round-trip == zero semantic diff (FSM section dropped)."""
    ir, data = _import_single(_STATE_MACHINE_CONTRACT)
    node_id = ir.nodes[0].node_id
    result = round_trip_node_diff(ir, node_id, data)
    assert round_trip_zero_diff(result) is True, (
        f"state_machine dialect round-trip has semantic diff: {result}"
    )
    assert result.total_changes == 0


@pytest.mark.unit
def test_state_machine_dialect_normalize_uses_canonical_node_type() -> None:
    """state_machine dialect: normalize_node_contract emits lowercase 'reducer' not 'REDUCER_GENERIC'."""
    data = _load_yaml(_REPO_ROOT / _STATE_MACHINE_CONTRACT)
    normalized = normalize_node_contract(data, source_path=_STATE_MACHINE_CONTRACT)
    assert normalized["node_type"] == "reducer"
    assert normalized["handler_id"] == "contract_registry_reducer"


@pytest.mark.unit
def test_state_machine_dialect_deterministic_ir() -> None:
    """state_machine dialect IR is deterministic across two identical imports."""
    ir1, _ = _import_single(_STATE_MACHINE_CONTRACT)
    ir2, _ = _import_single(_STATE_MACHINE_CONTRACT)
    assert ir1.model_dump_json() == ir2.model_dump_json()


# --------------------------------------------------------------------------- #
# Dialect 4: workflow_coordination
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_workflow_coordination_dialect_is_supported() -> None:
    """workflow_coordination dialect is detected (ORCHESTRATOR_GENERIC + workflow_coordination:)."""
    data = _load_yaml(_REPO_ROOT / _WORKFLOW_COORD_CONTRACT)
    assert data.get("node_type") == "ORCHESTRATOR_GENERIC"
    assert "workflow_coordination" in data, (
        "workflow_coordination section must be present"
    )
    assert supports_node_contract(data) is True


@pytest.mark.unit
def test_workflow_coordination_dialect_maps_to_orchestrator_role() -> None:
    """workflow_coordination dialect: ORCHESTRATOR_GENERIC maps to ORCHESTRATOR role."""
    ir, _ = _import_single(_WORKFLOW_COORD_CONTRACT)
    assert len(ir.nodes) == 1
    node = ir.nodes[0]
    assert node.role is EnumContractGraphNodeRole.ORCHESTRATOR
    assert node.node_id == "runtime_orchestrator"


@pytest.mark.unit
def test_workflow_coordination_dialect_zero_diff_round_trip() -> None:
    """workflow_coordination dialect: no-op round-trip == zero semantic diff (wf section dropped)."""
    ir, data = _import_single(_WORKFLOW_COORD_CONTRACT)
    node_id = ir.nodes[0].node_id
    result = round_trip_node_diff(ir, node_id, data)
    assert round_trip_zero_diff(result) is True, (
        f"workflow_coordination dialect round-trip has semantic diff: {result}"
    )
    assert result.total_changes == 0


@pytest.mark.unit
def test_workflow_coordination_dialect_normalize_uses_canonical_node_type() -> None:
    """workflow_coordination dialect: normalize_node_contract emits 'orchestrator' not 'ORCHESTRATOR_GENERIC'."""
    data = _load_yaml(_REPO_ROOT / _WORKFLOW_COORD_CONTRACT)
    normalized = normalize_node_contract(data, source_path=_WORKFLOW_COORD_CONTRACT)
    assert normalized["node_type"] == "orchestrator"
    assert normalized["handler_id"] == "runtime_orchestrator"


@pytest.mark.unit
def test_workflow_coordination_dialect_deterministic_ir() -> None:
    """workflow_coordination dialect IR is deterministic across two identical imports."""
    ir1, _ = _import_single(_WORKFLOW_COORD_CONTRACT)
    ir2, _ = _import_single(_WORKFLOW_COORD_CONTRACT)
    assert ir1.model_dump_json() == ir2.model_dump_json()


# --------------------------------------------------------------------------- #
# Cross-dialect: adapter version hash changes when implementation changes
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_all_four_dialects_share_single_adapter_version() -> None:
    """All four dialects are handled by the single 'node' adapter (single adapter_version_sha256)."""
    from omnibase_core.contract_graph.adapter_node_contract import (
        node_contract_adapter_version,
    )

    v = node_contract_adapter_version()
    assert v.startswith("sha256:"), "adapter version must be a sha256: prefixed hash"

    # All four dialect contracts imported via the same adapter share one adapter version
    for repo_relative in (
        _DESCRIPTOR_CONTRACT,
        _EVENT_BUS_CONTRACT,
        _STATE_MACHINE_CONTRACT,
        _WORKFLOW_COORD_CONTRACT,
    ):
        ir, _ = _import_single(repo_relative)
        for ref in ir.source_set.refs:
            if ref.dialect == "node":
                assert ref.adapter_version_sha256 == v, (
                    f"contract {repo_relative!r} has unexpected adapter version "
                    f"{ref.adapter_version_sha256!r} (expected {v!r})"
                )


@pytest.mark.unit
def test_all_four_dialect_source_hashes_differ() -> None:
    """Each dialect contract has a distinct source_contract_sha256."""
    hashes: dict[str, str] = {}
    for repo_relative in (
        _DESCRIPTOR_CONTRACT,
        _EVENT_BUS_CONTRACT,
        _STATE_MACHINE_CONTRACT,
        _WORKFLOW_COORD_CONTRACT,
    ):
        ir, _ = _import_single(repo_relative)
        for ref in ir.source_set.refs:
            if ref.dialect == "node":
                hashes[repo_relative] = ref.source_contract_sha256
    # All four source hashes must differ (distinct contracts)
    assert len(set(hashes.values())) == 4, (
        f"Expected 4 distinct source hashes, got {len(set(hashes.values()))}: {hashes}"
    )
