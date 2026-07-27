# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression proof for the OMN-14891 git-environment hijack.

Git exports ``GIT_DIR`` / ``GIT_WORK_TREE`` / ``GIT_INDEX_FILE`` /
``GIT_COMMON_DIR`` into every hook environment, and those variables OVERRIDE both
``cwd=`` and ``git -C``. A test fixture doing ``subprocess.run(["git", "init"],
cwd=tmp_path)`` therefore mutates the REAL invoking worktree when pytest runs
under this repo's pre-push hook.

WHY THIS FILE IS NOT VACUOUS
----------------------------
A test that merely asserts "``GIT_DIR`` is not in ``os.environ``" is worthless:
it passes for free whenever pytest happens to be launched from a normal shell,
which is exactly the condition under which the bug is invisible. So the proof
here is a DISCRIMINATOR PAIR over the same helper and the same child script:

* :func:`test_inherited_git_dir_hijacks_unguarded_git_calls` is the NEGATIVE
  CONTROL. It runs the child WITHOUT the scrub and asserts the decoy repo IS
  corrupted. If this assertion ever stops holding, the harness has stopped
  reproducing the defect and the sibling test below has become vacuous — so the
  suite goes red rather than silently green.
* :func:`test_scrub_prevents_inherited_git_dir_hijack` runs the identical child
  WITH the scrub and asserts the decoy is untouched while the intended tmp repo
  is written.

Neither test can pass by accident: the pair only goes green when the fake
``GIT_DIR`` is demonstrably load-bearing AND the scrub demonstrably defeats it.

Every git invocation below is itself guarded via ``scrub_git_location_env`` — a
test for this hazard must not be an instance of it.

Tickets: OMN-14891 (this defect), OMN-14744 (the per-file fix that did not hold),
OMN-14892 (index corruption under the same full-suite run).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    GIT_DISCOVERY_ENV_VARS,
    GIT_LOCATION_ENV_VARS,
    scrub_git_location_env,
    strip_git_location_env,
)

pytestmark = pytest.mark.unit

# A value that cannot plausibly occur in any real git config.
SENTINEL_EMAIL = "hijack@omn14891.invalid"
SENTINEL_NAME = "omn14891-hijack-probe"

# The child program. `SCRUB` is substituted with either the real scrub call or a
# no-op, so the hijacked and guarded runs execute byte-identical git operations
# and differ only in whether the environment was cleaned.
_CHILD_PROGRAM = """\
import os
import subprocess
import sys

sys.path.insert(0, {src!r})
from omnibase_core.validators.no_unguarded_git_subprocess import (
    strip_git_location_env,
)

work = {work!r}

{scrub}

# Deliberately UNGUARDED, exactly as the polluting fixtures were written: no
# env= keyword, so this inherits whatever git overrides are in the environment.
subprocess.run(["git", "init", "-q"], cwd=work, check=True)
subprocess.run(
    ["git", "config", "user.email", {email!r}], cwd=work, check=True
)
subprocess.run(["git", "config", "user.name", {name!r}], cwd=work, check=True)
"""


def _git(repo: Path, *args: str) -> None:
    """Run git against ``repo`` with a scrubbed environment."""
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(os.environ),
    )


def _make_decoy_repo(tmp_path: Path) -> Path:
    """A throwaway stand-in for the real invoking worktree. Never the real repo."""
    decoy = tmp_path / "decoy_worktree"
    decoy.mkdir()
    _git(decoy, "init", "-q")
    return decoy


