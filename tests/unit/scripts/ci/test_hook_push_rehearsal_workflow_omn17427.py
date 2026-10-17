# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The hook push rehearsal workflow judges a hook change the way a controller worker's push does (OMN-17427).

The workflow's two run steps are executed as written, in a throwaway repository with a bare
remote, with a stub ``uv`` that points at the test environment's own ``pre-commit``.
"""

from __future__ import annotations

import shutil
import stat
import subprocess
import sys
from pathlib import Path

import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

_ROOT = Path(__file__).resolve().parents[4]
_WORKFLOW = _ROOT / ".github" / "workflows" / "hook-push-rehearsal.yml"
_BASH = ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail"]

_BASE_CONFIG = """\
repos:
  - repo: local
    hooks:
      - id: sample
        name: sample
        entry: bash -c 'true'
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
"""


def _config(entry: str) -> str:
    return _BASE_CONFIG.replace("bash -c 'true'", entry)


def _steps() -> dict[str, str]:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return {
        step["id"] if "id" in step else step["name"]: step["run"]
        for step in workflow["jobs"]["rehearse"]["steps"]
        if "run" in step
    }


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={
            **scrub_git_location_env(),
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )
    return done.stdout.strip()


class _Rehearsal:
    """A repository whose pull request head carries ``config`` as its hook config."""

    def __init__(
        self, tmp_path: Path, config: str, changed: str = ".pre-commit-config.yaml"
    ) -> None:
        self.work = tmp_path / "work"
        self.work.mkdir()
        self.runner_temp = tmp_path / "runner"
        self.runner_temp.mkdir()
        self.output = tmp_path / "github_output"
        self.output.write_text("", encoding="utf-8")
        stub_bin = tmp_path / "bin"
        stub_bin.mkdir()
        pre_commit = shutil.which("pre-commit", path=str(Path(sys.executable).parent))
        assert pre_commit, "pre-commit is a dev dependency of this repository"
        self.tool_bin = Path(pre_commit).parent
        uv = stub_bin / "uv"
        uv.write_text(
            '#!/bin/sh\nif [ "$1 $2 $3" = "tool dir --bin" ]; then echo "$TOOL_BIN"; fi\n',
            encoding="utf-8",
        )
        uv.chmod(uv.stat().st_mode | stat.S_IXUSR)
        self.stub_bin = stub_bin

        _git(self.work, "init", "-q", "-b", "main")
        (self.work / "src").mkdir()
        (self.work / "src" / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.work / ".pre-commit-config.yaml").write_text(
            _BASE_CONFIG, encoding="utf-8"
        )
        (self.work / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        _git(self.work, "add", "-A")
        _git(self.work, "commit", "-q", "-m", "base")
        self.base = _git(self.work, "rev-parse", "HEAD")
        (self.work / changed).parent.mkdir(parents=True, exist_ok=True)
        (self.work / changed).write_text(config, encoding="utf-8")
        _git(self.work, "add", "-A")
        _git(self.work, "commit", "-q", "-m", "pull request head")
        self.head = _git(self.work, "rev-parse", "HEAD")

    def env(self, event: str, **extra: str) -> dict[str, str]:
        ambient = scrub_git_location_env()
        return {
            **ambient,
            "PATH": f"{self.stub_bin}:{ambient['PATH']}",
            "TOOL_BIN": str(self.tool_bin),
            "RUNNER_TEMP": str(self.runner_temp),
            "GITHUB_OUTPUT": str(self.output),
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
            "EVENT_NAME": event,
            "BASE_SHA": self.base,
            "HEAD_SHA": self.head,
            "PATH_REGEX": r"^(\.pre-commit-config\.yaml|scripts/hooks/)",
            "SAMPLE_FILE": "src/mod.py",
            "PUSH_TIMEOUT_S": "1800",
            **extra,
        }

    def run(self, step: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*_BASH, "-c", _steps()[step]],
            cwd=self.work,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=240,
        )

    def touched(self, event: str = "pull_request") -> bool:
        done = self.run("detect", self.env(event))
        assert done.returncode == 0, done.stderr
        return "touched=true" in self.output.read_text(encoding="utf-8")

    def rehearse(self, **extra: str) -> subprocess.CompletedProcess[str]:
        return self.run(
            "Install the pre-push hook and push a sample commit through it",
            self.env("pull_request", **extra),
        )


def test_workflow_declares_the_worker_push_environment_and_timeout() -> None:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    trigger = (
        workflow.get("on") or workflow[True]
    )  # YAML 1.1 reads the key `on` as True
    text = _steps()["Install the pre-push hook and push a sample commit through it"]
    assert "export PYTHONDONTWRITEBYTECODE=1" in text
    assert "unset PYTHONPATH" in text
    assert "pre-commit install -t pre-push" in text
    assert (
        trigger["workflow_call"]["inputs"]["push-timeout-seconds"]["default"] == "1800"
    )


def test_a_pull_request_that_changes_no_hook_path_does_not_rehearse(
    tmp_path: Path,
) -> None:
    run = _Rehearsal(tmp_path, _BASE_CONFIG, changed="docs/notes.md")
    assert run.touched() is False


def test_a_hook_path_change_rehearses_on_a_pull_request_only(tmp_path: Path) -> None:
    run = _Rehearsal(tmp_path, _config("bash -c ':'"))
    assert run.touched() is True
    run.output.write_text("", encoding="utf-8")
    assert run.touched(event="merge_group") is False


def test_a_hook_set_that_accepts_the_push_passes_and_sees_the_worker_environment(
    tmp_path: Path,
) -> None:
    entry = (
        'bash -c \'test "$PYTHONDONTWRITEBYTECODE" = 1 && test -z "${PYTHONPATH:-}"\''
    )
    run = _Rehearsal(tmp_path, _config(entry))
    done = run.rehearse(PYTHONPATH="/should/be/unset")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "would be accepted" in done.stdout


def test_a_hook_that_refuses_the_push_fails_the_rehearsal(tmp_path: Path) -> None:
    run = _Rehearsal(tmp_path, _config("bash -c 'exit 1'"))
    done = run.rehearse()
    assert done.returncode == 1
    assert "would be refused" in done.stdout


def test_a_pre_push_set_past_the_timeout_fails_the_rehearsal(tmp_path: Path) -> None:
    run = _Rehearsal(tmp_path, _config("bash -c 'sleep 60'"))
    done = run.rehearse(PUSH_TIMEOUT_S="3")
    assert done.returncode == 1
    assert "ran past the 3s push timeout" in done.stdout


def test_a_hook_that_leaves_a_file_in_the_tree_fails_the_rehearsal(
    tmp_path: Path,
) -> None:
    run = _Rehearsal(
        tmp_path, _config("bash -c 'mkdir -p stray && touch stray/left.txt'")
    )
    done = run.rehearse()
    assert done.returncode == 1
    assert "left files in the work tree" in done.stdout
    assert "stray/left.txt" in done.stdout


def test_a_sample_file_that_is_not_tracked_fails_loudly(tmp_path: Path) -> None:
    run = _Rehearsal(tmp_path, _config("bash -c ':'"))
    done = run.rehearse(SAMPLE_FILE="src/missing.py")
    assert done.returncode == 1
    assert "is not a tracked file" in done.stdout
