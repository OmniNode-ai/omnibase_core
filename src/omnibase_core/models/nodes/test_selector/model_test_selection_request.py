# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Input contract for the test-selector COMPUTE node (OMN-14700).

The node is pure/deterministic/no-I/O: every fact it needs is carried on this
request. The three I/O-derived inputs are resolved at the caller/EFFECT
boundary (``runtime_test_selector.py``), never inside the handler:

* ``changed_files`` — the git-diff file list (a ``git diff`` at the boundary).
* ``adjacency`` — the parsed ``test_selection_adjacency.yaml`` (a YAML read).
* ``pyproject_dependency_relevant`` — the content-aware pyproject.toml
  classification (a base-vs-head ``git show`` + TOML parse).
* ``test_file_counts`` — recursive ``test_*.py`` counts per candidate selected
  path (a filesystem walk). The node sums the counts of the paths it selects to
  compute the volume-aware split count; an absent path counts as ``0``, exactly
  mirroring the oracle's ``_count_test_files`` skip-if-missing behaviour.
* ``closure_selected_files`` — the file-grain import-graph-closure selection
  (OMN-14921), computed via
  ``scripts.ci.test_selection_closure.compute_closure_selection`` (grimp graph
  build + test-file AST reads). ``None`` fails closed to the whole-tree
  fallback — see ``selector_core.compute_selection``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.test_selector.model_adjacency_map import (
    ModelAdjacencyMap,
)

__all__ = ["ModelTestSelectionRequest"]


class ModelTestSelectionRequest(BaseModel):
    """Typed, side-effect-free request for a change-aware test selection."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ref_name: str
    adjacency: ModelAdjacencyMap
    changed_files: list[str] = Field(default_factory=list)
    event_name: str = "pull_request"
    feature_flag_enabled: bool = True
    pyproject_dependency_relevant: bool | None = None
    test_file_counts: dict[str, int] = Field(default_factory=dict)
    closure_selected_files: list[str] | None = None
