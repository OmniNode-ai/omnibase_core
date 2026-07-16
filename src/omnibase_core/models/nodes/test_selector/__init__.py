# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical I/O models for the test-selector COMPUTE node (OMN-14700).

Promoted verbatim from ``scripts/ci/test_selection_models.py`` and
``scripts/ci/test_selection_loader.py`` into the canonical ``omnibase_core``
model layer (root CLAUDE.md rule #7) so the RSD-regenerated
``node_test_selector_compute`` node and the legacy ``detect_test_paths.py``
oracle share ONE definition of each shape (no fork). The two ``scripts/ci``
modules re-export these names until the CI/pre-push swap follow-up
(OMN-14700 DoD 2/3) deletes the script.

Parent epic: OMN-2362 (Generic Validator Node Architecture / WS8).
"""

from omnibase_core.models.nodes.test_selector.model_adjacency_map import (
    ModelAdjacencyEntry,
    ModelAdjacencyMap,
    ModelThresholds,
)
from omnibase_core.models.nodes.test_selector.model_test_selection import (
    EnumFullSuiteReason,
    ModelTestSelection,
    ModuleName,
    TestPath,
)
from omnibase_core.models.nodes.test_selector.model_test_selection_request import (
    ModelTestSelectionRequest,
)

__all__ = [
    "EnumFullSuiteReason",
    "ModelAdjacencyEntry",
    "ModelAdjacencyMap",
    "ModelTestSelection",
    "ModelTestSelectionRequest",
    "ModelThresholds",
    "ModuleName",
    "TestPath",
]
