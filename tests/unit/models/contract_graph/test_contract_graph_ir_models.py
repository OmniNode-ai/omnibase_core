# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Contract Graph IR models (OMN-13132 — Phase 2).

Covers the six frozen Pydantic IR primitives plus the role/kind enums: frozen
immutability, ``extra="forbid"``, required fields, strong typing, and the
mandated role (``renderer``) + edge kinds (``component_renders`` /
``action_emits`` / ``data_binds``). Also asserts the namespace + class names are
distinct from the workflow-viz graph models (no collision).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums import (
    EnumContractGraphEdgeKind,
    EnumContractGraphNodeRole,
)
from omnibase_core.models.contract_graph import (
    ModelContractGraphContractRef,
    ModelContractGraphEdge,
    ModelContractGraphIr,
    ModelContractGraphNode,
    ModelContractGraphProtocol,
    ModelContractGraphSourceSet,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _ref() -> ModelContractGraphContractRef:
    return ModelContractGraphContractRef(
        ref_id="n1",
        source_path="src/x/contract.yaml",
        dialect="node",
        source_contract_sha256="sha256:" + "a" * 64,
        adapter_version_sha256="sha256:" + "b" * 64,
    )


def _node(node_id: str = "n1") -> ModelContractGraphNode:
    return ModelContractGraphNode(
        node_id=node_id,
        role=EnumContractGraphNodeRole.EFFECT,
        title="X",
        source_ref=_ref(),
    )


def _edge() -> ModelContractGraphEdge:
    return ModelContractGraphEdge(
        edge_id="e1",
        source_node_id="n1",
        target_node_id="onex.evt.core.x.v1",
        kind=EnumContractGraphEdgeKind.PUBLISHES,
        topic="onex.evt.core.x.v1",
    )


def _source_set() -> ModelContractGraphSourceSet:
    return ModelContractGraphSourceSet(
        discovery_roots=("src/x",),
        refs=(_ref(),),
    )


# --------------------------------------------------------------------------- #
# Enum requirements (plan-mandated)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_node_role_includes_renderer() -> None:
    values = {r.value for r in EnumContractGraphNodeRole}
    assert "renderer" in values
    assert {
        "effect",
        "compute",
        "reducer",
        "orchestrator",
        "component",
        "protocol",
    } <= values


@pytest.mark.unit
def test_edge_kind_includes_ui_kinds() -> None:
    values = {k.value for k in EnumContractGraphEdgeKind}
    assert {"component_renders", "action_emits", "data_binds"} <= values


# --------------------------------------------------------------------------- #
# Frozen + extra=forbid + required fields per model
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_contract_ref_frozen_and_forbid() -> None:
    ref = _ref()
    with pytest.raises(ValidationError):
        ref.dialect = "ui_component"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelContractGraphContractRef(
            ref_id="n1",
            source_path="p",
            dialect="node",
            source_contract_sha256="sha256:" + "a" * 64,
            adapter_version_sha256="sha256:" + "b" * 64,
            unknown="x",  # type: ignore[call-arg]
        )


@pytest.mark.unit
def test_contract_ref_requires_min_length_hashes() -> None:
    with pytest.raises(ValidationError):
        ModelContractGraphContractRef(
            ref_id="n1",
            source_path="p",
            dialect="node",
            source_contract_sha256="x",
            adapter_version_sha256="sha256:" + "b" * 64,
        )


@pytest.mark.unit
def test_protocol_frozen_forbid_optional_models() -> None:
    proto = ModelContractGraphProtocol(
        protocol_id="p1",
        qualified_name="pkg.ProtocolX",
    )
    assert proto.input_model is None and proto.output_model is None
    with pytest.raises(ValidationError):
        proto.qualified_name = "y"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelContractGraphProtocol(protocol_id="p1", qualified_name="x", bad=1)  # type: ignore[call-arg]


@pytest.mark.unit
def test_node_strong_typing_role_enum() -> None:
    node = _node()
    assert node.role is EnumContractGraphNodeRole.EFFECT
    with pytest.raises(ValidationError):
        ModelContractGraphNode(
            node_id="n1",
            role="not-a-role",  # type: ignore[arg-type]
            title="X",
            source_ref=_ref(),
        )


@pytest.mark.unit
def test_node_frozen_and_forbid() -> None:
    node = _node()
    with pytest.raises(ValidationError):
        node.title = "Y"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelContractGraphNode(
            node_id="n1",
            role=EnumContractGraphNodeRole.EFFECT,
            title="X",
            source_ref=_ref(),
            extra="x",  # type: ignore[call-arg]
        )


@pytest.mark.unit
def test_node_requires_source_ref() -> None:
    with pytest.raises(ValidationError):
        ModelContractGraphNode(  # type: ignore[call-arg]
            node_id="n1",
            role=EnumContractGraphNodeRole.EFFECT,
            title="X",
        )


@pytest.mark.unit
def test_edge_strong_typing_kind_enum() -> None:
    edge = _edge()
    assert edge.kind is EnumContractGraphEdgeKind.PUBLISHES
    with pytest.raises(ValidationError):
        ModelContractGraphEdge(
            edge_id="e1",
            source_node_id="n1",
            target_node_id="t",
            kind="bogus",  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_edge_topic_optional_and_frozen() -> None:
    edge = ModelContractGraphEdge(
        edge_id="e2",
        source_node_id="n1",
        target_node_id="proto",
        kind=EnumContractGraphEdgeKind.IMPLEMENTS_PROTOCOL,
    )
    assert edge.topic is None
    with pytest.raises(ValidationError):
        edge.topic = "x"  # type: ignore[misc]


@pytest.mark.unit
def test_source_set_requires_roots_and_frozen() -> None:
    ss = _source_set()
    assert ss.discovery_roots == ("src/x",)
    with pytest.raises(ValidationError):
        ModelContractGraphSourceSet(discovery_roots=(), refs=(_ref(),))
    with pytest.raises(ValidationError):
        ss.refs = ()  # type: ignore[misc]


@pytest.mark.unit
def test_ir_root_strong_typing_and_frozen() -> None:
    ir = ModelContractGraphIr(
        ir_version=ModelSemVer(major=0, minor=1, patch=0),
        nodes=(_node(),),
        edges=(_edge(),),
        source_set=_source_set(),
    )
    assert isinstance(ir.ir_version, ModelSemVer)
    assert ir.nodes[0].node_id == "n1"
    with pytest.raises(ValidationError):
        ir.nodes = ()  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelContractGraphIr(
            ir_version=ModelSemVer(major=0, minor=1, patch=0),
            nodes=(_node(),),
            source_set=_source_set(),
            junk=1,  # type: ignore[call-arg]
        )


@pytest.mark.unit
def test_ir_version_must_be_semver_not_str() -> None:
    with pytest.raises(ValidationError):
        ModelContractGraphIr(
            ir_version="0.1.0",  # type: ignore[arg-type]
            nodes=(_node(),),
            source_set=_source_set(),
        )


@pytest.mark.unit
def test_distinct_from_workflow_viz_graph_models() -> None:
    """The IR node is a different class than the workflow-viz ModelGraphNode.

    The workflow-viz node keys on a UUID node_id; the IR node keys on a stable
    semantic string. Importing both must not collide.
    """
    from omnibase_core.models.graph.model_graph_node import (
        ModelGraphNode as WorkflowVizGraphNode,
    )

    assert ModelContractGraphNode is not WorkflowVizGraphNode
    assert ModelContractGraphNode.__module__ != WorkflowVizGraphNode.__module__
    # IR node_id is a plain str field (semantic), not UUID
    assert _node().node_id == "n1"
