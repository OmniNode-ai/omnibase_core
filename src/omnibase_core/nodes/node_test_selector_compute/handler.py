# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeTestSelectorCompute — change-aware test-selection COMPUTE handler.

RSD-regenerates the governed impacted-test selector
(``scripts/ci/detect_test_paths.py``, OMN-13973) into a canonical COMPUTE node
on the def-B ``handle(request) -> response`` shape (root CLAUDE.md rule #7a),
following the OMN-14659 WS8 convert-clean template
(``node_no_env_fallbacks_check_compute``).

Architecture: COMPUTE node — pure, deterministic, no I/O. Every fact the
selection depends on (the changed-file list, the parsed adjacency map, the
pyproject.toml relevance classification, and the per-path test-file counts)
arrives on :class:`ModelTestSelectionRequest`; the git-diff, YAML read,
``git show`` classification, and filesystem walk all happen at the paired
caller/EFFECT boundary (``runtime_test_selector.py``), never in this handler.
The handler core imports no event-envelope type — the runtime adapter owns that
boundary — which is the def-B canonical shape (C-core).

Output shape: the existing typed :class:`ModelTestSelection` /
:class:`EnumFullSuiteReason` (promoted to the canonical model layer under
OMN-14700, NOT forked). The pure algorithm lives in :mod:`.selector_core` and
reproduces the oracle byte-for-byte (proven by the differential test battery).

Ticket: OMN-14700 (parent epic OMN-2362 — Generic Validator Node Architecture / WS8).
"""

from __future__ import annotations

from omnibase_core.models.nodes.test_selector.model_test_selection import (
    ModelTestSelection,
)
from omnibase_core.models.nodes.test_selector.model_test_selection_request import (
    ModelTestSelectionRequest,
)
from omnibase_core.nodes.node_test_selector_compute.selector_core import (
    compute_selection,
)

__all__ = ["NodeTestSelectorCompute"]


class NodeTestSelectorCompute:
    """COMPUTE handler that resolves a change-aware test selection."""

    def handle(self, request: ModelTestSelectionRequest) -> ModelTestSelection:
        """Definition-B canonical entry-point.

        Typed request in, typed response out — pure, no I/O, no clock.
        """
        return compute_selection(
            changed_files=request.changed_files,
            adjacency=request.adjacency,
            ref_name=request.ref_name,
            event_name=request.event_name,
            feature_flag_enabled=request.feature_flag_enabled,
            pyproject_dependency_relevant=request.pyproject_dependency_relevant,
            test_file_counts=request.test_file_counts,
        )
