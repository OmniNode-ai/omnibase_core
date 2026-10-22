# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The public runner placement check has no baseline (OMN-21280).

RULING 2026-10-16T07:07:09Z: "Ci runners should be for private repos only."
The shrink-only baseline let the public jobs it recorded keep running on the
self-hosted fleet. It is deleted, and these tests refuse its return:

* the baseline file is absent, under its old path or any other name;
* nothing in the check's wiring (pre-commit, CI, the reusable workflow, the
  package's CLI) names a baseline for it;
* every job in omnibase_core's own workflows runs on a GitHub-hosted label,
  except a reusable's job that reaches the fleet only for a private caller.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_public_runner_placement import self_hosted_jobs
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
BASELINE = (
    REPO_ROOT
    / "src"
    / "omnibase_core"
    / "contracts"
    / "public_runner_placement_baseline.yaml"
)
BASELINE_NAME = "public_runner_placement_baseline"
WIRING = (
    REPO_ROOT / ".pre-commit-config.yaml",
    REPO_ROOT / ".pre-commit-hooks.yaml",
    WORKFLOWS / "ci.yml",
    WORKFLOWS / "version-drift.yml",
    REPO_ROOT / "src/omnibase_core/handlers/handler_public_runner_placement_cli.py",
    REPO_ROOT / "src/omnibase_core/handlers/handler_public_runner_placement.py",
)
PRIVATE_GUARD = "github.event.repository.private && ("


def _repository_files() -> list[str]:
    """Tracked and untracked (not ignored) files present in the working tree."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        env=scrub_git_location_env(),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return [path for path in result.stdout.splitlines() if (REPO_ROOT / path).exists()]


def test_the_baseline_file_is_absent() -> None:
    """AC2 (OMN-21280): the placement baseline is deleted."""
    assert not BASELINE.exists(), (
        f"{BASELINE.relative_to(REPO_ROOT)} is back. The public runner placement "
        "check runs with no baseline (OMN-21280): move the job to a hosted label."
    )


def test_no_repository_file_carries_a_placement_baseline() -> None:
    """AC2 (OMN-21280): the baseline does not return under another directory."""
    offenders = [path for path in _repository_files() if BASELINE_NAME in path]
    assert offenders == []


@pytest.mark.parametrize("path", WIRING, ids=lambda p: p.name)
def test_the_check_wiring_names_no_baseline(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert BASELINE_NAME not in text
    if "public-runner-placement" in text or "public_runner_placement" in text:
        lines = [
            line
            for line in text.splitlines()
            if "runner-placement" in line or "runner_placement" in line
        ]
        assert not any("--baseline" in line for line in lines), lines


def _is_reusable(document: dict[object, object]) -> bool:
    triggers = document.get(True) or document.get("on")
    return isinstance(triggers, dict | list) and "workflow_call" in triggers


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.y*ml")), ids=lambda p: p.name)
def test_omnibase_core_runs_no_job_on_the_fleet(path: Path) -> None:
    """A job here is hosted; only a reusable may keep a private-caller route."""
    source = path.read_text(encoding="utf-8")
    assert self_hosted_jobs(source, path.name) == {}
    document = yaml.safe_load(source)
    jobs = document.get("jobs") or {}
    for job_id, job in jobs.items():
        runs_on = job.get("runs-on") if isinstance(job, dict) else None
        if isinstance(runs_on, str) and "${{" in runs_on:
            assert _is_reusable(document), (
                f"{path.name}:{job_id} computes runs-on outside a reusable workflow"
            )
            assert PRIVATE_GUARD in " ".join(runs_on.split()), (path.name, job_id)
