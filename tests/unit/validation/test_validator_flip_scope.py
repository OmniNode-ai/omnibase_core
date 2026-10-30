# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Historical baseline loading preserves ordering and fail-closed scope results."""

from pathlib import Path

import pytest

from omnibase_core.validation import validator_flip_scope as scope

pytestmark = pytest.mark.unit


def test_load_baseline_keeps_recorded_order_and_absent_means_empty(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.py"
    assert scope.load_baseline(path) == []
    path.write_text('NON_CANONICAL = ("z.node", "a.node")\n', encoding="utf-8")
    assert scope.load_baseline(path) == ["z.node", "a.node"]
    path.write_text("NON_CANONICAL: tuple[str, ...] = ()\n", encoding="utf-8")
    assert scope.load_baseline(path) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, []),
        ('NON_CANONICAL = ("a.node",)\n', ["a.node"]),
        ("not valid python!", None),
        ("NON_CANONICAL = dangerous()\n", None),
    ],
)
def test_base_baseline_is_parsed_without_executing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str | None,
    expected: list[str] | None,
) -> None:
    monkeypatch.setattr(scope, "_git_repo_root", lambda path: tmp_path)
    monkeypatch.setattr(scope, "_git_ref_exists", lambda root, ref: True)
    monkeypatch.setattr(scope, "_git_show", lambda root, ref, path: source)
    assert scope.load_base_baseline(tmp_path / "baseline.py", "base") == expected


@pytest.mark.parametrize("repo_exists", [False, True])
def test_unknown_git_base_is_distinct_from_an_absent_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repo_exists: bool
) -> None:
    monkeypatch.setattr(
        scope, "_git_repo_root", lambda path: tmp_path if repo_exists else None
    )
    monkeypatch.setattr(scope, "_git_ref_exists", lambda root, ref: False)
    assert scope.load_base_baseline(tmp_path / "baseline.py", "unknown") is None
