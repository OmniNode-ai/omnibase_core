# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The hook push rehearsal can give the pre-push set the sibling clones it reads (OMN-17427).

omnimarket's Topic Naming Lint pre-push hook runs omnibase_infra's
``scripts/validation/lint_topic_names.py`` and refuses the push when no sibling clone is found.
A worker has its siblings under OMNI_HOME; the rehearsal runner had only the caller's checkout,
so the rehearsal refused a push a worker would make. The ``sibling-repositories`` input names
repositories under the caller's owner to clone beside the workspace, each exported as
``<NAME>_PATH``; it defaults to empty, so other callers are unchanged.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

_ROOT = Path(__file__).resolve().parents[4]
_WORKFLOW = _ROOT / ".github" / "workflows" / "hook-push-rehearsal.yml"
_BASH = ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail"]
_SIBLINGS_STEP = "siblings"
_PUSH_STEP = "Install the pre-push hook and push a sample commit through it"
_STUB_GIT = """\
#!/bin/sh
echo "$*" >> "$GIT_CALLS"
if [ "$1" = clone ]; then
  for last; do :; done
  mkdir -p "$last"
  exit 0
fi
if [ "$1" = -C ]; then echo 0123456789abcdef0123456789abcdef01234567; fi
"""


def _workflow() -> dict[Any, Any]:
    loaded: dict[Any, Any] = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return loaded


def _steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = _workflow()["jobs"]["rehearse"]["steps"]
    return steps


def _step(key: str) -> dict[str, Any]:
    for step in _steps():
        if step.get("id") == key or step.get("name") == key:
            return step
    raise AssertionError(f"no step {key!r} in {_WORKFLOW}")


def _run_siblings_step(
    tmp_path: Path, repositories: str
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    workspace = tmp_path / "work" / "omnimarket"
    workspace.mkdir(parents=True)
    github_env = tmp_path / "github_env"
    github_env.write_text("", encoding="utf-8")
    calls = tmp_path / "git_calls"
    calls.write_text("", encoding="utf-8")
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    git = stub_bin / "git"
    git.write_text(_STUB_GIT, encoding="utf-8")
    git.chmod(git.stat().st_mode | stat.S_IXUSR)
    ambient = scrub_git_location_env()
    done = subprocess.run(
        [*_BASH, "-c", str(_step(_SIBLINGS_STEP)["run"])],
        cwd=workspace,
        env={
            **ambient,
            "PATH": f"{stub_bin}:{ambient['PATH']}",
            "GITHUB_WORKSPACE": str(workspace),
            "GITHUB_ENV": str(github_env),
            "GITHUB_SERVER_URL": "https://git.example.invalid",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GIT_CALLS": str(calls),
            "SIBLING_REPOSITORIES": repositories,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return done, tmp_path / "work", github_env, calls


def test_the_input_is_an_optional_string_that_defaults_to_none() -> None:
    workflow = _workflow()
    trigger = workflow.get("on") or workflow[True]  # YAML 1.1 reads `on` as True
    spec = trigger["workflow_call"]["inputs"]["sibling-repositories"]
    assert spec["type"] == "string"
    assert spec["required"] is False
    assert spec["default"] == ""


def test_the_siblings_step_is_gated_on_the_input_and_a_hook_change_and_precedes_the_push() -> (
    None
):
    siblings = _step(_SIBLINGS_STEP)
    condition = str(siblings["if"])
    assert "steps.detect.outputs.touched == 'true'" in condition
    assert "inputs.sibling-repositories != ''" in condition
    assert siblings["env"]["SIBLING_REPOSITORIES"] == (
        "${{ inputs.sibling-repositories }}"
    )
    names = [step.get("id") or step.get("name") for step in _steps()]
    assert names.index(_SIBLINGS_STEP) < names.index(_PUSH_STEP)
    # The push stays gated on the hook change alone, so a caller that names no sibling pushes
    # exactly as before.
    assert "sibling-repositories" not in str(_step(_PUSH_STEP)["if"])


def test_each_sibling_is_cloned_beside_the_workspace_and_exported_as_its_path(
    tmp_path: Path,
) -> None:
    done, parent, github_env, calls = _run_siblings_step(
        tmp_path, "omnibase_infra other.repo"
    )
    assert done.returncode == 0, done.stdout + done.stderr
    cloned = calls.read_text(encoding="utf-8")
    assert "https://git.example.invalid/owner/omnibase_infra.git" in cloned
    assert "https://git.example.invalid/owner/other.repo.git" in cloned
    assert (parent / "omnibase_infra").is_dir()
    exported = github_env.read_text(encoding="utf-8").splitlines()
    assert f"OMNIBASE_INFRA_PATH={parent / 'omnibase_infra'}" in exported
    assert f"OTHER_REPO_PATH={parent / 'other.repo'}" in exported


def test_an_entry_that_is_not_a_repository_name_is_refused(tmp_path: Path) -> None:
    done, _, github_env, calls = _run_siblings_step(tmp_path, "../escape/x")
    assert done.returncode == 1
    assert "is not a repository name" in done.stdout
    assert calls.read_text(encoding="utf-8") == ""
    assert github_env.read_text(encoding="utf-8") == ""
