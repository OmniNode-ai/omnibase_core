# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract Graph IR models (OMN-13132 — Phase 2, epic OMN-13129).

The canonical read-only intermediate the plan
(docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2)
calls the Contract Graph IR. Heterogeneous source contracts — backend node
contracts and UI component contracts — are imported into one deterministic graph
of nodes + typed edges, with stable hashes pinning provenance.

These models are DISTINCT from the workflow-viz graph models in
``omnibase_core.models.graph`` (``ModelGraphNode``/``ModelGraphEdge``, whose
``node_id`` is a UUID for orchestrator-graph visualization) and from the
validation-event ``ModelContractRef`` in
``omnibase_core.models.events.contract_validation``. The distinct
``contract_graph`` namespace and ``ModelContractGraph*`` names prevent any
identifier collision.
"""

from omnibase_core.models.contract_graph.model_contract_graph_contract_ref import (
    ModelContractGraphContractRef,
)
from omnibase_core.models.contract_graph.model_contract_graph_edge import (
    ModelContractGraphEdge,
)
from omnibase_core.models.contract_graph.model_contract_graph_ir import (
    ModelContractGraphIr,
)
from omnibase_core.models.contract_graph.model_contract_graph_node import (
    ModelContractGraphNode,
)
from omnibase_core.models.contract_graph.model_contract_graph_protocol import (
    ModelContractGraphProtocol,
)
from omnibase_core.models.contract_graph.model_contract_graph_source_set import (
    ModelContractGraphSourceSet,
)

__all__: tuple[str, ...] = (
    "ModelContractGraphIr",
    "ModelContractGraphNode",
    "ModelContractGraphEdge",
    "ModelContractGraphProtocol",
    "ModelContractGraphContractRef",
    "ModelContractGraphSourceSet",
)
