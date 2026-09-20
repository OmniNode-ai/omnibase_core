# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The pre-commit suite runs remotely, and its exclusions stay honest (OMN-18899).

No workflow in this repository ran the pre-commit suite, so fourteen hooks were
enforced nowhere but a developer's machine and the tree drifted red under them.
Two of those hooks had been red for months and were found by reading the
configuration, not by any gate firing.

The `precommit-suite` job in ci.yml closes that. This module keeps the closure
from decaying in the two ways it can:

* the job disappearing, or quietly acquiring a condition that lets it not run;
* the exclusion list outliving what it excuses, by naming a hook id that no
  longer exists, or by growing entries nobody has to justify.

It deliberately does NOT assert which hooks are excluded. That list is expected
to shrink, and a test pinning its contents would have to be edited by the same
change that shrinks it, which makes it a copy rather than a check.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
SKIP_FILE = REPO_ROOT / ".github" / "precommit-suite-skip.yaml"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

JOB_ID = "precommit-suite"


def _workflow() -> dict:
    loaded = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), "ci.yml did not parse to a mapping"
    return loaded


def _job() -> dict:
    jobs = _workflow()["jobs"]
    assert JOB_ID in jobs, f"ci.yml has no `{JOB_ID}` job"
    return jobs[JOB_ID]


def _skipped_ids() -> list[str]:
    """Read the exclusion list through the same parser the job's step uses."""
    loaded = yaml.safe_load(SKIP_FILE.read_text(encoding="utf-8"))
    assert isinstance(loaded, list), f"{SKIP_FILE.name} must be a YAML list of hook ids"
    return [str(item) for item in loaded]


def _configured_ids() -> set[str]:
    config = yaml.safe_load(PRECOMMIT_CONFIG.read_text(encoding="utf-8"))
    return {hook["id"] for repo in config["repos"] for hook in repo.get("hooks", [])}


class TestPrecommitSuiteJob:
    def test_job_exists_and_runs_the_suite(self) -> None:
        steps = _job()["steps"]
        commands = " ".join(str(step.get("run", "")) for step in steps)
        assert "pre-commit run --all-files" in commands

    def test_job_is_unconditional(self) -> None:
        """A gate that can be legitimately absent wedges a shape instead of failing it."""
        job = _job()
        assert "if" not in job, f"`{JOB_ID}` acquired an `if:` condition"
        assert "needs" not in job, f"`{JOB_ID}` acquired a `needs:` edge"

    def test_job_is_not_advisory(self) -> None:
        job = _job()
        assert job.get("continue-on-error") is not True
        for step in job["steps"]:
            assert step.get("continue-on-error") is not True, (
                f"a step of `{JOB_ID}` swallows its own failure: {step.get('name')}"
            )

    def test_job_is_not_soft_allowlisted(self) -> None:
        """The required summary's allowlist is what would make this job advisory."""
        from scripts.ci.ci_summary_gate import SOFT_ALLOWLIST

        assert _job()["name"] not in SOFT_ALLOWLIST

    def test_workflow_carries_no_pull_request_paths_filter(self) -> None:
        """A `paths:` filter would let the job be absent on some pull requests."""
        triggers = _workflow()[True] if True in _workflow() else _workflow()["on"]
        pull_request = triggers.get("pull_request") or {}
        assert "paths" not in pull_request
        assert "paths-ignore" not in pull_request


class TestSkipListIsHonest:
    def test_every_skipped_id_names_a_real_hook(self) -> None:
        unknown = sorted(set(_skipped_ids()) - _configured_ids())
        assert unknown == [], (
            "these ids are excluded from the pre-commit suite but no hook by "
            f"that id exists any more, so the exclusion excuses nothing: {unknown}"
        )

    def test_no_duplicate_entries(self) -> None:
        skipped = _skipped_ids()
        duplicates = sorted({item for item in skipped if skipped.count(item) > 1})
        assert duplicates == [], f"duplicated exclusions: {duplicates}"

    def test_the_list_is_read_by_the_job(self) -> None:
        """The file is only a scope if the job actually consumes it."""
        commands = " ".join(str(step.get("run", "")) for step in _job()["steps"])
        assert ".github/precommit-suite-skip.yaml" in commands
        assert "SKIP=" in commands, "pre-commit reads the exclusion set from SKIP"

    def test_the_list_lives_outside_the_workflows_directory(self) -> None:
        """A hook id inside a workflow file reads as CI coverage for its validator.

        The validator-requirements consumer resolves coverage by substring
        matching every validator's keywords against the concatenated text of
        `.github/workflows/*.y*ml`. An exclusion list placed there would flip
        the excluded validators to "covered" -- measured while this job was
        written: an earlier draft embedded the list in ci.yml and six baseline
        entries offered to record CI coverage for validators the job skips.
        """
        assert SKIP_FILE.exists()
        assert WORKFLOWS_DIR not in SKIP_FILE.parents

    def test_the_list_did_not_grow_past_its_measured_size(self) -> None:
        """A ratchet on the exclusion count, not on its contents.

        Measured on 2026-09-20: 17 hooks red over the whole tree, of which 16
        are debt and one (`check-release-identity`) asks a question that is
        meaningless on a pull request; three green hooks sourced from a private
        repository pre-commit's own clone cannot authenticate to; and one
        (`validate-deterministic-skill-routing`) that needs a sibling clone a
        runner does not have and is already mirrored by its own CI job.
        Twenty-one entries. The list is expected to shrink; growing it means a
        hook stopped being enforced, which is a decision, not a cleanup.
        Lowering this number when entries are removed is the ratchet working.
        """
        assert len(_skipped_ids()) <= 21