def _run_child(
    work: Path, decoy: Path, *, scrub: bool
) -> subprocess.CompletedProcess[str]:
    """Run the fixture-style git operations in a child that inherits GIT_DIR."""
    work.mkdir(parents=True, exist_ok=True)
    src = str(Path(__file__).resolve().parents[2] / "src")
    program = _CHILD_PROGRAM.format(
        src=src,
        work=str(work),
        email=SENTINEL_EMAIL,
        name=SENTINEL_NAME,
        scrub=(
            "strip_git_location_env(os.environ)"
            if scrub
            else "# scrub deliberately omitted (negative control)"
        ),
    )
    script = work.parent / f"child_{'guarded' if scrub else 'hijacked'}.py"
    script.write_text(program, encoding="utf-8")

    # Start from a clean environment, then inject the FAKE overrides a git hook
    # would export. The fake GIT_DIR points at the decoy, never the real repo.
    child_env = scrub_git_location_env(os.environ)
    child_env["GIT_DIR"] = str(decoy / ".git")
    child_env["GIT_WORK_TREE"] = str(decoy)
    child_env["GIT_INDEX_FILE"] = str(decoy / ".git" / "index")

    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
        env=child_env,
    )


def _decoy_config(decoy: Path) -> str:
    return (decoy / ".git" / "config").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# negative control: the fake GIT_DIR must genuinely be load-bearing
# ---------------------------------------------------------------------------


def test_inherited_git_dir_hijacks_unguarded_git_calls(tmp_path: Path) -> None:
    """WITHOUT the scrub, an inherited GIT_DIR redirects git at the decoy repo.

    This is the reproduction. It asserts the DAMAGE happens, which is what makes
    the guarded sibling test below a real proof instead of a tautology.
    """
    decoy = _make_decoy_repo(tmp_path)
    assert SENTINEL_EMAIL not in _decoy_config(decoy)

    result = _run_child(tmp_path / "unguarded_work", decoy, scrub=False)
    assert result.returncode == 0, result.stderr

    hijacked = _decoy_config(decoy)
    assert SENTINEL_EMAIL in hijacked, (
        "the fake GIT_DIR did not redirect the child's git calls, so this test "
        "cannot prove anything about the scrub — the harness is broken"
    )
    assert SENTINEL_NAME in hijacked


# ---------------------------------------------------------------------------
# the fix
# ---------------------------------------------------------------------------


def test_scrub_prevents_inherited_git_dir_hijack(tmp_path: Path) -> None:
    """WITH the scrub, the identical operations leave the decoy untouched."""
    decoy = _make_decoy_repo(tmp_path)
    work = tmp_path / "guarded_work"

    result = _run_child(work, decoy, scrub=True)
    assert result.returncode == 0, result.stderr

    guarded = _decoy_config(decoy)
    assert SENTINEL_EMAIL not in guarded, (
        f"OMN-14891 regression: git wrote into the directory named by GIT_DIR "
        f"({decoy / '.git'}) despite cwd={work}"
    )
    assert SENTINEL_NAME not in guarded
    assert "bare = true" not in guarded, (
        "OMN-14891 regression: `git init` re-initialised the GIT_DIR target as "
        "bare — the exact mutation observed on the shared canonical clone"
    )

    # The operations must still have DONE something; a scrub that broke git
    # would pass the assertions above for the wrong reason.
    assert SENTINEL_EMAIL in (work / ".git" / "config").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# the session fixture itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variable", [*GIT_LOCATION_ENV_VARS, *GIT_DISCOVERY_ENV_VARS])
def test_session_fixture_scrubs_git_variable(variable: str) -> None:
    """The autouse session fixture in tests/conftest.py removed each override."""
    assert variable not in os.environ


def test_no_git_config_override_survives() -> None:
    assert [key for key in os.environ if key.startswith("GIT_CONFIG")] == []


def test_strip_reports_and_removes(tmp_path: Path) -> None:
    environ = {
        "GIT_DIR": "/x/.git",
        "GIT_WORK_TREE": "/x",
        "GIT_CONFIG_GLOBAL": "/x/gitconfig",
        "PATH": "/usr/bin",
        "GIT_AUTHOR_NAME": "kept",
    }
    removed = strip_git_location_env(environ)

    assert set(removed) == {"GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG_GLOBAL"}
    # Identity and PATH must survive, or every committing fixture breaks.
    assert environ == {"PATH": "/usr/bin", "GIT_AUTHOR_NAME": "kept"}
