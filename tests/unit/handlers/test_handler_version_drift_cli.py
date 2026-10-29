# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the version-drift CLIs over real git clones in a temp dir (OMN-19998)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.handlers import (
    handler_merge_queue_parity_cli,
)

pytestmark = pytest.mark.unit


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(cwd),
        },
    ).stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


_QUEUE_ONLY = (
    "on:\n  pull_request:\n  merge_group:\njobs:\n  j:\n"
    "    if: github.event_name == 'merge_group'\n    runs-on: x\n    steps: []\n"
)
_BASELINE = (
    "violations:\n  - path: .github/workflows/ci.yml\n    job: j\n"
    "    rule: merge_queue_only_if\n    ticket: OMN-19998\n"
)


def test_parity_cli_fails_then_warns_once_baselined(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    _commit(repo, {".github/workflows/ci.yml": _QUEUE_ONLY}, "wf")
    assert handler_merge_queue_parity_cli.main(["--root", str(repo)]) == 1
    _commit(repo, {".onex_ratchets/merge_queue_parity_baseline.yaml": _BASELINE}, "bl")
    assert handler_merge_queue_parity_cli.main(["--root", str(repo)]) == 0


def test_parity_cli_refuses_baseline_growth_against_the_base(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    base = _commit(
        repo,
        {
            ".github/workflows/ci.yml": "on: [push]\njobs: {}\n",
            ".onex_ratchets/merge_queue_parity_baseline.yaml": "violations: []\n",
        },
        "base",
    )
    _commit(
        repo,
        {
            ".github/workflows/ci.yml": _QUEUE_ONLY,
            ".onex_ratchets/merge_queue_parity_baseline.yaml": _BASELINE,
        },
        "grow",
    )
    assert (
        handler_merge_queue_parity_cli.main(
            ["--root", str(repo), "--ratchet-base-ref", base]
        )
        == 1
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".github/workflows/ci.yml", True),
        (".github/workflows/ci.yaml", True),
        (".github/workflows/.ci.yml", True),
        (".github/workflows/.yaml", False),
        (".github/workflows/ci.yaml.bak", False),
        (".github/workflows/ci.YML", False),
        (".github/workflows/nested/ci.yml", False),
        (".github/workflows//ci.yml", False),
        ("./.github/workflows/ci.yml", False),
        ("/.github/workflows/ci.yml", False),
        ("other/.github/workflows/ci.yml", False),
        (".github/workflows/ci", False),
        (".github/workflows/", False),
    ],
)
def test_parity_workflow_selection_preserves_path_boundaries(
    path: str, expected: bool
) -> None:
    assert handler_merge_queue_parity_cli.is_workflow(path) is expected


def test_parity_workflow_selection_uses_rule_parameter() -> None:
    row = handler_merge_queue_parity_cli.load_workflow_rule()
    changed = row.model_copy(
        update={"parameters": {"path_pattern": r"^custom/[^/]+\.yml$"}}
    )
    assert not handler_merge_queue_parity_cli.is_workflow(
        ".github/workflows/ci.yml", rule=changed
    )
    assert handler_merge_queue_parity_cli.is_workflow("custom/ci.yml", rule=changed)


def test_parity_workflow_selection_refuses_missing_parameter() -> None:
    from omnibase_core.errors.model_onex_error import ModelOnexError

    row = handler_merge_queue_parity_cli.load_workflow_rule()
    broken = row.model_copy(update={"parameters": {}})
    with pytest.raises(ModelOnexError):
        handler_merge_queue_parity_cli.is_workflow(
            ".github/workflows/ci.yml", rule=broken
        )
