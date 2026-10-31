# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21676: the receipt gate installs its verifier from an omnimarket dev-merge tag.

Operator ruling 2026-10-31, extending the ruling of 2026-10-29T01:50:26Z "we
iterate with tags, not with releases": the repo-evidence gate takes its
omnimarket verifier from the dev-merge tag a caller names, resolved to a
commit that is recorded in the receipt, with the floor an ancestry fact. These
tests execute the install step's own script against a throwaway git remote that
stands in for omnimarket (a stub uv records what would be installed), and plant
every refusal: a malformed tag, an absent tag, a tag moved to another commit,
a commit that does not descend from the floor commit and a commit that is not
on the dev branch.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
VERIFIER_STEP = "Install the pinned verifier"
# omnimarket#3511's squash commit starts with this prefix; it is the first
# commit carrying the refusal of a contract that leaves an acceptance
# criterion unbound.
REFUSAL_COMMIT_PREFIX = "e565ba5"
STAMP = "20261031120000"


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _verifier_step() -> dict[str, Any]:
    steps = _workflow()["jobs"]["dod-verify"]["steps"]
    return next(step for step in steps if step.get("name") == VERIFIER_STEP)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(repo.parent),
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class Remote:
    """A throwaway stand-in for the omnimarket remote."""

    path: Path
    before_floor: str
    floor: str
    on_dev: str
    newest_on_dev: str
    off_dev: str

    def tag_for(self, sha: str) -> str:
        return f"dev-{STAMP}-{sha[:12]}"


@pytest.fixture
def remote(tmp_path: Path) -> Remote:
    path = tmp_path / "omnimarket"
    path.mkdir()
    _git(path, "init", "--quiet", "-b", "dev")
    _git(path, "config", "uploadpack.allowFilter", "true")

    def commit(name: str) -> str:
        (path / "f.txt").write_text(name)
        _git(path, "add", "f.txt")
        _git(path, "commit", "--quiet", "-m", name)
        return _git(path, "rev-parse", "HEAD")

    before_floor = commit("before the floor")
    floor = commit("the floor")
    on_dev = commit("after the floor")
    newest_on_dev = commit("newest on dev")
    # A commit that descends from the floor but never reached dev.
    _git(path, "checkout", "--quiet", "-b", "side", on_dev)
    off_dev = commit("only on a side branch")
    _git(path, "checkout", "--quiet", "dev")
    _git(path, "branch", "-D", "side")
    # The side commit stays reachable through its tag, as a pushed tag would.
    result = Remote(path, before_floor, floor, on_dev, newest_on_dev, off_dev)
    for sha in (before_floor, floor, on_dev, newest_on_dev, off_dev):
        _git(path, "tag", result.tag_for(sha), sha)
    return result


