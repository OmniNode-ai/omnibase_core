# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19998 - every push to dev gets a lightweight dev-<UTC>-<sha12> tag.

omnibase_core is a sibling consumed by omnibase_spi, omnibase_infra,
omnimarket, omniintelligence, omnimemory and omniclaude; a consumer can pin
a dev-* tag through a uv git source instead of waiting for a PyPI release.
The tag must appear on every dev merge without anyone remembering to cut it,
so it is a workflow on ``push`` to ``dev`` and nothing else: no tag on main,
on a pull request branch or on any other ref.

These tests run the workflow's own tag step, extracted from the YAML, against
a throwaway repository and a local bare remote. They prove the name
(``dev-<committer time in UTC, YYYYMMDDHHMMSS>-<first 12 hex of the sha>``),
that the tag is lightweight and points at the commit, that a second run for
the same commit pushes nothing, and that a dry run pushes nothing.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "dev-merge-tag.yml"
REUSABLE = REPO_ROOT / ".github" / "workflows" / "dev-merge-tag-reusable.yml"
JOB_ID = "dev-merge-tag"
STEP_NAME = "Create the dev merge tag"
TAG_PATTERN = re.compile(r"^dev-[0-9]{14}-[0-9a-f]{12}$")
# +05:30 is 09:34:05 UTC: a name built from local time instead of UTC differs.
FIXTURE_DATE = "2026-10-16T15:04:05+05:30"


def _workflow(path: Path = WORKFLOW) -> dict[Any, Any]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict), f"{path.name} must parse as a mapping"
    return parsed


def _triggers(workflow: dict[Any, Any]) -> dict[str, Any]:
    # PyYAML reads the bare key `on` as the boolean True.
    triggers = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, dict), f"{WORKFLOW.name} has no `on:` mapping"
    return triggers


def _tag_script() -> str:
    steps = _workflow(REUSABLE)["jobs"][JOB_ID]["steps"]
    matches = [step for step in steps if step.get("name") == STEP_NAME]
    assert len(matches) == 1, f"expected one step named {STEP_NAME!r}"
    script = matches[0]["run"]
    assert isinstance(script, str)
    return script


def _git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> str:
    if env is None:
        env = _git_env(FIXTURE_DATE)
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=scrub_git_location_env(env),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_env(committer_date: str) -> dict[str, str]:
    # Built from nothing rather than copied from the process environment: the
    # fixture needs only a PATH that reaches git and bash (OMN-17744 boundary).
    git = shutil.which("git")
    assert git is not None, "git must be on PATH"
    env = {"PATH": os.pathsep.join([str(Path(git).parent), os.defpath])}
    env.update(
        {
            "GIT_AUTHOR_NAME": "dev-merge-tag test",
            "GIT_AUTHOR_EMAIL": "dev-merge-tag@example.invalid",
            "GIT_COMMITTER_NAME": "dev-merge-tag test",
            "GIT_COMMITTER_EMAIL": "dev-merge-tag@example.invalid",
            "GIT_AUTHOR_DATE": committer_date,
            "GIT_COMMITTER_DATE": committer_date,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        }
    )
    return env


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path, str]:
    """A clone with one commit on dev, its bare origin, and that commit's sha.

    The committer date carries a +05:30 offset, so a name built from local time
    instead of UTC differs from the expected one.
    """
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    env = _git_env(FIXTURE_DATE)
    _git(tmp_path, "init", "--bare", "-q", str(origin), env=env)
    _git(tmp_path, "init", "-q", "-b", "dev", str(work), env=env)
    (work / "README").write_text("dev merge tag fixture\n", encoding="utf-8")
    _git(work, "add", "README", env=env)
    _git(work, "commit", "-q", "-m", "fixture", env=env)
    _git(work, "remote", "add", "origin", str(origin), env=env)
    _git(work, "push", "-q", "origin", "dev", env=env)
    sha = _git(work, "rev-parse", "HEAD", env=env)
    return work, origin, sha


def _run_step(
    work: Path, sha: str, *, dry_run: str, output: Path
) -> subprocess.CompletedProcess[str]:
    env = _git_env(FIXTURE_DATE)
    env.update(
        {
            "SHA": sha,
            "DRY_RUN": dry_run,
            "GITHUB_OUTPUT": str(output),
            "TZ": "Asia/Kolkata",
        }
    )
    return subprocess.run(
        ["bash", "-c", _tag_script()],
        cwd=work,
        env=scrub_git_location_env(env),
        capture_output=True,
        text=True,
        check=False,
    )


