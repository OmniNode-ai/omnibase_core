# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20921: the Version Pin Compliance job no longer reads onex_change_control.

The ``version-pin-check`` job was advisory (``continue-on-error: true``), was not
a need of CI Summary and not a required context, and read a version matrix whose
omnibase-core row was fourteen minor versions stale. The retirement deletes the
job; this module proves nothing in ``.github`` or the CI Summary poller still
names it, and that no remaining job depends on a job that is not there.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.ci_summary_gate import SOFT_ALLOWLIST

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
GITHUB_DIR = REPO_ROOT / ".github"
CI_YML = GITHUB_DIR / "workflows" / "ci.yml"
REQUIRED_CHECKS = GITHUB_DIR / "required-checks.yaml"
VALIDATOR_REQUIREMENTS = (
    REPO_ROOT / "architecture-handshakes" / "validator-requirements.yaml"
)

_JOB_ID = "version-pin-check"
_JOB_NAME = "Version Pin Compliance"
_SCRIPT = "check_version_pins"


def _ci_jobs() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    jobs = data["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _dangling_needs(jobs: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    """Return ``(job, missing_need)`` for every ``needs:`` entry with no job."""
    dangling: list[tuple[str, str]] = []
    for job_id, job in jobs.items():
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        dangling.extend((job_id, need) for need in needs if need not in jobs)
    return dangling


def _github_files() -> list[Path]:
    return sorted(
        path
        for path in GITHUB_DIR.rglob("*")
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def test_ci_workflow_runs_no_version_pin_script() -> None:
    assert _SCRIPT not in CI_YML.read_text(encoding="utf-8")


def test_version_pin_check_job_is_gone() -> None:
    jobs = _ci_jobs()
    assert _JOB_ID not in jobs
    assert _JOB_NAME not in {job.get("name") for job in jobs.values()}


def test_nothing_in_github_names_the_retired_job() -> None:
    offenders = [
        f"{path.relative_to(REPO_ROOT)}"
        for path in _github_files()
        if _JOB_ID in path.read_text(encoding="utf-8")
        or _JOB_NAME in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_required_checks_manifest_has_no_version_pin_context() -> None:
    manifest = yaml.safe_load(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    assert _JOB_NAME not in yaml.safe_dump(manifest)


def test_ci_summary_poller_no_longer_allowlists_the_job() -> None:
    assert _JOB_NAME not in SOFT_ALLOWLIST
    requirements = yaml.safe_load(VALIDATOR_REQUIREMENTS.read_text(encoding="utf-8"))
    mirror = requirements["model_b_rollup_enforcement"]["repos"]["omnibase_core"][
        "poller_soft_allowlist"
    ]
    assert _JOB_NAME not in mirror


def test_every_ci_needs_entry_resolves_to_a_job() -> None:
    assert _dangling_needs(_ci_jobs()) == []


def test_dangling_needs_checker_flags_a_broken_needs_entry() -> None:
    """Positive control: the checker above is not vacuous."""
    jobs = _ci_jobs()
    victim = next(job_id for job_id, job in jobs.items() if "needs" in job)
    broken = {**jobs, victim: {**jobs[victim], "needs": ["no-such-job-omn20921"]}}
    assert _dangling_needs(broken) == [(victim, "no-such-job-omn20921")]
