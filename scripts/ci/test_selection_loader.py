# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Load and validate the static module adjacency map.

Promotion bridge (OMN-14700): the ``ModelAdjacencyMap`` family now lives in
``omnibase_core.models.nodes.test_selector.model_adjacency_map`` (the canonical
model layer) so the ``node_test_selector_compute`` node and this legacy
``detect_test_paths.py`` oracle validate against ONE model (no fork). The models
are re-exported here; only ``load_adjacency_map`` (the YAML filesystem read — the
caller-boundary I/O the node never performs) is defined locally. Deleted by the
CI + pre-push swap follow-up (OMN-14700 DoD 2/3).
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.test_selector.model_adjacency_map import (
    ModelAdjacencyEntry,
    ModelAdjacencyMap,
    ModelThresholds,
)

__all__ = [
    "ModelAdjacencyEntry",
    "ModelAdjacencyMap",
    "ModelThresholds",
    "load_adjacency_map",
]


def load_adjacency_map(path: Path) -> ModelAdjacencyMap:
    # ModelAdjacencyMap.from_yaml_text FAILS on a duplicate mapping key (OMN-14897)
    # instead of silently keeping the last occurrence — a fail-open shape in the
    # selector's own config. The YAML filesystem read stays here at the caller
    # boundary; the parse+validate is the one canonical model method.
    return ModelAdjacencyMap.from_yaml_text(path.read_text(encoding="utf-8"))