def _remote_tags(origin: Path) -> dict[str, str]:
    listing = _git(
        origin,
        "for-each-ref",
        "--format=%(refname:short) %(objecttype) %(objectname)",
        "refs/tags",
    )
    tags: dict[str, str] = {}
    for line in listing.splitlines():
        name, objecttype, objectname = line.split()
        assert objecttype == "commit", (
            f"{name} is a {objecttype}, not a lightweight tag"
        )
        tags[name] = objectname
    return tags


def _outputs(output: Path) -> dict[str, str]:
    pairs = (
        line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
    )
    return dict(pairs)


def test_workflow_runs_only_on_push_to_dev() -> None:
    workflow = _workflow()
    triggers = _triggers(workflow)
    assert set(triggers) == {"push"}, (
        f"triggers must be push only, got {sorted(triggers)}"
    )
    push = triggers["push"]
    assert push == {"branches": ["dev"]}, f"push must filter to dev only, got {push!r}"
    job = workflow["jobs"][JOB_ID]
    assert job["if"] == "github.ref == 'refs/heads/dev'"
    assert job["permissions"] == {"contents": "write"}
    assert job["uses"] == "./.github/workflows/dev-merge-tag-reusable.yml"
    concurrency = workflow["concurrency"]
    assert concurrency["cancel-in-progress"] is False


def test_reusable_is_called_only_and_repeats_the_dev_check() -> None:
    reusable = _workflow(REUSABLE)
    triggers = reusable.get("on", reusable.get(True))
    assert triggers == {"workflow_call": None}, (
        f"the reusable must be workflow_call only, got {triggers!r}"
    )
    job = reusable["jobs"][JOB_ID]
    assert job["if"] == "github.ref == 'refs/heads/dev'"
    assert job["permissions"] == {"contents": "write"}


def test_tag_name_is_dev_utc_committer_time_and_sha12(
    repo: tuple[Path, Path, str], tmp_path: Path
) -> None:
    work, origin, sha = repo
    output = tmp_path / "out"
    result = _run_step(work, sha, dry_run="false", output=output)
    assert result.returncode == 0, result.stderr + result.stdout

    expected = f"dev-20261016093405-{sha[:12]}"
    assert TAG_PATTERN.match(expected)
    assert _remote_tags(origin) == {expected: sha}
    assert _outputs(output) == {"tag": expected, "created": "true"}


def test_second_run_for_the_same_commit_pushes_nothing(
    repo: tuple[Path, Path, str], tmp_path: Path
) -> None:
    work, origin, sha = repo
    first = _run_step(work, sha, dry_run="false", output=tmp_path / "first")
    assert first.returncode == 0, first.stderr + first.stdout
    tags_after_first = _remote_tags(origin)

    _git(work, "tag", "-d", next(iter(tags_after_first)))
    second_output = tmp_path / "second"
    second = _run_step(work, sha, dry_run="false", output=second_output)
    assert second.returncode == 0, second.stderr + second.stdout
    assert _remote_tags(origin) == tags_after_first
    assert _outputs(second_output) == {
        "tag": next(iter(tags_after_first)),
        "created": "false",
    }


def test_an_existing_dev_tag_for_the_sha_under_another_stamp_is_reused(
    repo: tuple[Path, Path, str], tmp_path: Path
) -> None:
    work, origin, sha = repo
    earlier = f"dev-20261016000000-{sha[:12]}"
    _git(work, "tag", earlier, sha)
    _git(work, "push", "-q", "origin", f"refs/tags/{earlier}")
    output = tmp_path / "out"
    result = _run_step(work, sha, dry_run="false", output=output)
    assert result.returncode == 0, result.stderr + result.stdout
    assert _remote_tags(origin) == {earlier: sha}
    assert _outputs(output) == {"tag": earlier, "created": "false"}


def test_dry_run_prints_the_name_and_pushes_nothing(
    repo: tuple[Path, Path, str], tmp_path: Path
) -> None:
    work, origin, sha = repo
    output = tmp_path / "out"
    result = _run_step(work, sha, dry_run="true", output=output)
    assert result.returncode == 0, result.stderr + result.stdout
    expected = f"dev-20261016093405-{sha[:12]}"
    assert expected in result.stdout
    assert _remote_tags(origin) == {}
    assert _outputs(output) == {"tag": expected, "created": "false"}


def test_a_value_that_is_not_a_full_sha_is_refused(
    repo: tuple[Path, Path, str], tmp_path: Path
) -> None:
    work, origin, sha = repo
    result = _run_step(work, sha[:12], dry_run="false", output=tmp_path / "out")
    assert result.returncode != 0
    assert "not a full commit sha" in result.stdout + result.stderr
    assert _remote_tags(origin) == {}
