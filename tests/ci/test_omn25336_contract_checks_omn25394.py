# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The local-done-gate checks of contracts/OMN-25336.yaml can go red (OMN-25394, review findings 3 and 4).

Each test pulls the real ``python -c`` source out of the contract's check and runs it, so a change to
the contract changes what is tested. Findings: the registry import search read a git error with empty
stdout as clean and never fetched; ``onex scm pr-checks`` exits 0 on a red head, so a check that read its
exit status could not fail.
"""

from __future__ import annotations

import json
import shlex
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT = _REPO_ROOT / "contracts" / "OMN-25336.yaml"
_FORBIDDEN = "validate_ticket_contract"


def _check_source(entry_id: str) -> str:
    """The ``python -c`` program of the contract's check ``entry_id``."""
    entries = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))["dod_evidence"]
    (entry,) = [e for e in entries if e["id"] == entry_id]
    argv = shlex.split(entry["checks"][0]["check_value"])
    assert argv[:5] == ["uv", "run", "--locked", "python", "-c"], argv[:5]
    return argv[5]


_BASE_PATH = "/usr/local/bin:/usr/bin:/bin"


def _run(
    source: str, env: dict[str, str], path_prefix: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``source`` with an explicit environment (no process environment is read or inherited)."""
    path = _BASE_PATH if path_prefix is None else f"{path_prefix}:{_BASE_PATH}"
    return subprocess.run(
        [sys.executable, "-I", "-c", source],
        env={"PATH": path, "HOME": "/nonexistent", **env},
        capture_output=True,
        text=True,
        check=False,
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def _registry_repo(registry: Path, name: str, source: str, branch: str) -> Path:
    """A clone ``name`` under ``registry`` of a bare origin whose ``branch`` holds ``source``."""
    origin = registry.parent / "origins" / f"{name}.git"
    origin.mkdir(parents=True)
    _git(origin, "init", "-q", "--bare", f"--initial-branch={branch}")
    seed = registry.parent / "seeds" / name
    seed.mkdir(parents=True)
    _git(seed, "init", "-q", f"--initial-branch={branch}")
    (seed / "mod.py").write_text(source, encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", str(origin), branch)
    clone = registry / name
    _git(registry, "clone", "-q", str(origin), str(clone))
    return clone


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    home = tmp_path / "omni_home"
    home.mkdir()
    return home


def _search(registry: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        _check_source("dod-omn25336-ac10-registry-search"),
        {"OMNI_HOME": str(registry)},
    )


@pytest.mark.unit
def test_omn25336_import_search_a_clean_registry_reads_clean(registry: Path) -> None:
    """Positive control: a clone whose default branch holds no removed name passes."""
    _registry_repo(registry, "clean", "VALUE = 1\n", "dev")

    result = _search(registry)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.unit
def test_omn25336_import_search_finds_an_import_on_the_default_branch(
    registry: Path,
) -> None:
    _registry_repo(registry, "dirty", f"from x import {_FORBIDDEN}\n", "dev")

    result = _search(registry)

    assert result.returncode == 1
    assert "dirty" in result.stdout


@pytest.mark.unit
def test_omn25336_import_search_git_error_with_empty_stdout_is_not_clean(
    registry: Path,
) -> None:
    """Failing control: a clone whose origin/HEAD cannot be resolved is an error, not a clean read."""
    # a clone of an origin that holds no commit has no origin/HEAD to resolve and nothing to search
    origin = registry.parent / "origins" / "broken.git"
    origin.mkdir(parents=True)
    _git(origin, "init", "-q", "--bare", "--initial-branch=dev")
    _git(registry, "clone", "-q", str(origin), str(registry / "broken"))

    result = _search(registry)

    assert result.returncode != 0
    assert "broken" in result.stdout


@pytest.mark.unit
def test_omn25336_import_search_a_failed_fetch_is_not_clean(registry: Path) -> None:
    clone = _registry_repo(registry, "offline", "VALUE = 1\n", "dev")
    _git(clone, "remote", "set-url", "origin", str(registry / "no-such-origin.git"))

    result = _search(registry)

    assert result.returncode != 0
    assert "offline" in result.stdout


@pytest.mark.unit
def test_omn25336_import_search_fetches_before_it_searches(registry: Path) -> None:
    """Failing control: an import merged to the default branch after the clone was made is found."""
    clone = _registry_repo(registry, "stale", "VALUE = 1\n", "dev")
    origin = registry.parent / "origins" / "stale.git"
    pusher = registry.parent / "pusher"
    _git(registry.parent, "clone", "-q", str(origin), str(pusher))
    (pusher / "mod.py").write_text(f"from x import {_FORBIDDEN}\n", encoding="utf-8")
    _git(pusher, "commit", "-q", "-am", "import the removed name")
    _git(pusher, "push", "-q", "origin", "dev")
    assert clone.is_dir()

    result = _search(registry)

    assert result.returncode == 1
    assert "stale" in result.stdout


def _fake_onex(directory: Path, payload: dict[str, object]) -> Path:
    """An ``onex`` that prints ``payload`` and exits 0, as the real pr-checks does on a red head."""
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "onex"
    script.write_text(
        "#!/bin/sh\ncat <<'JSON'\n" + json.dumps(payload) + "\nJSON\nexit 0\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return directory


_HEAD = "a" * 40


def _checks(klass: str, red: list[str], head: str = _HEAD) -> dict[str, object]:
    return {
        "result": {
            "head_sha": head,
            "class": klass,
            "red": red,
            "pending": [],
            "read_at": "2026-11-17T15:00:00Z",
        }
    }


@pytest.mark.unit
def test_omn25336_import_search_pr_checks_check_goes_red_on_a_red_head_with_exit_0(
    tmp_path: Path,
) -> None:
    """Failing control: the tool exits 0 on a red head; the check must read the JSON, not the status."""
    source = _check_source("dod-omn25336-ac1-required-checks-at-head")
    red = _fake_onex(tmp_path / "red", _checks("red", ["CI Summary"]))
    green = _fake_onex(tmp_path / "green", _checks("green", []))

    assert _run(source, {}, red).returncode == 1
    assert _run(source, {}, green).returncode == 0


@pytest.mark.unit
def test_omn25336_import_search_pr_checks_check_refuses_a_read_with_no_full_head(
    tmp_path: Path,
) -> None:
    source = _check_source("dod-omn25336-ac1-required-checks-at-head")
    short = _fake_onex(tmp_path / "short", _checks("green", [], head="abc"))

    assert _run(source, {}, short).returncode == 1


@pytest.mark.unit
def test_omn25336_import_search_lab_comment_check_goes_red_on_a_head_the_clone_does_not_hold(
    tmp_path: Path,
) -> None:
    """The head the watcher reads must be the head of the PR's branch in the canonical clone."""
    home = tmp_path / "omni_home"
    clone = home / "omnibase_core"
    clone.mkdir(parents=True)
    _git(clone, "init", "-q")
    (clone / "f").write_text("x\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "c")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=clone,
        env=scrub_git_location_env(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    _git(clone, "update-ref", "refs/remotes/origin/the-branch", head)
    source = _check_source("dod-omn25336-ac11-lab-comment")

    def view(sha: str) -> dict[str, object]:
        return {"result": {"state": "OPEN", "head_ref": "the-branch", "head_sha": sha}}

    right = _fake_onex(tmp_path / "right", view(head))
    wrong = _fake_onex(tmp_path / "wrong", view("b" * 40))

    assert _run(source, {"OMNI_HOME": str(home)}, right).returncode == 0
    assert _run(source, {"OMNI_HOME": str(home)}, wrong).returncode == 1
