# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression guard for the direct-invocation .200-default host guard
(OMN-15977 Hole 1).

Root cause this prevents regressing: the OMN-15059 guard
(`scripts/hooks/prepush_smart_tests.sh`) only fires on the `git push` path.
Build agents routinely run the full suite DIRECTLY as a verification step
(`uv run pytest tests/ -q > .gate_logs/full_suite3.log`) -- no pre-push hook
fires for that invocation, so the `.200`-default host-check is never
consulted. Observed 3x in one lane (full_suite1/2/3) on 2026-08-12.

`scripts/hooks/pytest_full_suite_host_guard.py` closes this by hooking
`pytest_configure` from the repo-root `conftest.py`, which -- unlike a hook
under `tests/conftest.py` -- loads for EVERY invocation regardless of which
testpath is targeted.

Two assertion classes:

1. Pure-function unit tests against the decision logic directly (fast,
   exhaustive: CI env, override env, `-k`/`-m` narrowing, narrow vs.
   whole-suite targets, host match/mismatch/undetermined).
2. Behavioral, end-to-end: a real `pytest` subprocess against a synthetic
   project that imports the shipped guard module and wires it exactly the
   way the repo-root `conftest.py` does, proving the guard actually refuses a
   non-`.200` direct full-suite invocation BEFORE collection -- the
   `proof_class: receipt-bound` requirement for OMN-15977.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_MODULE = REPO_ROOT / "scripts" / "hooks" / "pytest_full_suite_host_guard.py"
ROOT_CONFTEST = REPO_ROOT / "conftest.py"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "hooks"))
# NOTE(OMN-15977): dynamic sys.path import -- mypy cannot resolve this
# statically (unlike src/omnibase_core, this repo's tests/ tree is outside
# mypy's `mypy src/omnibase_core` CI gate, and core's [tool.mypy] does not
# set ignore_missing_imports globally the way sibling repos do).
import pytest_full_suite_host_guard as guard  # type: ignore[import-not-found]

_GUARANTEED_NON_MATCHING_HOSTNAME = "definitely-not-the-200-host-omn15977"

# The guard fail-opens under CI env and honors the override env var. The
# behavioral subprocess tests inherit this process's environment, so on a CI
# runner (CI=true / GITHUB_ACTIONS=true) an un-stripped inherit would bypass
# the guard and invert the refusal assertions. Strip them; tests that need one
# (e.g. the CI-bypass pin) re-add it explicitly via env_overrides.
_ENV_VARS_THAT_BYPASS_THE_GUARD = (
    "CI",
    "GITHUB_ACTIONS",
    "PREPUSH_ALLOW_LOCAL_FULL_SUITE",
)


def _guard_neutral_env() -> dict[str, str]:
    return {
        k: v for k, v in os.environ.items() if k not in _ENV_VARS_THAT_BYPASS_THE_GUARD
    }


# =============================================================================
# 1. Pure decision-function unit tests
# =============================================================================


def test_guard_module_and_root_conftest_exist() -> None:
    assert GUARD_MODULE.is_file(), f"expected {GUARD_MODULE}"
    assert ROOT_CONFTEST.is_file(), (
        "expected a repo-root conftest.py -- unlike tests/conftest.py, this is "
        "the only conftest.py pytest loads for EVERY testpath in this repo "
        "(scripts/ci/tests, scripts/tests, ... per pyproject.toml testpaths)"
    )


def test_root_conftest_wires_pytest_configure_not_collection_modifyitems() -> None:
    """Must hook pytest_configure (before collection), not
    pytest_collection_modifyitems (after collection) -- collecting this
    repo's several-thousand-test tree is itself non-trivial wall-clock, so
    refusing only after paying that cost defeats the purpose."""
    text = ROOT_CONFTEST.read_text(encoding="utf-8")
    assert "def pytest_configure(" in text
    assert "def pytest_collection_modifyitems(" not in text


