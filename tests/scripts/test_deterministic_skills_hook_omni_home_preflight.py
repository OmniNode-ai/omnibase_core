# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMNI_HOME fail-fast preflight for the deterministic-skill-routing hook (OMN-17167).

``scripts/pre_commit_validate_deterministic_skills.sh`` resolves an ``omniclaude``
sibling clone. Reported by a contractor 2026-08-30: with a stale or unset
``OMNI_HOME`` the hook failed with a generic "skills root not found" line that
never printed the ``$OMNI_HOME``-derived path it actually probed, so a STALE
OMNI_HOME (set, wrong directory) was byte-indistinguishable from an UNSET one.

Doctrine under test: omni_home CLAUDE.md rule 8 (fail fast on missing env, never
a silent default), rule 6 (no absolute paths -- the remediation is an ``export``
line), and memory ``feedback_own_errors_give_full_paths`` (name the variable AND
the full missing path).

These tests drive THE real hook script end-to-end via subprocess from an isolated
tmp cwd where no sibling can resolve, with a stubbed ``uv`` on PATH so the passing
case proves resolution without running the real gate -- the same harness shape as
``tests/scripts/test_prepush_hook_host_identity_guard.py``. Git env vars are
stripped from the child per the OMN-14746/14744 worktree-safety lesson.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_SCRIPT = REPO_ROOT / "scripts" / "pre_commit_validate_deterministic_skills.sh"

# The literal remediation the operator must be able to copy. Asserting on its
# PRESENCE (not merely a non-zero exit) is the point of the ticket: an opaque
# non-zero exit is the defect, not the fix.
_UNSET_MESSAGE = "OMNI_HOME is not set."
_SIBLING_LAYOUT = "It must be the directory containing the sibling clones (omniclaude)."
_EXPORT_EXAMPLE = "export OMNI_HOME=$HOME/omninode"
_STALE_MESSAGE = "OMNI_HOME is set to"

_STUB_UV = """#!/usr/bin/env bash
echo "STUB_UV_INVOKED $*"
exit 0
"""


def _clean_env(stub_bin: Path) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "OMNI_HOME",
            "DETERMINISTIC_SKILL_ROOT",
            "GIT_DIR",
            "GIT_INDEX_FILE",
            "GIT_WORK_TREE",
        }
    }
    env["PATH"] = f"{stub_bin}{os.pathsep}{env.get('PATH', '')}"
    return env


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    """A PATH entry whose ``uv`` records its argv instead of running the gate."""
    bin_dir = tmp_path / "stub_bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(_STUB_UV)
    stub.chmod(0o755)
    return bin_dir


@pytest.fixture
def isolated_hook(tmp_path: Path) -> Path:
    """The real hook, copied where NO sibling candidate can resolve.

    ``_external/omniclaude/...`` and ``../omniclaude/...`` are both relative to the
    cwd, so the isolated tree is deliberately nested one level down with no
    ``omniclaude`` anywhere above it.
    """
    workdir = tmp_path / "isolated" / "scripts"
    workdir.mkdir(parents=True)
    dest = workdir / HOOK_SCRIPT.name
    shutil.copy2(HOOK_SCRIPT, dest)
    dest.chmod(0o755)
    return dest


def _run(
    hook: Path, env: dict[str, str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(hook)],
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.unit
def test_hook_script_exists_and_is_executable() -> None:
    assert HOOK_SCRIPT.is_file(), f"missing hook script: {HOOK_SCRIPT}"
    assert os.access(HOOK_SCRIPT, os.X_OK), "hook script must be executable"


@pytest.mark.unit
def test_no_hardcoded_absolute_paths() -> None:
    """Rule #6: the remediation is an ``export`` line, never a machine path."""
    text = HOOK_SCRIPT.read_text()
    for prefix in ("/" + "Users/", "/" + "Volumes/"):
        assert prefix not in text, f"hardcoded local absolute path in hook: {prefix}"


@pytest.mark.unit
def test_unset_omni_home_names_the_variable_and_the_expected_layout(
    isolated_hook: Path, stub_bin: Path
) -> None:
    """UNSET -> exit 2, naming the variable, the layout, and a copyable export."""
    result = _run(isolated_hook, _clean_env(stub_bin), isolated_hook.parent.parent)

    assert result.returncode == 2, (
        f"expected exit 2 on unset OMNI_HOME, got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert _UNSET_MESSAGE in result.stderr, (
        f"stderr must name the unset variable; got:\n{result.stderr}"
    )
    assert _SIBLING_LAYOUT in result.stderr, (
        f"stderr must state what OMNI_HOME points at; got:\n{result.stderr}"
    )
    assert _EXPORT_EXAMPLE in result.stderr, (
        f"stderr must carry the copyable export example; got:\n{result.stderr}"
    )
    assert "STUB_UV_INVOKED" not in result.stdout, (
        "the gate must not run when its skills root cannot be resolved"
    )


@pytest.mark.unit
def test_stale_omni_home_prints_the_full_missing_path(
    isolated_hook: Path, stub_bin: Path, tmp_path: Path
) -> None:
    """STALE -> exit 2 naming the FULL expanded missing path AND the variable.

    This is the case the pre-OMN-17167 hook could not express: it emitted the same
    generic line as the unset case, so the operator could not tell that OMNI_HOME
    was set-but-wrong.
    """
    stale_root = tmp_path / "stale_registry"
    stale_root.mkdir()
    env = _clean_env(stub_bin)
    env["OMNI_HOME"] = str(stale_root)

    result = _run(isolated_hook, env, isolated_hook.parent.parent)

    expected_missing = str(stale_root / "omniclaude" / "plugins" / "onex" / "skills")
    assert result.returncode == 2, (
        f"expected exit 2 on stale OMNI_HOME, got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert expected_missing in result.stderr, (
        f"stderr must print the full expanded missing path {expected_missing!r}; "
        f"got:\n{result.stderr}"
    )
    assert _STALE_MESSAGE in result.stderr, (
        f"stderr must say OMNI_HOME is set (not unset); got:\n{result.stderr}"
    )
    assert _UNSET_MESSAGE not in result.stderr, (
        "a stale OMNI_HOME must not be reported as unset -- that is the reported "
        f"defect; got:\n{result.stderr}"
    )
    assert _EXPORT_EXAMPLE in result.stderr, (
        f"stderr must carry the copyable export example; got:\n{result.stderr}"
    )


@pytest.mark.unit
def test_correct_omni_home_resolves_and_does_not_preflight_fail(
    isolated_hook: Path, stub_bin: Path, tmp_path: Path
) -> None:
    """CORRECT -> the preflight stays silent and the gate runs against the sibling."""
    registry = tmp_path / "registry"
    skills = registry / "omniclaude" / "plugins" / "onex" / "skills"
    skills.mkdir(parents=True)
    env = _clean_env(stub_bin)
    env["OMNI_HOME"] = str(registry)

    result = _run(isolated_hook, env, isolated_hook.parent.parent)

    assert result.returncode == 0, (
        f"expected the gate to run, got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert _UNSET_MESSAGE not in result.stderr
    assert _STALE_MESSAGE not in result.stderr
    assert "STUB_UV_INVOKED" in result.stdout, (
        f"the gate must actually be invoked; got stdout:\n{result.stdout}"
    )
    assert str(skills) in result.stdout, (
        f"--skills-root must resolve to the OMNI_HOME sibling; got:\n{result.stdout}"
    )
