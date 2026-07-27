# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the unguarded-git-subprocess guard (OMN-14891).

The guard must FAIL CLOSED on any git shell-out in tests/ that can inherit
GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE / GIT_COMMON_DIR from a git hook, while
staying silent on legitimately-scrubbed calls and on the many non-call
occurrences of the string ``"git"`` that already exist in this suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    GIT_LOCATION_ENV_VARS,
    main,
    validate_paths,
    validate_source,
)

pytestmark = pytest.mark.unit

FAKE = Path("tests/unit/fake_test_module.py")


# ---------------------------------------------------------------------------
# must FIRE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        'subprocess.run(["git", "init"], cwd=repo, check=True)',
        'subprocess.run(["git", "-C", str(repo), "add", "."], check=True)',
        'subprocess.check_call(["git", "commit", "-m", "x"], cwd=repo)',
        'subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo)',
        'subprocess.Popen(["git", "status"], cwd=repo)',
        'subprocess.call(["git", "status"], cwd=repo)',
        'subprocess.run(("git", "init"), cwd=repo)',
    ],
)
def test_unguarded_git_call_is_flagged(source: str) -> None:
    assert len(validate_source(FAKE, source)) == 1


def test_env_copied_from_os_environ_is_not_a_scrub() -> None:
    """`env=os.environ.copy()` inherits every override — the exact defect."""
    findings = validate_source(
        FAKE, 'subprocess.run(["git", "init"], cwd=repo, env=os.environ.copy())'
    )
    assert len(findings) == 1
    assert "without removing" in findings[0].reason


def test_partial_scrub_is_not_a_scrub() -> None:
    """A helper that misses even one location variable must still fail."""
    source = """
import os
import subprocess


def _git(repo, *args):
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE"):
        env.pop(key, None)
    return subprocess.run(["git", *args], cwd=repo, env=env)
"""
    assert len(validate_source(FAKE, source)) == 1


def test_git_config_global_is_rejected_even_when_scrubbed() -> None:
    """An env scrub fixes location; it cannot stop a deliberate global write."""
    source = (
        'subprocess.run(["git", "config", "--global", "user.email", "x@y.z"], '
        "env=scrub_git_location_env(os.environ))"
    )
    findings = validate_source(FAKE, source)
    assert len(findings) == 1
    assert "--global" in findings[0].reason


def test_git_config_system_is_rejected() -> None:
    source = (
        'subprocess.run(["git", "config", "--system", "x", "y"], '
        "env=scrub_git_location_env(os.environ))"
    )
    assert len(validate_source(FAKE, source)) == 1


# ---------------------------------------------------------------------------
# must NOT fire
# ---------------------------------------------------------------------------


def test_canonical_helper_is_accepted() -> None:
    source = (
        'subprocess.run(["git", "init"], cwd=repo, '
        "env=scrub_git_location_env(os.environ))"
    )
    assert validate_source(FAKE, source) == []


def test_full_replacement_env_is_accepted() -> None:
    """A replacement environment cannot inherit GIT_DIR by construction."""
    source = 'subprocess.run(["git", "init"], cwd=repo, env={"PATH": "/usr/bin"})'
    assert validate_source(FAKE, source) == []


def test_replacement_env_reading_os_environ_is_rejected() -> None:
    """`{**os.environ}` looks like a literal but still inherits everything."""
    source = 'subprocess.run(["git", "init"], cwd=repo, env={**os.environ})'
    assert len(validate_source(FAKE, source)) == 1


def test_inline_scrub_in_enclosing_function_is_accepted() -> None:
    """The shape the pre-existing per-file fixes use."""
    keys = ",\n        ".join(f'"{name}"' for name in GIT_LOCATION_ENV_VARS)
    source = f"""
import os
import subprocess


def _git(repo, *args):
    env = os.environ.copy()
    for key in (
        {keys},
    ):
        env.pop(key, None)
    return subprocess.run(["git", *args], cwd=repo, env=env)
"""
    assert validate_source(FAKE, source) == []


def test_scrubbing_helper_referenced_by_name_is_accepted() -> None:
    keys = ",\n        ".join(f'"{name}"' for name in GIT_LOCATION_ENV_VARS)
    source = f"""
import os
import subprocess


def _base_env():
    env = dict(os.environ)
    for key in (
        {keys},
    ):
        env.pop(key, None)
    return env


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, env={{**_base_env()}})
"""
    assert validate_source(FAKE, source) == []


@pytest.mark.parametrize(
    "source",
    [
        # `git` as a dict key, not a program.
        'config = {"permissions": {"git": {"commit": False}}}',
        # `git` as a plain value.
        'fields["mutation_verb"] = "git"',
        'assert "git" not in load_runtime_ops_verb_allowlist()',
        # `git` as an exception argument, not an argv.
        'raise subprocess.TimeoutExpired("git", 60)',
        # source code *about* a git call, held in a string literal.
        'src = \'subprocess.run([\\"git\\", \\"status\\"])\'',
        # a non-git program.
        'subprocess.run(["python", str(script)], cwd=repo)',
        # git appears as an argument, not the program.
        'subprocess.run(["sudo", "git", "status"], cwd=repo)',
    ],
)
def test_non_call_occurrences_do_not_fire(source: str) -> None:
    assert validate_source(FAKE, source) == []


def test_dynamic_argv_is_not_flagged() -> None:
    """A non-literal argv carries no static evidence; it is out of scope."""
    assert validate_source(FAKE, "subprocess.run(argv, cwd=repo)") == []


# ---------------------------------------------------------------------------
# self-scan + CLI
# ---------------------------------------------------------------------------


def test_repo_tests_tree_is_clean() -> None:
    """The live regression: tests/ must contain no unguarded git call.

    This is what turns the guard from detection into enforcement — it fails the
    moment anyone reintroduces the OMN-14891 shape anywhere under tests/.
    """
    tests_root = Path(__file__).resolve().parents[2]
    findings = validate_paths([tests_root])
    assert findings == [], "\n".join(finding.format() for finding in findings)


def test_guard_itself_is_not_flagged() -> None:
    """The scrub helper and this suite must not trip their own gate."""
    here = Path(__file__).resolve()
    assert validate_paths([here]) == []


def test_main_returns_nonzero_on_violation(tmp_path: Path) -> None:
    offender = tmp_path / "test_offender.py"
    offender.write_text(
        'import subprocess\nsubprocess.run(["git", "init"], cwd="/tmp")\n',
        encoding="utf-8",
    )
    assert main([str(offender)]) == 1


def test_main_returns_zero_when_clean(tmp_path: Path) -> None:
    clean = tmp_path / "test_clean.py"
    clean.write_text("x = 1\n", encoding="utf-8")
    assert main([str(clean)]) == 0
