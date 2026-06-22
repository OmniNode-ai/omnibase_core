# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-side execution-graph DAG model (OMN-12835).

Typed, validated binding of an orchestrator contract's declared
``execution_graph`` block. Enforces no-duplicate-id, no-dangling-edge, and
acyclicity invariants at parse time so declared graphs are no longer silently
dropped.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.contracts.model_contract_workflow_node import (
    ModelContractWorkflowNode,
)


class ModelContractExecutionGraph(BaseModel):
    """
    Typed, validated execution-graph DAG declared by an orchestrator contract.

    Enforces structural integrity at parse time:
    - no duplicate ``node_id`` values
    - no dangling ``depends_on`` edges (every referenced id must exist)
    - acyclicity (the graph must be a DAG)
    """

    nodes: list[ModelContractWorkflowNode] = Field(
        default_factory=list,
        description="Execution graph nodes with declared dependency edges",
    )

    @model_validator(mode="after")
    def validate_graph_integrity(self) -> "ModelContractExecutionGraph":
        """Enforce no-duplicate-id, no-dangling-edge, and acyclicity invariants."""
        node_ids = [node.node_id for node in self.nodes]

        # No duplicate node ids.
        duplicates = sorted({nid for nid in node_ids if node_ids.count(nid) > 1})
        if duplicates:
            msg = f"Execution graph has duplicate node_id values: {duplicates}"
            raise ValueError(msg)

        id_set = set(node_ids)

        # No dangling edges: every depends_on target must be a declared node.
        for node in self.nodes:
            missing = [dep for dep in node.depends_on if dep not in id_set]
            if missing:
                msg = (
                    f"Execution graph node '{node.node_id}' depends on "
                    f"undeclared node_id(s): {sorted(missing)}"
                )
                raise ValueError(msg)

        # Acyclicity: Kahn's algorithm over the dependency edges.
        adjacency: dict[str, list[str]] = {nid: [] for nid in id_set}
        in_degree: dict[str, int] = dict.fromkeys(id_set, 0)
        for node in self.nodes:
            for dep in node.depends_on:
                adjacency[dep].append(node.node_id)
                in_degree[node.node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for downstream in adjacency[current]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    queue.append(downstream)

        if visited != len(id_set):
            msg = "Execution graph contains a cycle (must be a DAG)"
            raise ValueError(msg)

        return self

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
