# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Isolated base and feature commits for producer-removal tests."""

import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit
MANIFEST = ".github/required-checks.yaml"
WORKFLOW = ".github/workflows/producer.yml"
CONTEXT = "C"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "--allow-empty", "-qm", "fixture")


def manifest(root: Path, rows: list[dict[str, object]]) -> None:
    (root / MANIFEST).write_text(yaml.safe_dump({"gates": rows}), encoding="utf-8")


def row(**changes: object) -> dict[str, object]:
    return {
        "name": CONTEXT,
        "mode": "REQUIRED",
        "workflow": "producer.yml",
        "job_path": ["produce"],
        **changes,
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".github/workflows").mkdir(parents=True)
    manifest(root, [row()])
    (root / WORKFLOW).write_text("jobs:\n  produce: {}\n", encoding="utf-8")
    (root / ".github/workflows/control.yaml").write_text(
        "jobs:\n  control: {}\n", encoding="utf-8"
    )
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "producer-test")
    git(root, "config", "user.email", "producer@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "core.hooksPath", "/dev/null")
    commit(root)
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(root, "checkout", "-qb", "feature")
    commit(root)
    return root
