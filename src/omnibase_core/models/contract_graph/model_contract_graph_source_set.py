# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ContractGraphSourceSet — the deterministic set of imported source contracts.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

The source set records *exactly* which source contracts were imported into an
IR, in deterministic order, each with its hashed reference. Embedding the
source set (alongside per-node refs) in the IR output makes the provenance of a
graph explicit and reproducible: two imports over the same discovery roots
produce an identical source set.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contract_graph.model_contract_graph_contract_ref import (
    ModelContractGraphContractRef,
)

__all__ = ["ModelContractGraphSourceSet"]


class ModelContractGraphSourceSet(BaseModel):
    """The ordered, hashed set of source contracts imported into an IR.

    ``refs`` is sorted deterministically by ``source_path`` at construction time
    by the importing adapter so the set is reproducible. ``discovery_roots``
    records the repo-relative roots scanned (for evidence); discovery excludes
    ``.venv``, ``omni_worktrees``, and generated surfaces.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    discovery_roots: tuple[str, ...] = Field(
        ...,
        description="Repo-relative roots scanned for source contracts",
        min_length=1,
    )
    refs: tuple[ModelContractGraphContractRef, ...] = Field(
        ...,
        description="Deterministically ordered hashed references to imported source contracts",
    )
