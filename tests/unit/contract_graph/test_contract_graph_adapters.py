# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Contract Graph IR dialect adapters + importer (OMN-13132).

Covers the read-only node-contract and UI-component adapters, manifest-driven
discovery (excluding .venv/omni_worktrees/generated), stable hashing, a
deterministic-IR assertion over >=2 REAL contracts (>=1 backend node + >=1 UI
component), and a no-op round-trip == zero-semantic-diff proof through the
shipped ``cli_contract_diff`` spine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.contract_graph import (
    EXCLUDED_DISCOVERY_DIRS,
    adapter_version_sha256,
    canonical_contract_sha256,
    discover_contract_paths,
    import_paths,
    node_contract_adapter_version,
    round_trip_node_diff,
    round_trip_ui_component_diff,
    round_trip_zero_diff,
    supports_node_contract,
    supports_ui_component,
    ui_component_adapter_version,
)
from omnibase_core.contract_graph.importer import _load_yaml
from omnibase_core.enums.enum_contract_graph_edge_kind import EnumContractGraphEdgeKind
from omnibase_core.enums.enum_contract_graph_node_role import EnumContractGraphNodeRole
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.contract_graph import ModelContractGraphIr
from omnibase_core.models.dashboard.model_action_contract import ModelActionContract
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.dashboard.model_data_binding_contract import (
    ModelDataBindingContract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Two REAL backend node contracts shipped in this repo (effect + reducer).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_EFFECT_CONTRACT = (
    "src/omnibase_core/nodes/node_compliance_evidence_effect/contract.yaml"
)
_REDUCER_CONTRACT = (
    "src/omnibase_core/nodes/node_compliance_report_reducer/contract.yaml"
)


def _real_ui_component() -> ModelComponentContract:
    """A real-shape UI component contract instance (Phase-0 primitive)."""
    return ModelComponentContract(
        component_id="compliance_status_grid",
        component_kind=EnumWidgetType.STATUS_GRID,
        title="Compliance Status",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        data_bindings=(
            ModelDataBindingContract(
                binding_id="b1",
                projection_topic="onex.evt.core.compliance-report-updated.v1",
                ordering_authority_field="updated_at",
                required_fields=("status",),
            ),
        ),
        actions=(
            ModelActionContract(
                action_id="a1",
                command_topic="onex.cmd.core.compliance-rescan.v1",
                label="Rescan",
            ),
        ),
    )


def _import_real_ir() -> ModelContractGraphIr:
    effect_fs = _REPO_ROOT / _EFFECT_CONTRACT
    reducer_fs = _REPO_ROOT / _REDUCER_CONTRACT
    return import_paths(
        discovery_roots=("src/omnibase_core/nodes",),
        node_paths=(
            (effect_fs, _EFFECT_CONTRACT),
            (reducer_fs, _REDUCER_CONTRACT),
        ),
        ui_components=((_real_ui_component(), "in-memory://compliance_status_grid"),),
    )


# --------------------------------------------------------------------------- #
# Dialect detection
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_supports_node_contract_matches_real_contract() -> None:
    data = _load_yaml(_REPO_ROOT / _EFFECT_CONTRACT)
    assert supports_node_contract(data) is True
    assert supports_ui_component(data) is False


@pytest.mark.unit
def test_supports_ui_component_matches_serialized_component() -> None:
    data = _real_ui_component().model_dump(mode="json")
    assert supports_ui_component(data) is True
    assert supports_node_contract(data) is False


@pytest.mark.unit
def test_unknown_node_type_is_not_supported() -> None:
    assert supports_node_contract({"node_type": "workflow"}) is False
    assert supports_node_contract({}) is False


# --------------------------------------------------------------------------- #
# Hashing (stable, deterministic, distinct per adapter)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_canonical_hash_ignores_metadata_and_is_stable() -> None:
    a = {"name": "x", "node_type": "effect", "_metadata": {"generated_at": "t1"}}
    b = {"name": "x", "node_type": "effect", "_metadata": {"generated_at": "t2"}}
    assert canonical_contract_sha256(a) == canonical_contract_sha256(b)
    assert canonical_contract_sha256(a).startswith("sha256:")


@pytest.mark.unit
def test_canonical_hash_changes_on_semantic_change() -> None:
    a = {"name": "x", "node_type": "effect"}
    b = {"name": "y", "node_type": "effect"}
    assert canonical_contract_sha256(a) != canonical_contract_sha256(b)


@pytest.mark.unit
def test_adapter_version_hashes_distinct_and_stable() -> None:
    node_v = node_contract_adapter_version()
    ui_v = ui_component_adapter_version()
    assert node_v.startswith("sha256:") and ui_v.startswith("sha256:")
    assert node_v != ui_v
    # stable across calls
    assert node_v == node_contract_adapter_version()


@pytest.mark.unit
def test_adapter_version_helper_changes_with_implementation() -> None:
    # Different implementation source -> different version hash; same -> stable.
    assert adapter_version_sha256(
        "x", ("def f(): return 1",)
    ) != adapter_version_sha256("x", ("def f(): return 2",))
    assert adapter_version_sha256("x", ("src",)) == adapter_version_sha256(
        "x", ("src",)
    )


# --------------------------------------------------------------------------- #
# Manifest-driven discovery excludes vendored/generated surfaces
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_discovery_excludes_venv_and_worktrees(tmp_path: Path) -> None:
    (tmp_path / "good").mkdir()
    (tmp_path / "good" / "contract.yaml").write_text("name: ok\n", encoding="utf-8")
    for excluded in (".venv", "omni_worktrees", "generated"):
        d = tmp_path / excluded / "nested"
        d.mkdir(parents=True)
        (d / "contract.yaml").write_text("name: bad\n", encoding="utf-8")

    found = discover_contract_paths((tmp_path,))
    found_strs = [str(p) for p in found]
    assert any("good/contract.yaml" in s for s in found_strs)
    for excluded in (".venv", "omni_worktrees", "generated"):
        assert not any(f"/{excluded}/" in s for s in found_strs)


@pytest.mark.unit
def test_excluded_dirs_constant_covers_required_surfaces() -> None:
    assert {".venv", "omni_worktrees", "generated"} <= EXCLUDED_DISCOVERY_DIRS


# --------------------------------------------------------------------------- #
# Import produces correct roles + typed edges
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_import_assigns_roles_and_edges() -> None:
    ir = _import_real_ir()
    roles = {n.node_id: n.role for n in ir.nodes}
    # node_id is the contract handler_id (a stable semantic id), falling back to
    # name only when handler_id is absent.
    assert roles["node.compliance.evidence"] is EnumContractGraphNodeRole.EFFECT
    assert roles["node.compliance.report.reducer"] is EnumContractGraphNodeRole.REDUCER
    assert roles["compliance_status_grid"] is EnumContractGraphNodeRole.COMPONENT

    kinds = {(e.source_node_id, e.kind) for e in ir.edges}
    assert ("node.compliance.evidence", EnumContractGraphEdgeKind.PUBLISHES) in kinds
    assert ("node.compliance.evidence", EnumContractGraphEdgeKind.SUBSCRIBES) in kinds
    assert ("compliance_status_grid", EnumContractGraphEdgeKind.ACTION_EMITS) in kinds
    assert ("compliance_status_grid", EnumContractGraphEdgeKind.DATA_BINDS) in kinds


@pytest.mark.unit
def test_import_embeds_per_source_and_adapter_hashes() -> None:
    ir = _import_real_ir()
    # one ref per source; each carries source + adapter hashes
    assert len(ir.source_set.refs) == 3
    for ref in ir.source_set.refs:
        assert ref.source_contract_sha256.startswith("sha256:")
        assert ref.adapter_version_sha256.startswith("sha256:")
    # node-dialect and ui-dialect adapter versions differ within the IR
    dialect_versions = {
        ref.dialect: ref.adapter_version_sha256 for ref in ir.source_set.refs
    }
    assert dialect_versions["node"] != dialect_versions["ui_component"]


# --------------------------------------------------------------------------- #
# Deterministic IR over >=2 REAL contracts (>=1 node + >=1 UI component)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_deterministic_ir_across_two_runs() -> None:
    ir1 = _import_real_ir()
    ir2 = _import_real_ir()
    assert ir1.model_dump_json() == ir2.model_dump_json()
    # at least one backend node contract + one UI component contract present
    roles = {n.role for n in ir1.nodes}
    assert EnumContractGraphNodeRole.COMPONENT in roles
    assert {EnumContractGraphNodeRole.EFFECT, EnumContractGraphNodeRole.REDUCER} & roles


# --------------------------------------------------------------------------- #
# No-op round-trip == zero semantic diff (through cli_contract_diff)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_node_no_op_round_trip_zero_semantic_diff() -> None:
    ir = _import_real_ir()
    src = _load_yaml(_REPO_ROOT / _EFFECT_CONTRACT)
    result = round_trip_node_diff(ir, src["handler_id"], src)
    assert round_trip_zero_diff(result) is True
    assert result.total_changes == 0


@pytest.mark.unit
def test_reducer_no_op_round_trip_zero_semantic_diff() -> None:
    ir = _import_real_ir()
    src = _load_yaml(_REPO_ROOT / _REDUCER_CONTRACT)
    result = round_trip_node_diff(ir, src["handler_id"], src)
    assert round_trip_zero_diff(result) is True
    assert result.total_changes == 0


@pytest.mark.unit
def test_ui_component_no_op_round_trip_zero_semantic_diff() -> None:
    ir = _import_real_ir()
    result = round_trip_ui_component_diff(ir, _real_ui_component())
    assert round_trip_zero_diff(result) is True
    assert result.total_changes == 0
