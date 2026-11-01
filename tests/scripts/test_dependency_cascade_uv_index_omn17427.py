# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427, OMN-19998: the lock step runs once against the dev tag source.

Execute the workflow's lock step under GitHub's Bash errexit/pipefail settings
with a fake uv: one call, no index wait (the dev merge tag is a git ref that
exists before the run), uv's failure is the leg's failure, and a no-diff lock
sets SKIP.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"


def _step(name: str) -> dict[str, object]:
    with WORKFLOW_PATH.open() as handle:
        document = yaml.safe_load(handle)
    for step in document["jobs"]["open-bump-pr"]["steps"]:
        if step.get("name") == name:
            assert isinstance(step, dict)
            return step
    raise AssertionError(f"No step named {name!r}")


def _run_lock(tmp_path: Path, mode: str) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "0.1.0"\n'
    )
    (repo / "uv.lock").write_text("version = 1\n# original lock\n")
    for args in (
        ["git", "init", "-q"],
        ["git", "add", "pyproject.toml", "uv.lock"],
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Initial files",
        ],
    ):
        subprocess.run(args, cwd=repo, check=True, capture_output=True, timeout=10)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "count").write_text("0")
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        """#!/bin/bash
set -eu
count=$(cat "$UV_STATE/count")
count=$((count + 1))
printf '%s\\n' "$count" > "$UV_STATE/count"
printf '%s\\n' "$@" > "$UV_STATE/argv-$count"
echo "uv attempt $count"
if [ "$UV_MODE" = unrelated ]; then
  echo 'failed to fetch commit' >&2
  exit 2
fi
if [ "$UV_MODE" = index-lag ]; then
  printf 'Because there is no version of\\n      omnibase-core==0.47.49 and your project depends on it\\n' >&2
  exit 1
fi
if [ "$UV_MODE" != unchanged ]; then
  echo '# resolved dev tag' >> uv.lock
fi
echo 'Resolved target'
"""
    )
    fake_uv.chmod(0o755)
    run = _step("Upgrade lockfile").get("run")
    assert isinstance(run, str)
    assert "${{" not in run
    script = tmp_path / "lock.sh"
    script.write_text(run)
    return subprocess.run(
        [
            "env",
            f"PATH={bin_dir}:/usr/bin:/bin",
            f"UV_STATE={tmp_path}",
            f"UV_MODE={mode}",
            "BUMP_PACKAGE=omnibase_core",
            "PKG_HYPHEN=omnibase-core",
            "DEV_TAG=dev-20261101175705-134f715a53e5",
            f"GITHUB_ENV={tmp_path / 'github-env'}",
            "REPO_NAME=omnimemory",
            "bash",
            "--noprofile",
            "--norc",
            "-eo",
            "pipefail",
            str(script),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def _assert_one_invocation(tmp_path: Path) -> None:
    assert int((tmp_path / "count").read_text()) == 1
    argv = (tmp_path / "argv-1").read_text().splitlines()
    assert argv == [
        "lock",
        "--no-config",
        "--default-index",
        "https://pypi.org/simple",
        "--upgrade-package",
        "omnibase-core",
    ]


@pytest.mark.unit
def test_lock_step_env_carries_the_package_and_the_dev_tag() -> None:
    env = _step("Upgrade lockfile").get("env")
    assert isinstance(env, dict)
    assert env["PKG_HYPHEN"] == "${{ steps.vars.outputs.pkg_hyphen }}"
    assert env["DEV_TAG"] == "${{ steps.vars.outputs.version }}"
    assert "RESOLVED" not in env


@pytest.mark.unit
def test_lock_runs_once_without_waiting_for_the_index(tmp_path: Path) -> None:
    result = _run_lock(tmp_path, "changed")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "Resolved target" in result.stdout
    assert "CASCADE-UV-INDEX-WAIT" not in result.stdout
    _assert_one_invocation(tmp_path)
    assert (tmp_path / "github-env").read_text() == "SKIP=false\n"


@pytest.mark.unit
def test_an_index_lag_answer_is_not_retried(tmp_path: Path) -> None:
    started = time.monotonic()
    result = _run_lock(tmp_path, "index-lag")
    assert time.monotonic() - started < 8
    assert result.returncode == 1, (result.stdout, result.stderr)
    _assert_one_invocation(tmp_path)
    assert not (tmp_path / "github-env").exists()


@pytest.mark.unit
def test_unrelated_uv_failure_exits_immediately_with_its_status(tmp_path: Path) -> None:
    result = _run_lock(tmp_path, "unrelated")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "failed to fetch commit" in result.stderr
    _assert_one_invocation(tmp_path)
    assert not (tmp_path / "github-env").exists()


@pytest.mark.unit
def test_successful_lock_without_changes_sets_skip(tmp_path: Path) -> None:
    result = _run_lock(tmp_path, "unchanged")
    assert result.returncode == 0, (result.stdout, result.stderr)
    _assert_one_invocation(tmp_path)
    assert (tmp_path / "github-env").read_text() == "SKIP=true\n"
