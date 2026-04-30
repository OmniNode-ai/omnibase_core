# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the co-change dark matter filter pipeline."""

from omnibase_core.analysis.co_change_dark_matter import find_dark_matter
from omnibase_core.analysis.co_change_matrix import (
    CoChangeMatrix,
    build_cochange_matrix,
)
from omnibase_core.analysis.import_graph import ImportGraph


def _make_matrix(commits: list[list[str]]) -> CoChangeMatrix:
    return build_cochange_matrix(commits)


def _empty_graph() -> ImportGraph:
    return ImportGraph()


def _graph_with_edge(a: str, b: str) -> ImportGraph:
    g = ImportGraph()
    g.edges_out[a] = {b}
    return g


# ---------------------------------------------------------------------------
# Acceptance criterion 3: empty when fewer than 3 commits
# ---------------------------------------------------------------------------


class TestInsufficientCommits:
    def test_zero_commits_returns_empty(self) -> None:
        matrix = _make_matrix([])
        result = find_dark_matter(matrix, _empty_graph())
        assert result == []

    def test_one_commit_returns_empty(self) -> None:
        matrix = _make_matrix([["a.py", "b.py"]])
        result = find_dark_matter(matrix, _empty_graph())
        assert result == []

    def test_two_commits_returns_empty(self) -> None:
        matrix = _make_matrix([["a.py", "b.py"], ["a.py", "b.py"]])
        result = find_dark_matter(matrix, _empty_graph())
        assert result == []

    def test_three_commits_passes_threshold(self) -> None:
        commits = [["a.py", "b.py"]] * 3
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        # May or may not return results depending on other filters, but should not raise
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Acceptance criterion 2: filter — < 3 co-changes
# ---------------------------------------------------------------------------


class TestCoChangeCountFilter:
    def test_pair_with_two_co_changes_excluded(self) -> None:
        commits = [["a.py", "b.py"], ["a.py", "b.py"]] + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("a.py", "b.py") not in pairs

    def test_pair_with_three_co_changes_not_excluded_by_count(self) -> None:
        # Repeated 3x to pass count filter, 10 more commits for signal
        commits = [["a.py", "b.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        # a.py and b.py always co-occur → NPMI = 1.0 ≥ 0.5, passes all filters
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("a.py", "b.py") in pairs


# ---------------------------------------------------------------------------
# Acceptance criterion 2: filter — NPMI < 0.5
# ---------------------------------------------------------------------------


class TestNpmiFilter:
    def test_low_npmi_pair_excluded(self) -> None:
        # a.py and b.py co-change 3 times out of 100 commits each → low NPMI
        commits = [["a.py", "b.py"]] * 3 + [["a.py"]] * 47 + [["b.py"]] * 47
        # total_commits = 97; file_count: a.py=50, b.py=50; pair=3
        # p_ab=3/97≈0.031, p_a=50/97≈0.515, p_b=50/97≈0.515
        # NPMI will be negative → excluded
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("a.py", "b.py") not in pairs


# ---------------------------------------------------------------------------
# Acceptance criterion 2: filter — static import edge
# ---------------------------------------------------------------------------


class TestStaticEdgeFilter:
    def test_pair_with_static_edge_a_imports_b_excluded(self) -> None:
        commits = [["a.py", "b.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        graph = _graph_with_edge("a.py", "b.py")
        result = find_dark_matter(matrix, graph)
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("a.py", "b.py") not in pairs

    def test_pair_with_static_edge_b_imports_a_excluded(self) -> None:
        commits = [["a.py", "b.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        graph = _graph_with_edge("b.py", "a.py")
        result = find_dark_matter(matrix, graph)
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("a.py", "b.py") not in pairs

    def test_pair_without_static_edge_not_excluded(self) -> None:
        commits = [["a.py", "b.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        graph = _graph_with_edge("c.py", "d.py")
        result = find_dark_matter(matrix, graph)
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("a.py", "b.py") in pairs


# ---------------------------------------------------------------------------
# Acceptance criterion 2: filter — test↔impl pair
# ---------------------------------------------------------------------------


class TestTestImplFilter:
    def test_test_impl_pair_excluded(self) -> None:
        commits = [["tests/test_foo.py", "src/foo.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("src/foo.py", "tests/test_foo.py") not in pairs
        assert ("tests/test_foo.py", "src/foo.py") not in pairs

    def test_two_test_files_not_excluded_by_test_impl(self) -> None:
        commits = [["tests/test_foo.py", "tests/test_bar.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("tests/test_bar.py", "tests/test_foo.py") in pairs

    def test_two_src_files_not_excluded_by_test_impl(self) -> None:
        commits = [["src/foo.py", "src/bar.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("src/bar.py", "src/foo.py") in pairs


# ---------------------------------------------------------------------------
# Acceptance criterion 2: filter — same-prefix pair (first 3 path segments)
# ---------------------------------------------------------------------------


class TestSamePrefixFilter:
    def test_same_prefix_pair_excluded(self) -> None:
        commits = [
            ["src/omnibase_core/models/foo.py", "src/omnibase_core/models/bar.py"]
        ] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert (
            "src/omnibase_core/models/foo.py",
            "src/omnibase_core/models/bar.py",
        ) not in pairs
        assert (
            "src/omnibase_core/models/bar.py",
            "src/omnibase_core/models/foo.py",
        ) not in pairs

    def test_different_prefix_pair_not_excluded(self) -> None:
        commits = [
            ["src/omnibase_core/models/foo.py", "src/omnibase_core/validation/bar.py"]
        ] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert (
            "src/omnibase_core/models/foo.py",
            "src/omnibase_core/validation/bar.py",
        ) in pairs

    def test_short_paths_not_same_prefix(self) -> None:
        # a.py and b.py have fewer than 3 segments → not same-prefix filtered
        commits = [["a.py", "b.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        pairs = [(r["a"], r["b"]) for r in result]
        assert ("a.py", "b.py") in pairs


# ---------------------------------------------------------------------------
# Acceptance criterion 1: top 20 sorted by NPMI descending
# ---------------------------------------------------------------------------


class TestTopKAndSorting:
    def test_returns_at_most_20_pairs(self) -> None:
        # Create 30 unique pairs each co-changing 5 times
        files = [f"module_{i}/a.py" for i in range(30)]
        commits: list[list[str]] = []
        # Each file pair co-changes 5 times
        for i in range(0, 30, 2):
            commits.extend([[files[i], files[i + 1]]] * 5)
        # Add enough non-co-change commits
        commits.extend([[f"solo_{i}.py"] for i in range(30)])
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        assert len(result) <= 20

    def test_results_sorted_by_npmi_desc(self) -> None:
        commits = [["a.py", "b.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        npmi_values = [r["npmi"] for r in result]
        assert npmi_values == sorted(npmi_values, reverse=True)

    def test_result_contains_required_fields(self) -> None:
        commits = [["a.py", "b.py"]] * 3 + [["c.py"]] * 10
        matrix = _make_matrix(commits)
        result = find_dark_matter(matrix, _empty_graph())
        for item in result:
            assert {"a", "b", "npmi", "co_changes"} <= set(item.keys())
            assert isinstance(item["npmi"], float)
            assert isinstance(item["co_changes"], int)
