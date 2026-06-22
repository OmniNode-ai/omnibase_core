# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-side execution-graph node model (OMN-12835).

A single node in a contract-declared execution graph (DAG), mirroring the
``execution_graph.nodes[]`` entries declared in orchestrator contracts.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWorkflowNode(BaseModel):
    """
    A single node in a contract-declared execution graph (DAG).

    Mirrors the ``execution_graph.nodes[]`` entries declared in orchestrator
    contracts. Extra contract fields (``description``, ``step_config``) are
    tolerated via ``extra="ignore"`` so the typed binding does not force every
    declaring contract to be exhaustively modeled here — only the structural
    DAG fields (``node_id``, ``node_type``, ``depends_on``) are load-bearing.
    """

    node_id: str = Field(
        description="Unique identifier for this workflow node within the graph",
    )

    node_type: str = Field(
        description="Node archetype classification (e.g. EFFECT_GENERIC, ORCHESTRATOR_INTERNAL)",
    )

    depends_on: list[str] = Field(
        default_factory=list,
        description="node_id values this node depends on (incoming DAG edges)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
