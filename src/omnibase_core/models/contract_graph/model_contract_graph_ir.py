# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ContractGraphIr — the root of the Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

DISTINCT from the workflow-viz graph models (``models/graph/``) and the
validation-event contract-ref. This is the canonical intermediate the plan
calls ``ModelGraphIR``: a deterministic, read-only graph of imported contracts
(backend node contracts + UI component contracts) plus the source set and
hashes that pin its provenance. A no-op round-trip of this IR back to canonical
normalized contract form must yield zero semantic diff (verified through
``cli_contract_diff``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contract_graph.model_contract_graph_edge import (
    ModelContractGraphEdge,
)
from omnibase_core.models.contract_graph.model_contract_graph_node import (
    ModelContractGraphNode,
)
from omnibase_core.models.contract_graph.model_contract_graph_source_set import (
    ModelContractGraphSourceSet,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelContractGraphIr"]


class ModelContractGraphIr(BaseModel):
    """The deterministic, read-only Contract Graph intermediate.

    ``nodes`` and ``edges`` are stored in deterministic order (by id) by the
    importing adapter. ``source_set`` pins which source contracts were imported
    with their stable hashes. ``ir_version`` versions the IR schema itself
    (additive/versioned). The IR is frozen and carries no I/O or mutation: it is
    a pure projection of source contracts that round-trips to canonical
    normalized contract form with zero semantic diff.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ir_version: ModelSemVer = Field(
        ...,
        description="Semantic version of the Contract Graph IR schema",
    )
    nodes: tuple[ModelContractGraphNode, ...] = Field(
        ...,
        description="IR nodes (deterministically ordered by node_id)",
    )
    edges: tuple[ModelContractGraphEdge, ...] = Field(
        default=(),
        description="Typed IR edges (deterministically ordered by edge_id)",
    )
    source_set: ModelContractGraphSourceSet = Field(
        ...,
        description="Hashed, ordered set of source contracts imported into this IR",
    )
