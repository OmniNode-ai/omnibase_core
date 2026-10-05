# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Isolated Git repositories shared by the release-identity parity tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / "tests/fixtures/validator_parity/release_identity"
SCRIPT = REPO / "scripts/check_release_identity.py"


def cases() -> list[dict[str, object]]:
    return list(yaml.safe_load((CORPUS / "cases.yaml").read_text())["cases"])


def git(root: Path, *args: str) -> str:
    scrubbed_git_env = scrub_git_location_env()
    return subprocess.run(
        ["git", *args],
        cwd=root,
        env=scrubbed_git_env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", "fixture")


def checkout(root: Path, case: dict[str, object]) -> Path:
    root.mkdir(parents=True)
    (root / "scripts").mkdir()
    shutil.copy2(CORPUS / str(case["name"]) / "pyproject.toml", root / "pyproject.toml")
    (root / "src").mkdir()
    (root / "src/example.py").write_text("initial = True\n")
    (root / "docs").mkdir()
    (root / "docs/example.md").write_text("initial\n")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "parity")
    git(root, "config", "user.email", "parity@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "core.hooksPath", "/dev/null")
    commit(root)
    tags = case.get("tags", [])
    assert isinstance(tags, list)
    for tag in tags:
        git(root, "tag", str(tag))
    git(root, "branch", "base")
    topology = case.get("topology")
    if topology in ("peer", "peer_only", "stale_base"):
        git(root, "checkout", "-qb", "peer")
        (root / "src/example.py").write_text("peer = True\n")
        commit(root)
        if topology == "stale_base":
            git(root, "branch", "-f", "base", "HEAD")
        else:
            git(root, "tag", "v9.0.0")
        git(root, "checkout", "-q", "main")
    if topology in ("pending_staged", "pending_unstaged", "docs_commit"):
        (root / "docs/example.md").write_text("branch delta\n")
        commit(root)
        if topology != "docs_commit":
            (root / "src/example.py").write_text("pending = True\n")
            if topology == "pending_staged":
                git(root, "add", "src/example.py")
    if topology == "shallow":
        (root / "docs/example.md").write_text("second\n")
        commit(root)
        clone = root.with_name(root.name + "-shallow")
        git(root, "clone", "-q", "--depth", "1", root.as_uri(), str(clone))
        for tag in tags:
            git(clone, "tag", str(tag))
        root = clone
    if topology == "bundle":
        git(root, "config", "remote.origin.url", "fixture.bundle")
    if topology == "quoted_path":
        special = root / "src" / "spaces and\nnewlines.py"
        special.write_text("changed = True\n")
        git(root, "add", str(special))
    if topology == "disconnected_base":
        git(root, "checkout", "--orphan", "unrelated")
        git(root, "commit", "--allow-empty", "-qm", "unrelated")
        git(root, "branch", "-f", "base", "HEAD")
        git(root, "checkout", "-q", "main")
    return root.resolve()


def argv(case: dict[str, object]) -> list[str]:
    args = case.get("args", [])
    assert isinstance(args, list)
    return [str(arg) for arg in args]


def oracle(root: Path, case: dict[str, object]) -> subprocess.CompletedProcess[str]:
    (root / "scripts").mkdir(exist_ok=True)
    shutil.copy2(SCRIPT, root / "scripts/check_release_identity.py")
    scrubbed_git_env = scrub_git_location_env()
    return subprocess.run(
        [sys.executable, str(root / "scripts/check_release_identity.py"), *argv(case)],
        cwd=root,
        env=scrubbed_git_env,
        capture_output=True,
        text=True,
        input=str(case.get("stdin", "")),
        check=False,
    )


def rows(stderr: str, root: Path) -> list[dict[str, str | int]]:
    lines = stderr.splitlines()
    if not lines:
        return []
    return [
        {
            "path": "pyproject.toml",
            "line": 1,
            "message": lines[0].replace(str(root), "<root>"),
        }
    ]


def report_rows(report_json: str, root: Path) -> list[dict[str, str | int]]:
    from omnibase_core.models.validation.model_validation_report import (
        ModelValidationReport,
    )

    report = ModelValidationReport.model_validate_json(report_json)
    result: list[dict[str, str | int]] = []
    for finding in report.findings:
        location = finding.location or f"{root / 'pyproject.toml'}:1"
        path, line = location.rsplit(":", 1)
        result.append(
            {
                "path": str(Path(path).relative_to(root)),
                "line": int(line),
                "message": finding.message.replace(str(root), "<root>"),
            }
        )
    return result
