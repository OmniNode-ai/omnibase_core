# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Filter pipeline for co-change dark matter detection.

Dark matter pairs: files that co-change frequently but have no static import
relationship — hidden coupling that is architecturally significant precisely
because it cannot be explained by the import graph.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.analysis.co_change_matrix import CoChangeMatrix, compute_npmi
from omnibase_core.analysis.import_graph import ImportGraph
from omnibase_core.types.typed_dict_dark_matter_pair import TypedDictDarkMatterPair

_MIN_CO_CHANGES = 3
_MIN_NPMI = 0.5
_TOP_K = 20
_MIN_COMMITS = 3


def find_dark_matter(
    matrix: CoChangeMatrix,
    import_graph: ImportGraph,
) -> list[TypedDictDarkMatterPair]:
    """Return the top 20 co-change pairs that are not explained by the import graph.

    Returns an empty list when the matrix has fewer than _MIN_COMMITS commits
    (insufficient statistical signal).
    """
    if matrix.total_commits < _MIN_COMMITS:
        return []

    total = matrix.total_commits
    candidates: list[TypedDictDarkMatterPair] = []

    for (a, b), co_count in matrix.pair_count.items():
        if co_count < _MIN_CO_CHANGES:
            continue

        p_a = matrix.file_count.get(a, 0) / total
        p_b = matrix.file_count.get(b, 0) / total
        p_ab = co_count / total

        # p_ab == 1.0 means every commit contains both files → NPMI = 1.0 by definition;
        # compute_npmi divides by -log(p_ab) which is 0 at p_ab=1, so handle here.
        if p_ab >= 1.0:
            npmi = 1.0
        else:
            npmi = compute_npmi(p_a, p_b, p_ab)
        if npmi < _MIN_NPMI:
            continue

        if _has_static_edge(a, b, import_graph):
            continue

        if _is_test_impl_pair(a, b):
            continue

        if _same_prefix(a, b):
            continue

        candidates.append(
            TypedDictDarkMatterPair(a=a, b=b, npmi=npmi, co_changes=co_count)
        )

    candidates.sort(key=lambda p: p["npmi"], reverse=True)
    return candidates[:_TOP_K]


def _has_static_edge(a: str, b: str, graph: ImportGraph) -> bool:
    """True if there is a static import edge in either direction."""
    a_edges = graph.edges_out.get(a, set())
    b_edges = graph.edges_out.get(b, set())
    return b in a_edges or a in b_edges


def _is_test_impl_pair(a: str, b: str) -> bool:
    """True if exactly one of the two paths lives under a test directory."""
    a_is_test = _is_test_path(a)
    b_is_test = _is_test_path(b)
    return a_is_test != b_is_test


def _is_test_path(path: str) -> bool:
    parts = Path(path).parts
    return any(p in ("tests", "test") for p in parts)


def _same_prefix(a: str, b: str, segments: int = 3) -> bool:
    """True if the first `segments` path components are identical."""
    a_parts = Path(a).parts
    b_parts = Path(b).parts
    if len(a_parts) < segments or len(b_parts) < segments:
        return False
    return a_parts[:segments] == b_parts[:segments]