def _run_step(
    tmp_path: Path, remote: Remote, tag: str, *, version: str = "0.4.305"
) -> tuple[int, str, Path, Path]:
    """Run the step's script with a stub uv; return the code, output, uv log, temp."""
    step = _verifier_step()
    run_dir = tmp_path / "run"
    bin_dir = run_dir / "bin"
    bin_dir.mkdir(parents=True)
    uv_log = run_dir / "uv.log"
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s UV_PROJECT_ENVIRONMENT=%s\\n" "$*" "${{UV_PROJECT_ENVIRONMENT:-}}" >> "{uv_log}"\n'
        'if [ "$1" = venv ]; then\n'
        '  dir="${@: -1}"\n'
        '  mkdir -p "$dir/bin"\n'
        "  printf '#!/usr/bin/env bash\\nexit 0\\n' > \"$dir/bin/python\"\n"
        '  chmod +x "$dir/bin/python"\n'
        "fi\n"
    )
    stub.chmod(0o755)
    workspace = run_dir / "workspace"
    workspace.mkdir()
    runner_temp = run_dir / "runner_temp"
    runner_temp.mkdir()
    github_env = run_dir / "github_env"
    github_env.write_text("")
    github_output = run_dir / "github_output"
    github_output.write_text("")
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(run_dir),
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_ENV": str(github_env),
        "GITHUB_OUTPUT": str(github_output),
        "RUNNER_TEMP": str(runner_temp),
        **{key: str(value) for key, value in step["env"].items()},
        "VERIFIER_TAG": tag,
        "VERIFIER_VERSION": version,
        "VERIFIER_FLOOR_SHA": remote.floor,
        "VERIFIER_REPO_URL": remote.path.as_uri(),
    }
    result = subprocess.run(
        [shutil.which("bash") or "bash", "-c", step["run"]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr, uv_log, run_dir


def test_the_tag_is_a_declared_input_that_defaults_to_the_fallback() -> None:
    workflow = _workflow()
    # PyYAML interprets the YAML 1.1 `on` key as True.
    trigger = workflow.get(True, workflow.get("on"))
    inputs = trigger["workflow_call"]["inputs"]
    assert inputs["verifier-tag"]["default"] == ""
    assert inputs["verifier-tag"]["type"] == "string"
    assert inputs["verifier-tag"]["required"] is False
    # The version input stays, as the migration fallback.
    assert "verifier-version" in inputs
    assert "fallback" in inputs["verifier-version"]["description"].lower()
    assert _verifier_step()["env"]["VERIFIER_TAG"] == "${{ inputs.verifier-tag }}"


def test_the_floor_commit_is_declared_once_and_is_the_refusal_commit() -> None:
    step = _verifier_step()
    floor = step["env"]["VERIFIER_FLOOR_SHA"]
    assert len(floor) == 40
    assert floor.startswith(REFUSAL_COMMIT_PREFIX)
    lines = [
        line
        for line in WORKFLOW_PATH.read_text().splitlines()
        if "VERIFIER_FLOOR_SHA:" in line
    ]
    assert len(lines) == 1, lines
    assert step["env"]["VERIFIER_REPO_URL"] == (
        "${{ github.server_url }}/OmniNode-ai/omnimarket.git"
    )
    assert step["env"]["VERIFIER_BRANCH"] == "dev"


@pytest.mark.parametrize("which", ["on_dev", "newest_on_dev"])
def test_a_tag_after_the_floor_is_installed_from_its_resolved_commit(
    tmp_path: Path, remote: Remote, which: str
) -> None:
    sha = getattr(remote, which)
    tag = remote.tag_for(sha)
    returncode, output, uv_log, run_dir = _run_step(tmp_path, remote, tag)
    assert returncode == 0, output
    calls = uv_log.read_text()
    src = run_dir / "workspace" / ".dod-verify" / "verifier-src"
    assert f"sync --project {src} --frozen --no-dev --no-editable --no-config" in calls
    assert f"UV_PROJECT_ENVIRONMENT={run_dir}/workspace/.dod-verify/venv" in calls
    assert "omnimarket==" not in calls, "the tag path installs no released version"
    # The checkout the verifier is installed from is exactly the resolved commit.
    assert _git(src, "rev-parse", "HEAD") == sha
    receipt = (run_dir / "runner_temp" / "dod" / "verifier-commit.txt").read_text()
    assert f"tag={tag} commit={sha} floor_commit={remote.floor}" in receipt
    outputs = (run_dir / "github_output").read_text()
    assert f"verifier_tag={tag}" in outputs
    assert f"verifier_commit={sha}" in outputs
    assert "DOD_VERIFY_PY=" in (run_dir / "github_env").read_text()


def test_the_floor_commit_itself_is_admitted(tmp_path: Path, remote: Remote) -> None:
    returncode, output, uv_log, _ = _run_step(
        tmp_path, remote, remote.tag_for(remote.floor)
    )
    assert returncode == 0, output
    assert "sync" in uv_log.read_text()


def test_an_annotated_tag_is_resolved_to_its_peeled_commit(
    tmp_path: Path, remote: Remote
) -> None:
    tag = f"dev-{STAMP}-{remote.newest_on_dev[:12]}"
    _git(remote.path, "tag", "-d", tag)
    _git(remote.path, "tag", "-a", "-m", "annotated", tag, remote.newest_on_dev)
    returncode, output, _, run_dir = _run_step(tmp_path, remote, tag)
    assert returncode == 0, output
    receipt = (run_dir / "runner_temp" / "dod" / "verifier-commit.txt").read_text()
    assert f"commit={remote.newest_on_dev} " in receipt


def test_a_tag_whose_commit_is_before_the_floor_is_refused(
    tmp_path: Path, remote: Remote
) -> None:
    returncode, output, uv_log, _ = _run_step(
        tmp_path, remote, remote.tag_for(remote.before_floor)
    )
    assert returncode == 1, output
    assert "does not descend from the floor commit" in output
    assert not uv_log.exists(), "nothing may be installed below the floor"


def test_a_tag_whose_commit_is_not_on_dev_is_refused(
    tmp_path: Path, remote: Remote
) -> None:
    returncode, output, uv_log, _ = _run_step(
        tmp_path, remote, remote.tag_for(remote.off_dev)
    )
    assert returncode == 1, output
    assert "is not reachable from the omnimarket dev branch" in output
    assert not uv_log.exists()


def test_a_tag_moved_to_another_commit_is_refused(
    tmp_path: Path, remote: Remote
) -> None:
    # The name still carries the older commit's sha12, but the tag now names
    # the newest commit: the immutable identity no longer holds.
    tag = remote.tag_for(remote.on_dev)
    _git(remote.path, "tag", "-f", tag, remote.newest_on_dev)
    returncode, output, uv_log, _ = _run_step(tmp_path, remote, tag)
    assert returncode == 1, output
    assert "the tag was moved, refusing it" in output
    assert not uv_log.exists()


def test_an_absent_tag_is_refused(tmp_path: Path, remote: Remote) -> None:
    returncode, output, uv_log, _ = _run_step(
        tmp_path, remote, f"dev-{STAMP}-{'0' * 12}"
    )
    assert returncode == 1, output
    assert "is absent from" in output
    assert not uv_log.exists()


@pytest.mark.parametrize(
    "tag",
    [
        "v0.4.321",
        "main",
        "dev-2026103112000-abcdefabcdef",
        "dev-20261031120000-ABCDEFABCDEF",
        "dev-20261031120000-abcdef",
        "dev-20261031120000-abcdefabcdef/../x",
        "refs/tags/dev-20261031120000-abcdefabcdef",
    ],
)
def test_a_value_that_is_not_a_dev_merge_tag_is_refused(
    tmp_path: Path, remote: Remote, tag: str
) -> None:
    returncode, output, uv_log, _ = _run_step(tmp_path, remote, tag)
    assert returncode == 1, output
    assert "must be an omnimarket dev-merge tag" in output
    assert not uv_log.exists()


def test_the_version_is_ignored_when_a_tag_is_set(
    tmp_path: Path, remote: Remote
) -> None:
    # A version below the old floor would be refused on the fallback path.
    returncode, output, uv_log, _ = _run_step(
        tmp_path, remote, remote.tag_for(remote.newest_on_dev), version="0.3.1"
    )
    assert returncode == 0, output
    assert "verifier-version 0.3.1 is ignored" in output
    assert "omnimarket==" not in uv_log.read_text()


def test_an_empty_tag_keeps_the_version_fallback_working(
    tmp_path: Path, remote: Remote
) -> None:
    returncode, output, uv_log, _ = _run_step(tmp_path, remote, "", version="0.4.305")
    assert returncode == 0, output
    assert "omnimarket==0.4.305" in uv_log.read_text()
    assert "verifier-version is the migration fallback" in output


def test_the_summary_records_the_tag_and_the_resolved_commit() -> None:
    summary = next(
        step
        for step in _workflow()["jobs"]["dod-verify"]["steps"]
        if step.get("name") == "Summarise"
    )
    assert summary["env"]["VERIFIER_TAG"] == "${{ inputs.verifier-tag }}"
    assert "Verifier tag: %s" in summary["run"]
    assert "verifier-commit.txt" in summary["run"]