def test_is_ci_environment() -> None:
    assert guard.is_ci_environment({"CI": "true"})
    assert guard.is_ci_environment({"GITHUB_ACTIONS": "true"})
    assert not guard.is_ci_environment({})


def test_is_full_suite_target_bare_invocation_falls_back_to_testpaths() -> None:
    assert guard.is_full_suite_target(
        args=[],
        testpaths=["tests/unit"],
        keyword="",
        markexpr="",
        full_suite_target="tests/unit",
    )


def test_is_full_suite_target_ancestor_directory_counts() -> None:
    """`tests/` is an ancestor of `tests/unit/` -- selecting it hands pytest
    the whole escalation target under a different label."""
    assert guard.is_full_suite_target(
        args=["tests/"],
        testpaths=[],
        keyword="",
        markexpr="",
        full_suite_target="tests/unit",
    )


def test_is_full_suite_target_narrow_subdirectory_is_not_whole_suite() -> None:
    assert not guard.is_full_suite_target(
        args=["tests/unit/hooks"],
        testpaths=[],
        keyword="",
        markexpr="",
        full_suite_target="tests/unit",
    )


def test_is_full_suite_target_single_file_is_not_whole_suite() -> None:
    assert not guard.is_full_suite_target(
        args=["tests/unit/hooks/test_something.py"],
        testpaths=[],
        keyword="",
        markexpr="",
        full_suite_target="tests/unit",
    )


def test_is_full_suite_target_keyword_narrowing_exempts_whole_suite_path() -> None:
    """`-k` on `tests/unit` is a real narrowing even though the target path
    looks like the whole suite -- the guard must not brick that workflow."""
    assert not guard.is_full_suite_target(
        args=["tests/unit"],
        testpaths=[],
        keyword="test_something",
        markexpr="",
        full_suite_target="tests/unit",
    )


def test_is_full_suite_target_markexpr_narrowing_exempts_whole_suite_path() -> None:
    assert not guard.is_full_suite_target(
        args=["tests/unit"],
        testpaths=[],
        keyword="",
        markexpr="unit",
        full_suite_target="tests/unit",
    )


def test_is_full_suite_target_no_args_and_no_testpaths_is_not_whole_suite() -> None:
    assert not guard.is_full_suite_target(
        args=[],
        testpaths=[],
        keyword="",
        markexpr="",
        full_suite_target="tests/unit",
    )


def test_violation_message_none_when_host_undetermined() -> None:
    """Fail-open: an unresolvable hostname must not block the run. This is a
    routing optimization, not a security control (see module docstring)."""
    assert (
        guard.full_suite_host_violation_message(
            host="",
            target_hostname="stickybeatz-studio",
            allow_override=False,
        )
        is None
    )


def test_violation_message_none_when_host_matches_case_insensitive() -> None:
    assert (
        guard.full_suite_host_violation_message(
            host="Stickybeatz-Studio",
            target_hostname="stickybeatz-studio",
            allow_override=False,
        )
        is None
    )


def test_violation_message_none_when_override_set() -> None:
    assert (
        guard.full_suite_host_violation_message(
            host="omnibook",
            target_hostname="stickybeatz-studio",
            allow_override=True,
        )
        is None
    )


def test_violation_message_present_on_real_mismatch() -> None:
    message = guard.full_suite_host_violation_message(
        host="omnibook",
        target_hostname="stickybeatz-studio",
        allow_override=False,
    )
    assert message is not None
    assert "omnibook" in message
    assert "stickybeatz-studio" in message
    assert "PREPUSH_ALLOW_LOCAL_FULL_SUITE" in message


# =============================================================================
# 2. Behavioral: real pytest subprocess, proves refusal end-to-end
# =============================================================================


