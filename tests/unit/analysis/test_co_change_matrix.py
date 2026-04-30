# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import pytest

from omnibase_core.analysis.co_change_matrix import build_cochange_matrix


def test_pair_counts() -> None:
    commits = [
        ["a.py", "b.py"],
        ["a.py", "b.py", "c.py"],
        ["a.py"],
    ]
    m = build_cochange_matrix(commits)
    assert m.pair_count[("a.py", "b.py")] == 2
    assert m.pair_count[("a.py", "c.py")] == 1
    assert m.file_count["a.py"] == 3
    assert m.total_commits == 3


def test_single_file_commit_no_pairs() -> None:
    commits = [["a.py"], ["b.py"]]
    m = build_cochange_matrix(commits)
    assert len(m.pair_count) == 0
    assert m.file_count["a.py"] == 1
    assert m.file_count["b.py"] == 1
    assert m.total_commits == 2


def test_empty_commits() -> None:
    m = build_cochange_matrix([])
    assert m.pair_count == {}
    assert m.file_count == {}
    assert m.total_commits == 0


def test_duplicate_files_in_commit_counted_once() -> None:
    commits = [["a.py", "a.py", "b.py"]]
    m = build_cochange_matrix(commits)
    assert m.file_count["a.py"] == 1
    assert m.pair_count[("a.py", "b.py")] == 1


def test_pairs_are_sorted_tuples() -> None:
    commits = [["z.py", "a.py"]]
    m = build_cochange_matrix(commits)
    assert ("a.py", "z.py") in m.pair_count
    assert ("z.py", "a.py") not in m.pair_count


def test_matrix_is_frozen() -> None:
    m = build_cochange_matrix([["a.py", "b.py"]])
    with pytest.raises((AttributeError, TypeError)):
        # NOTE(OMN-10361): intentional forbidden assignment to verify frozen dataclass behavior.
        m.total_commits = 99  # type: ignore[misc]
