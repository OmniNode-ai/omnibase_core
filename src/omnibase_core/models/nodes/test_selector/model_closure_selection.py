# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Result model for the file-grain import-graph-closure selector (OMN-14206).

Moved verbatim from ``scripts/ci/test_selection_closure.py`` so the closure
primitive can ship in the ``omnibase_core`` wheel and be consumed by other
repositories (omnibase_infra, omnimarket) without a copy.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelClosureSelection"]


class ModelClosureSelection(BaseModel):
    """Governing file-grain closure selection for one selector run.

    Computed over every configured candidate root (``tests/unit/`` by default),
    because the promoted selector has no module-grain candidate ceiling to
    shrink within (OMN-14921 promotion: the module-grain map is retired).

    ``fail_closed=True`` means the caller MUST NOT narrow: ``selected_files``
    is then the conservative whole-tree sentinel — the configured candidate
    roots themselves (``["tests/unit/"]`` by default) — never a
    partial/best-effort list.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_files: list[str] = Field(default_factory=list)
    fail_closed: bool = False
    fail_closed_reasons: list[str] = Field(default_factory=list)
    candidate_file_count: int = 0
    impacted_module_count: int = 0
    elapsed_seconds: float = 0.0