def _write_synthetic_project(tmp_path: Path) -> Path:
    """A minimal project that wires the SHIPPED guard module exactly the way
    this repo's root conftest.py does, so the behavioral assertion below
    exercises the real shipped code, not a re-implementation of it."""
    project = tmp_path / "proj"
    hooks_dir = project / "scripts" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "pytest_full_suite_host_guard.py").write_text(
        GUARD_MODULE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (project / "conftest.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent / 'scripts' / 'hooks'))\n"
        "from pytest_full_suite_host_guard import enforce\n\n"
        "def pytest_configure(config):\n"
        "    enforce(config, 'tests')\n",
        encoding="utf-8",
    )
    tests_dir = project / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_x.py").write_text(
        "def test_x():\n    assert True\n", encoding="utf-8"
    )
    return project


def _run_pytest(
    project: Path, *extra_args: str, env_overrides: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    env = _guard_neutral_env()
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests", *extra_args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_direct_invocation_refused_on_non_200_host(tmp_path: Path) -> None:
    """THE OMN-15977 Hole-1 regression proof: a direct `pytest tests` run
    (no `git push` in sight) on a non-.200 host is refused BEFORE
    collection."""
    project = _write_synthetic_project(tmp_path)
    result = _run_pytest(
        project,
        env_overrides={"PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME},
    )
    assert result.returncode != 0, (
        "expected the direct-invocation guard to refuse a full-suite pytest "
        f"run on a non-.200 host; got exit {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "not the designated .200 build host" in result.stderr, (
        f"expected the refusal message; got stderr={result.stderr!r}"
    )
    assert "1 passed" not in result.stdout, (
        "the guard must refuse BEFORE any test executes -- found a passing "
        f"test run in stdout: {result.stdout!r}"
    )


def test_direct_invocation_allowed_when_host_matches(tmp_path: Path) -> None:
    """Anti-overreach pin: on the designated .200 host, a full-suite direct
    invocation must proceed normally."""
    project = _write_synthetic_project(tmp_path)
    real_host = guard.resolve_local_hostname()
    assert real_host, "this test requires a resolvable local hostname"
    result = _run_pytest(project, env_overrides={"PREPUSH_200_HOSTNAME": real_host})
    assert result.returncode == 0, (
        f"expected the run to proceed on a matching host; got exit "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "1 passed" in result.stdout, f"stdout={result.stdout!r}"


def test_direct_invocation_allowed_with_narrow_target_on_non_200_host(
    tmp_path: Path,
) -> None:
    """Anti-overreach pin: a real narrow target must still run locally. If
    this ever fails, the guard has become a blanket local-pytest block and
    will be disabled within a week -- worse than no guard at all."""
    project = _write_synthetic_project(tmp_path)
    (project / "tests" / "sub").mkdir()
    (project / "tests" / "sub" / "test_y.py").write_text(
        "def test_y():\n    assert True\n", encoding="utf-8"
    )
    env = _guard_neutral_env()
    env["PREPUSH_200_HOSTNAME"] = _GUARANTEED_NON_MATCHING_HOSTNAME
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sub"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"expected a narrow (non-whole-suite) target to be allowed on a "
        f"non-.200 host; got exit {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "1 passed" in result.stdout, f"stdout={result.stdout!r}"


def test_direct_invocation_allowed_under_ci_env(tmp_path: Path) -> None:
    """CI runners are never gated -- this guard exists to protect a
    contended local Mac, not a short-lived, isolated CI runner."""
    project = _write_synthetic_project(tmp_path)
    result = _run_pytest(
        project,
        env_overrides={
            "PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME,
            "CI": "true",
        },
    )
    assert result.returncode == 0, (
        f"expected CI env to bypass the guard entirely; got exit "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "1 passed" in result.stdout, f"stdout={result.stdout!r}"


def test_direct_invocation_allowed_with_override_env(tmp_path: Path) -> None:
    project = _write_synthetic_project(tmp_path)
    result = _run_pytest(
        project,
        env_overrides={
            "PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME,
            "PREPUSH_ALLOW_LOCAL_FULL_SUITE": "1",
        },
    )
    assert result.returncode == 0, (
        f"expected PREPUSH_ALLOW_LOCAL_FULL_SUITE=1 to bypass the guard; got "
        f"exit {result.returncode}. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "1 passed" in result.stdout, f"stdout={result.stdout!r}"
