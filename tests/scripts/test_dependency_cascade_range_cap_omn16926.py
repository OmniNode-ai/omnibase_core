# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-16926: a range-capped cascade leg must fail, never report "already on latest".

``uv lock --upgrade-package`` cannot cross a ``pyproject.toml`` range cap
(``omnibase-core>=0.46.13,<0.47.0``) any more than a ``[tool.uv.sources]`` git
override. A capped leg re-resolves inside the cap, produces no lockfile diff,
and the Skip summary used to read that as "already uses the latest version".

Three changes close it:

* the movable guard passes ``--target-version`` (the released version) to
  ``check_dep_provenance.py`` so its range-cap channel runs;
* the guard runs AFTER the exact-pin rewrite, so an exact stale pin that the
  rewrite moves to the target is not reported as capped;
* after the lock, a step reads the version ``uv.lock`` actually locks and fails
  the leg unless it equals the released version, so "no change" is reported
  only when the lock already holds the target.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"

VERIFY_STEP = "Verify locked version is the target"


def _steps() -> list[dict[str, object]]:
    with WORKFLOW_PATH.open() as fh:
        doc = yaml.safe_load(fh)
    steps = doc["jobs"]["open-bump-pr"]["steps"]
    assert isinstance(steps, list)
    return [s for s in steps if isinstance(s, dict)]


def _names() -> list[object]:
    return [s.get("name") for s in _steps()]


def _step(name: str) -> dict[str, object]:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(f"open-bump-pr has no step named {name!r}: {_names()}")


def _run(name: str) -> str:
    run = _step(name).get("run", "")
    assert isinstance(run, str)
    return run


@pytest.mark.unit
def test_movable_guard_receives_the_released_version_as_target() -> None:
    step = _step("Check dependency is movable")
    env = step.get("env")
    assert isinstance(env, dict), step
    assert env.get("TARGET_VERSION") == "${{ steps.vars.outputs.version }}", env
    run = _run("Check dependency is movable")
    assert "--check-movable" in run, run
    assert '--target-version "$TARGET_VERSION"' in run, run


@pytest.mark.unit
def test_pin_rewrite_runs_before_the_movable_guard() -> None:
    names = _names()
    pin_idx = names.index("Update pyproject.toml pin")
    guard_idx = names.index("Check dependency is movable")
    lock_idx = names.index("Upgrade lockfile")
    assert pin_idx < guard_idx < lock_idx, names


@pytest.mark.unit
def test_verify_step_sits_between_lock_and_commit_and_runs_on_skip() -> None:
    names = _names()
    assert VERIFY_STEP in names, names
    verify_idx = names.index(VERIFY_STEP)
    assert names.index("Upgrade lockfile") < verify_idx, names
    assert verify_idx < names.index("Commit and push"), names
    assert verify_idx < names.index("Skip summary"), names
    condition = _step(VERIFY_STEP).get("if")
    assert condition == "steps.token_check.outputs.has_token == 'true'", condition
    env = _step(VERIFY_STEP).get("env")
    assert isinstance(env, dict)
    assert env.get("PKG_HYPHEN") == "${{ steps.vars.outputs.pkg_hyphen }}", env
    assert env.get("RESOLVED") == "${{ steps.vars.outputs.version }}", env


@pytest.mark.unit
def test_skip_summary_states_the_locked_version_not_latest() -> None:
    run = _run("Skip summary")
    assert "already uses the latest version" not in run, run
    assert "${RESOLVED}" in run, run
    env = _step("Skip summary").get("env")
    assert isinstance(env, dict)
    assert env.get("RESOLVED") == "${{ steps.vars.outputs.version }}", env
    assert "already on latest" not in _run("Upgrade lockfile")


def _lock(tmp_path: Path, packages: dict[str, str]) -> Path:
    blocks = [
        f'[[package]]\nname = "{name}"\nversion = "{version}"\n'
        for name, version in packages.items()
    ]
    (tmp_path / "uv.lock").write_text(
        'version = 1\nrequires-python = ">=3.12"\n\n' + "\n".join(blocks)
    )
    return tmp_path


def _run_verify(cwd: Path, target: str) -> subprocess.CompletedProcess[str]:
    if shutil.which("uv") is None:
        pytest.skip("uv is not on PATH")
    exports = (
        "export PKG_HYPHEN=omnibase-core REPO_NAME=omniintelligence "
        f"RESOLVED={shlex.quote(target)}\n"
    )
    return subprocess.run(
        ["bash", "-c", exports + _run(VERIFY_STEP)],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.unit
def test_verify_step_passes_when_lock_holds_the_target(tmp_path: Path) -> None:
    cwd = _lock(tmp_path, {"omnibase-core": "0.47.0", "pydantic": "2.11.0"})
    result = _run_verify(cwd, "0.47.0")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CASCADE-LOCKED-VERSION-OK" in result.stdout, result.stdout


@pytest.mark.unit
def test_verify_step_fails_a_capped_leg_naming_both_versions(tmp_path: Path) -> None:
    cwd = _lock(tmp_path, {"omnibase-core": "0.46.13"})
    result = _run_verify(cwd, "0.47.0")
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert "::error::" in out, out
    assert "0.46.13" in out, out
    assert "0.47.0" in out, out
    assert "CASCADE-LOCKED-VERSION-OK" not in out, out


@pytest.mark.unit
def test_verify_step_fails_when_the_package_is_not_locked(tmp_path: Path) -> None:
    cwd = _lock(tmp_path, {"pydantic": "2.11.0"})
    result = _run_verify(cwd, "0.47.0")
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert "::error::" in out, out
