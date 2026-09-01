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

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_MODULE = REPO_ROOT / "scripts" / "hooks" / "pytest_full_suite_host_guard.py"
GRANT_MODULE = REPO_ROOT / "scripts" / "hooks" / "prepush_override_grant.py"
ROOT_CONFTEST = REPO_ROOT / "conftest.py"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "hooks"))
import pytest_full_suite_host_guard as guard

_GUARANTEED_NON_MATCHING_HOSTNAME = "definitely-not-the-200-host-omn15977"


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
            override_authorized=False,
        )
        is None
    )


def test_violation_message_none_when_host_matches_case_insensitive() -> None:
    assert (
        guard.full_suite_host_violation_message(
            host="Stickybeatz-Studio",
            target_hostname="stickybeatz-studio",
            override_authorized=False,
        )
        is None
    )


def test_violation_message_none_when_host_matches_201_gate_runner() -> None:
    assert (
        guard.full_suite_host_violation_message(
            host="gate-runner-201",
            target_hostname="stickybeatz-studio",
            additional_target_hostnames=("gate-runner-201",),
            override_authorized=False,
        )
        is None
    )


def test_violation_message_none_when_override_authorized() -> None:
    """``override_authorized`` is resolved by the caller from a CONSUMED grant
    token, never read off the environment (OMN-16480). The rename from
    ``allow_override`` is the point: the input is a spent, scope-checked
    authorization, not an ambient inheritable flag."""
    assert (
        guard.full_suite_host_violation_message(
            host="omnibook",
            target_hostname="stickybeatz-studio",
            override_authorized=True,
        )
        is None
    )


