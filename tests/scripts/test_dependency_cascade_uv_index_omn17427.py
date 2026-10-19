# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427: isolate provenance checks and wait on uv's exact-version answer.

Execute the workflow's lock step under GitHub's Bash errexit/pipefail settings
with a fake uv, including wrapped index errors, unrelated failures and no diffs.
"""

from __future__ import annotations

import re
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


def _run_lock(
    tmp_path: Path, mode: str, *, total_s: int = 5
) -> subprocess.CompletedProcess[str]:
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
printf '%s\n' "$count" > "$UV_STATE/count"
printf '%s\n' "$@" > "$UV_STATE/argv-$count"
echo "uv attempt $count"
if [ "$UV_MODE" = unrelated ]; then
  echo 'failed to fetch commit' >&2
  exit 2
fi
if [ "$UV_MODE" = never ] || { [ "$UV_MODE" = delayed ] && [ "$count" -le 2 ]; }; then
  printf 'Because there is no version of\n      omnibase-core==0.47.49 and your project depends on it\n' >&2
  exit 1
fi
if [ "$UV_MODE" != unchanged ]; then
  echo '# resolved 0.47.49' >> uv.lock
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
            "RESOLVED=0.47.49",
            "CASCADE_WAIT_INTERVAL_S=1",
            f"CASCADE_WAIT_TOTAL_S={total_s}",
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


def _assert_invocations(tmp_path: Path, count: int) -> None:
    assert int((tmp_path / "count").read_text()) == count
    for attempt in range(1, count + 1):
        argv = (tmp_path / f"argv-{attempt}").read_text().splitlines()
        assert argv == [
            "lock",
            "--no-config",
            "--default-index",
            "https://pypi.org/simple",
            "--upgrade-package",
            "omnibase_core==0.47.49",
            "--refresh-package",
            "omnibase_core",
        ]


@pytest.mark.unit
def test_movable_check_runs_outside_the_downstream_project() -> None:
    run = _step("Check dependency is movable").get("run")
    assert isinstance(run, str)
    assert "uv run --no-project --with packaging python" in run
    assert "uv run python" not in run


@pytest.mark.unit
def test_wrapped_uv_index_errors_retry_until_exact_release_resolves(
    tmp_path: Path,
) -> None:
    env = _step("Upgrade lockfile").get("env")
    assert isinstance(env, dict)
    assert env["PKG_HYPHEN"] == "${{ steps.vars.outputs.pkg_hyphen }}"
    assert env["RESOLVED"] == "${{ steps.vars.outputs.version }}"
    result = _run_lock(tmp_path, "delayed")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (
        "CASCADE-UV-INDEX-WAIT-OK package=omnibase-core version=0.47.49 waited_s="
        in result.stdout
    )
    assert (
        result.stdout.count("there is no version of\n      omnibase-core==0.47.49") == 2
    )
    assert "Resolved target" in result.stdout
    for attempt in range(1, 4):
        assert f"uv attempt {attempt}" in result.stdout
    _assert_invocations(tmp_path, 3)
    assert (tmp_path / "github-env").read_text() == "SKIP=false\n"


@pytest.mark.unit
def test_uv_index_wait_times_out_within_bound(tmp_path: Path) -> None:
    started = time.monotonic()
    result = _run_lock(tmp_path, "never", total_s=2)
    assert time.monotonic() - started < 8
    assert result.returncode == 1, (result.stdout, result.stderr)
    match = re.search(
        r"^CASCADE-UV-INDEX-WAIT-TIMEOUT package=omnibase-core version=0\.47\.49 waited_s=(\d+)$",
        result.stdout,
        re.MULTILINE,
    )
    assert match is not None, result.stdout
    assert 2 <= int(match.group(1)) < 8
    assert "::error::" in result.stdout
    assert "CASCADE-UV-INDEX-WAIT-OK" not in result.stdout
    count = int((tmp_path / "count").read_text())
    assert count > 1
    _assert_invocations(tmp_path, count)
    assert result.stdout.count("there is no version of") == count
    assert not (tmp_path / "github-env").exists()


@pytest.mark.unit
def test_unrelated_uv_failure_exits_immediately_with_its_status(tmp_path: Path) -> None:
    result = _run_lock(tmp_path, "unrelated")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "failed to fetch commit" in result.stdout
    assert "CASCADE-UV-INDEX-WAIT-" not in result.stdout
    _assert_invocations(tmp_path, 1)
    assert not (tmp_path / "github-env").exists()


@pytest.mark.unit
def test_successful_lock_without_changes_sets_skip(tmp_path: Path) -> None:
    result = _run_lock(tmp_path, "unchanged")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "CASCADE-UV-INDEX-WAIT-OK" in result.stdout
    assert "Resolved target" in result.stdout
    _assert_invocations(tmp_path, 1)
    assert (tmp_path / "github-env").read_text() == "SKIP=true\n"
