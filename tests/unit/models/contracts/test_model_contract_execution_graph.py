# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for the typed contract-side execution-graph DAG binding (OMN-12835).

Before OMN-12835, orchestrator contracts could declare a
``workflow_coordination.workflow_definition.execution_graph`` block but the
typed contract model (``ModelWorkflowConfig``) had no field for it, so the
declared graph was silently dropped on parse. These tests prove the graph is
now typed-bound and traversable, and that the DAG integrity validators
(no-duplicate-id, no-dangling-edge, acyclicity) are enforced.

The fixture mirrors the canonical node_intelligence_orchestrator contract:
5 nodes / 4 edges
(receive_request -> route_operation -> execute_compute -> execute_effects ->
publish_outcome).
"""

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.contracts.model_contract_execution_graph import (
    ModelContractExecutionGraph,
)
from omnibase_core.models.contracts.model_contract_workflow_definition import (
    ModelContractWorkflowDefinition,
)
from omnibase_core.models.contracts.model_workflow_config import ModelWorkflowConfig

# Mirrors node_intelligence_orchestrator/contract.yaml workflow_coordination block.
INTELLIGENCE_ORCHESTRATOR_WORKFLOW_YAML = """
workflow_definition:
  workflow_metadata:
    workflow_name: "intelligence_workflow"
    workflow_version:
      major: 1
      minor: 0
      patch: 0
    description: "Routes intelligence operations to appropriate compute/effect nodes"
  execution_graph:
    nodes:
      - node_id: "receive_request"
        node_type: EFFECT_GENERIC
        description: "Receive intelligence operation request"
        step_config:
          event_pattern: ["intelligence.*"]
      - node_id: "route_operation"
        node_type: ORCHESTRATOR_INTERNAL
        description: "Route operation based on EnumIntelligenceOperationType"
        depends_on: ["receive_request"]
        step_config:
          routing_field: "operation_type"
      - node_id: "execute_compute"
        node_type: ORCHESTRATOR_INTERNAL
        description: "Dispatch to appropriate compute node based on operation routing"
        depends_on: ["route_operation"]
      - node_id: "execute_effects"
        node_type: EFFECT_GENERIC
        description: "Execute effect nodes for persistence"
        depends_on: ["execute_compute"]
      - node_id: "publish_outcome"
        node_type: EFFECT_GENERIC
        description: "Publish workflow outcome event"
        depends_on: ["execute_effects"]
  coordination_rules:
    execution_mode: parallel
    parallel_execution_allowed: true
    max_parallel_branches: 5
"""


@pytest.mark.unit
def test_intelligence_orchestrator_execution_graph_is_typed_bound() -> None:
    """The declared execution_graph parses into typed nodes (5 nodes / 4 edges)."""
    raw = yaml.safe_load(INTELLIGENCE_ORCHESTRATOR_WORKFLOW_YAML)
    config = ModelWorkflowConfig.model_validate(raw)

    assert config.workflow_definition is not None
    graph = config.workflow_definition.execution_graph

    # 5 nodes — no silent drop.
    assert len(graph.nodes) == 5
    assert [n.node_id for n in graph.nodes] == [
        "receive_request",
        "route_operation",
        "execute_compute",
        "execute_effects",
        "publish_outcome",
    ]

    # 4 edges across the chain.
    total_edges = sum(len(n.depends_on) for n in graph.nodes)
    assert total_edges == 4

    # Edges are traversable / correctly wired.
    by_id = {n.node_id: n for n in graph.nodes}
    assert by_id["receive_request"].depends_on == []
    assert by_id["route_operation"].depends_on == ["receive_request"]
    assert by_id["execute_compute"].depends_on == ["route_operation"]
    assert by_id["execute_effects"].depends_on == ["execute_compute"]
    assert by_id["publish_outcome"].depends_on == ["execute_effects"]

    # Metadata bound too.
    assert (
        config.workflow_definition.workflow_metadata.workflow_name
        == "intelligence_workflow"
    )


@pytest.mark.unit
def test_non_declaring_workflow_config_unaffected() -> None:
    """A workflow config without a workflow_definition stays None (no regression)."""
    config = ModelWorkflowConfig(execution_mode="sequential")
    assert config.workflow_definition is None


@pytest.mark.unit
def test_workflow_node_extra_fields_ignored() -> None:
    """Contract-extra fields (description, step_config) are tolerated."""
    graph = ModelContractExecutionGraph.model_validate(
        {
            "nodes": [
                {
                    "node_id": "a",
                    "node_type": "EFFECT_GENERIC",
                    "description": "ignored",
                    "step_config": {"k": "v"},
                },
            ]
        }
    )
    assert graph.nodes[0].node_id == "a"
    assert graph.nodes[0].depends_on == []


@pytest.mark.unit
def test_duplicate_node_id_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate node_id"):
        ModelContractExecutionGraph.model_validate(
            {
                "nodes": [
                    {"node_id": "a", "node_type": "EFFECT_GENERIC"},
                    {"node_id": "a", "node_type": "COMPUTE_GENERIC"},
                ]
            }
        )


@pytest.mark.unit
def test_dangling_edge_rejected() -> None:
    with pytest.raises(ValidationError, match="undeclared node_id"):
        ModelContractExecutionGraph.model_validate(
            {
                "nodes": [
                    {
                        "node_id": "a",
                        "node_type": "EFFECT_GENERIC",
                        "depends_on": ["does_not_exist"],
                    },
                ]
            }
        )


@pytest.mark.unit
def test_cycle_rejected() -> None:
    with pytest.raises(ValidationError, match="cycle"):
        ModelContractExecutionGraph.model_validate(
            {
                "nodes": [
                    {
                        "node_id": "a",
                        "node_type": "COMPUTE_GENERIC",
                        "depends_on": ["b"],
                    },
                    {
                        "node_id": "b",
                        "node_type": "COMPUTE_GENERIC",
                        "depends_on": ["a"],
                    },
                ]
            }
        )


@pytest.mark.unit
def test_workflow_node_is_frozen() -> None:
    definition = ModelContractWorkflowDefinition.model_validate(
        {
            "workflow_metadata": {"workflow_name": "w"},
            "execution_graph": {
                "nodes": [{"node_id": "a", "node_type": "EFFECT_GENERIC"}]
            },
        }
    )
    node = definition.execution_graph.nodes[0]
    with pytest.raises(ValidationError):
        node.node_id = "mutated"