def test_violation_message_present_on_real_mismatch() -> None:
    message = guard.full_suite_host_violation_message(
        host="omnibook",
        target_hostname="stickybeatz-studio",
        override_authorized=False,
    )
    assert message is not None
    assert "omnibook" in message
    assert "stickybeatz-studio" in message
    assert "prepush_override_grant.py mint" in message, (
        "the refusal must name the supported override path; a refusal with no "
        "alternative is how a gate gets disabled outright"
    )
    assert "PREPUSH_ALLOW_LOCAL_FULL_SUITE" not in message, (
        "the message must not advertise the retired inheritable env var -- it "
        "is now refused, not honored"
    )


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
    for module in (GUARD_MODULE, GRANT_MODULE):
        (hooks_dir / module.name).write_text(
            module.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (project / "conftest.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent))\n"
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


def _hermetic_subprocess_env(env_overrides: dict[str, str]) -> dict[str, str]:
    """Base env for a guard-subprocess test, with ambient guard inputs stripped.

    The guard's ``is_ci_environment()`` check short-circuits BEFORE the host
    check (CI runners are never gated -- by design). If this OUTER test
    process is itself running under CI (as it does in this repo's own CI
    pipeline), ``dict(os.environ)`` would carry ``CI``/``GITHUB_ACTIONS``
    into the subprocess and mask the host-check assertions below regardless
    of ``PREPUSH_200_HOSTNAME`` -- the subprocess would exit 0 via the CI
    bypass, never reaching the code path under test. Strip those here so
    subprocess behavior depends only on the explicit ``env_overrides``, not
    on whether this test itself happens to run under CI. Tests that want the
    CI-bypass behavior (e.g. ``test_direct_invocation_allowed_under_ci_env``)
    still get it -- they set ``CI``/``GITHUB_ACTIONS`` explicitly via
    ``env_overrides``, applied after this strip.

    The subprocess must also discard the guard's local override and pytest's
    ambient narrowing controls. Otherwise a developer shell exporting
    ``PREPUSH_ALLOW_LOCAL_FULL_SUITE`` or ``PYTEST_ADDOPTS`` can bypass the
    refusal path the subprocess tests are proving.
    """
    env = _no_git_env()
    for name in (
        "CI",
        "GITHUB_ACTIONS",
        "PREPUSH_ALLOW_LOCAL_FULL_SUITE",
        "PREPUSH_200_HOSTNAME",
        "PYTEST_ADDOPTS",
        "PYTEST_CURRENT_TEST",
    ):
        env.pop(name, None)
    env.update(env_overrides)
    return env


#: A live `git push` exports these into hook children, and they override both
#: `-C` and cwd for every descendant `git` call (memory
#: reference_git_env_vars_override_c_and_cwd). Left set, a synthetic-repo test
#: would operate on THIS worktree instead -- the same leak the real hook unsets
#: for its pytest run.
_GIT_SCOPING_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
)


def _no_git_env() -> dict[str, str]:
    """Ambient env with every git LOCATION override removed (OMN-14891).

    Routed through the shipped `scrub_git_location_env` rather than a local
    pop-loop so this helper cannot drift from the validator's own notion of
    which variables retarget a repository -- a hand-maintained list here would
    silently stop covering a name the validator later adds.
    """
    env = dict(scrub_git_location_env(os.environ))
    for name in _GIT_SCOPING_ENV_VARS:
        env.pop(name, None)
    return env


def _git_init(project: Path) -> None:
    """Make the synthetic project a real git repo with one commit.

    The grant is bound to a repo root and a HEAD sha, both resolved from git by
    the shipped module itself (never from a caller argument -- a forgeable
    scope binds nothing). So the behavioral grant test needs a real, if
    minimal, worktree rather than a bare directory.
    """
    for args in (
        ["init", "-q"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "test"],
        ["add", "-A"],
        ["commit", "-q", "-m", "synthetic project", "--no-gpg-sign"],
    ):
        # The scrub is spelled out here rather than hoisted into a local `env`
        # so the OMN-14891 guard can verify it statically. GIT_DIR /
        # GIT_WORK_TREE / GIT_INDEX_FILE are exported into every process a git
        # hook spawns and OVERRIDE both `cwd=` and `-C`, so an unscrubbed call
        # would build this synthetic project inside the REAL worktree.
        subprocess.run(
            ["git", *args],
            cwd=project,
            env=scrub_git_location_env(os.environ),
            capture_output=True,
            check=True,
        )


def _run_pytest(
    project: Path, *extra_args: str, env_overrides: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    env = _hermetic_subprocess_env(env_overrides)
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
    env = _hermetic_subprocess_env(
        {"PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME}
    )
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


def test_direct_invocation_refused_when_override_env_is_present(
    tmp_path: Path,
) -> None:
    """INVERTED by OMN-16480. This test previously asserted that
    ``PREPUSH_ALLOW_LOCAL_FULL_SUITE=1`` bypasses the guard -- which is exactly
    the behavior that let one leaked variable recursively spawn a second
    44,064-test suite and burn ~9h03m (friction report F-01/F-04).

    An environment variable is inherited by every descendant process, so
    honoring one means the guard is disarmed for a whole process tree,
    silently, with no receipt. The variable is now a REFUSAL: the leak
    terminates here instead of arming the next level of recursion.
    """
    project = _write_synthetic_project(tmp_path)
    result = _run_pytest(
        project,
        env_overrides={
            "PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME,
            "PREPUSH_ALLOW_LOCAL_FULL_SUITE": "1",
        },
    )
    assert result.returncode != 0, (
        "expected an inherited PREPUSH_ALLOW_* variable to be REFUSED, not "
        f"honored; got exit {result.returncode}. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "PREPUSH_ALLOW_LOCAL_FULL_SUITE" in combined, f"output={combined!r}"
    assert "REJECTED" in combined, f"output={combined!r}"
    assert "1 passed" not in result.stdout, (
        "the refusal must land before any test executes"
    )


def test_direct_invocation_allowed_with_a_minted_grant(tmp_path: Path) -> None:
    """End-to-end proof that the replacement escape path actually works, and
    that it is single-use.

    Without this, the fix could ship as a gate with no usable override at all
    -- which gets the gate itself disabled within a week (the verbatim
    rationale the OMN-15059 guard was written under). The second run proves the
    grant is spent: a nested invocation cannot replay it, which is the property
    that terminates the OMN-16425 recursion.
    """
    project = _write_synthetic_project(tmp_path)
    _git_init(project)

    mint = subprocess.run(
        [
            sys.executable,
            str(project / "scripts" / "hooks" / "prepush_override_grant.py"),
            "mint",
            "--reason",
            "behavioral proof for OMN-16480",
            "--ttl-minutes",
            "5",
        ],
        cwd=project,
        env=_no_git_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert mint.returncode == 0, f"mint failed: {mint.stderr!r}"

    allowed = _run_pytest(
        project,
        env_overrides={"PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME},
    )
    assert allowed.returncode == 0, (
        "expected a minted single-use grant to authorize this run; got exit "
        f"{allowed.returncode}. stdout={allowed.stdout!r} "
        f"stderr={allowed.stderr!r}"
    )
    assert "1 passed" in allowed.stdout, f"stdout={allowed.stdout!r}"

    refused = _run_pytest(
        project,
        env_overrides={"PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME},
    )
    assert refused.returncode != 0, (
        "the grant must be SPENT after one use -- a reusable grant is an "
        "environment variable with extra steps"
    )
    assert "not the designated .200 build host" in refused.stderr

    receipts = (
        project / ".onex_state" / "prepush_override" / "receipts.jsonl"
    ).read_text(encoding="utf-8")
    assert "prepush_override_consumed" in receipts, (
        "every override use must leave a receipt -- an invisible override is "
        "the F-04 defect regardless of how it is spelled"
    )


# =============================================================================
# 3. The committed host table is the identity authority (OMN-16991)
# =============================================================================
#
# A dispatched pre-push run executes inside a TRANSPLANTED copy of this repo,
# which carries this very guard. Until the guard read the same committed table
# the bash hook reads, a lab host could be a legitimate placement target and
# still have every full-suite run there die at `pytest_configure` -- writing a
# receipt whose nonzero pytest exit is indistinguishable from a genuine red.

_HOST_TABLE_HEADER = (
    "#label\trole\thostname\tssh_target\tcores\tuv_abs_path\tuv_min_version"
    "\tworkroot\tslot_mode\tslots\trepos_denied\tmode\tnote\n"
)


def _write_host_table(project: Path, hostname: str, mode: str) -> None:
    (project / "scripts" / "hooks" / "prepush_hosts.tsv").write_text(
        _HOST_TABLE_HEADER
        + f"hx\tcapacity\t{hostname}\t-\t8\t/bin/uv\t0.1.0\t/tmp/w\tlockdir\t1\t-\t{mode}\tsynthetic\n",
        encoding="utf-8",
    )


def test_full_suite_allowed_when_the_committed_table_authorizes_this_host(
    tmp_path: Path,
) -> None:
    """The proof that a transplanted full suite can now go green on a promoted
    lab host: identity comes from the committed table, and a nonsense
    PREPUSH_200_HOSTNAME (which alone used to decide this) cannot veto it."""
    project = _write_synthetic_project(tmp_path)
    real_host = guard.resolve_local_hostname()
    assert real_host, "this test requires a resolvable local hostname"
    _write_host_table(project, real_host.lower(), "authorizing")
    _git_init(project)
    result = _run_pytest(
        project,
        env_overrides={"PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME},
    )
    assert result.returncode == 0, (
        "an authorizing row for this host must let the full suite run; got "
        f"exit {result.returncode}. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "1 passed" in result.stdout, f"stdout={result.stdout!r}"


def test_full_suite_refused_when_the_committed_table_only_shadows_this_host(
    tmp_path: Path,
) -> None:
    """`shadow` is a placement mode, never an identity. This is the exact
    reason a shadow host could never record the green run its own promotion
    criteria demanded."""
    project = _write_synthetic_project(tmp_path)
    real_host = guard.resolve_local_hostname()
    _write_host_table(project, real_host.lower(), "shadow")
    _git_init(project)
    result = _run_pytest(
        project,
        env_overrides={"PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME},
    )
    assert result.returncode != 0, (
        f"a shadow row must not authorize; got exit {result.returncode}"
    )
    assert "not the designated .200 build host" in result.stderr


def test_an_uncommitted_table_row_cannot_self_designate_this_host(
    tmp_path: Path,
) -> None:
    """The forgeable-artifact surface OMN-16688 deliberately avoided: a
    one-line uncommitted edit naming this machine must not authorize it, so the
    working copy has to agree with HEAD."""
    project = _write_synthetic_project(tmp_path)
    real_host = guard.resolve_local_hostname()
    _write_host_table(project, "some-other-machine", "authorizing")
    _git_init(project)
    _write_host_table(project, real_host.lower(), "authorizing")
    result = _run_pytest(
        project,
        env_overrides={"PREPUSH_200_HOSTNAME": _GUARANTEED_NON_MATCHING_HOSTNAME},
    )
    assert result.returncode != 0, (
        f"an uncommitted row must be ignored, not honored; got exit {result.returncode}"
    )
