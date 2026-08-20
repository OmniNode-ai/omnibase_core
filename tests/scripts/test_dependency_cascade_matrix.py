# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for .github/workflows/dependency-cascade.yml downstream matrix.

OMN-9425: the cascade workflow opens dependency-bump PRs in downstream repos
when a foundation package (omnibase_core / omnibase_spi / omnibase_infra) is
released. The downstream set is hardcoded in a shell ``case`` statement inside
the workflow and has silently drifted from the actual consumer list in the past
(ccc was missing even though onex_change_control depends on omnibase-core).

This test parses the workflow YAML, extracts the ``case`` block, and asserts
that each foundation package's downstream list contains every repo that
actually consumes it — guarding against future omissions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"


def _extract_case_mapping() -> dict[str, list[str]]:
    """Parse the ``case "$PACKAGE" in ... esac`` block in the workflow.

    Returns a dict mapping each foundation package name to its list of
    downstream repos, exactly as the workflow will emit them at runtime.
    """
    content = WORKFLOW_PATH.read_text()
    case_re = re.compile(
        r"(?P<pkg>[a-z_]+)\)\s*\n\s*REPOS=\'(?P<repos>\[[^\]]*\])\'",
        re.MULTILINE,
    )
    mapping: dict[str, list[str]] = {}
    for match in case_re.finditer(content):
        pkg = match.group("pkg")
        repos = json.loads(match.group("repos"))
        mapping[pkg] = repos
    return mapping


@pytest.mark.unit
def test_workflow_yaml_parses() -> None:
    """The workflow file must be valid YAML."""
    with WORKFLOW_PATH.open() as fh:
        doc = yaml.safe_load(fh)
    assert doc["name"] == "Dependency Cascade"


@pytest.mark.unit
def test_omnibase_core_cascades_to_onex_change_control() -> None:
    """OMN-9425: ccc's uv.lock must be auto-bumped on omnibase_core release.

    onex_change_control depends on omnibase-core (see ccc/pyproject.toml).
    Without this entry, ccc PRs block on stale lockfiles when new core
    modules ship, as happened with ccc#301 pre-OMN-9425.
    """
    mapping = _extract_case_mapping()
    assert "omnibase_core" in mapping, (
        "omnibase_core case missing from dependency-cascade.yml"
    )
    assert "onex_change_control" in mapping["omnibase_core"], (
        "onex_change_control must be in the omnibase_core downstream matrix; "
        "without it, ccc's uv.lock won't auto-bump on core releases "
        "(see OMN-9425 and the ccc#301 regression)."
    )


@pytest.mark.unit
def test_all_foundation_packages_have_downstream_lists() -> None:
    """Each foundation package in the docstring must have a case branch."""
    mapping = _extract_case_mapping()
    expected = {"omnibase_core", "omnibase_spi", "omnibase_infra"}
    assert expected.issubset(mapping.keys()), (
        f"Missing case branches for: {expected - mapping.keys()}"
    )


@pytest.mark.unit
def test_downstream_lists_are_non_empty_and_unique() -> None:
    """Sanity: every case emits at least one repo and no duplicates."""
    mapping = _extract_case_mapping()
    for pkg, repos in mapping.items():
        assert repos, f"{pkg}: downstream list is empty"
        assert len(repos) == len(set(repos)), (
            f"{pkg}: downstream list has duplicates: {repos}"
        )


@pytest.mark.unit
def test_omnibase_spi_and_infra_exclude_ccc() -> None:
    """ccc does not hard-depend on spi or infra; keep them out.

    Guard against over-eager additions. If ccc's pyproject.toml ever gains a
    spi or infra dependency, update the workflow case AND this test together.
    """
    mapping = _extract_case_mapping()
    assert "onex_change_control" not in mapping.get("omnibase_spi", []), (
        "ccc does not depend on omnibase-spi; see onex_change_control/pyproject.toml"
    )
    assert "onex_change_control" not in mapping.get("omnibase_infra", []), (
        "ccc does not depend on omnibase-infra; see onex_change_control/pyproject.toml"
    )


# ---------------------------------------------------------------------------
# OMN-16286: three confirmed bugs in the `open-bump-pr` job.
#
# 1. `--base main` was hardcoded, but every downstream repo's default branch
#    (and the branch the job checks out) is `dev` -- the cascade PR diffed
#    the entire dev-vs-main divergence and violated dev-only-promotion policy.
# 2. Cascade PR titles/branches/bodies carried no OMN ticket and no
#    Evidence-Source, so Receipt-Gate's identity-binding check (title <->
#    branch <-> Evidence-Ticket, all four axes) hard-failed on every PR this
#    workflow opened -- unlandable anywhere without manual intervention.
# 3. No `check_dep_provenance.py --check-movable` guard (omnibase_infra's own
#    copy has had one since OMN-15604), so `uv lock --upgrade-package`
#    against a `[tool.uv.sources]` git-overridden pin silently produced a
#    suspicious full-file uv.lock rewrite instead of failing loud.
# ---------------------------------------------------------------------------


def _job_body() -> dict[str, object]:
    with WORKFLOW_PATH.open() as fh:
        doc = yaml.safe_load(fh)
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["open-bump-pr"]
    assert isinstance(job, dict)
    return job


def _step_run(step_name: str) -> str:
    job = _job_body()
    steps = job["steps"]
    assert isinstance(steps, list)
    for step in steps:
        if isinstance(step, dict) and step.get("name") == step_name:
            run = step.get("run", "")
            assert isinstance(run, str)
            return run
    raise AssertionError(
        f"open-bump-pr job has no step named {step_name!r}; steps present: "
        f"{[s.get('name') for s in steps if isinstance(s, dict)]}"
    )


@pytest.mark.unit
def test_open_pull_request_targets_dev_not_main() -> None:
    """Bug 1: downstream branches are cut from dev, so the PR must target dev."""
    script = _step_run("Open pull request")
    assert "--base dev" in script, script
    assert "--base main" not in script, (
        "cascade PRs must never target main -- downstream repos' default "
        f"branch is dev, and diffing dev-vs-main is the OMN-16286 bug: {script}"
    )


@pytest.mark.unit
def test_workflow_call_requires_ticket_and_evidence_source() -> None:
    """Bug 2: the caller (release.yml) must supply real, non-optional evidence."""
    with WORKFLOW_PATH.open() as fh:
        doc = yaml.safe_load(fh)
    on_block = doc[True] if True in doc else doc["on"]
    call_inputs = on_block["workflow_call"]["inputs"]
    dispatch_inputs = on_block["workflow_dispatch"]["inputs"]

    for inputs in (call_inputs, dispatch_inputs):
        assert inputs["ticket"]["required"] is True, inputs["ticket"]
        assert inputs["ticket"]["type"] == "string"
        assert inputs["evidence_source"]["required"] is True, inputs["evidence_source"]
        assert inputs["evidence_source"]["type"] == "string"


@pytest.mark.unit
def test_pr_title_branch_and_body_all_carry_the_same_ticket() -> None:
    """Bug 2: Receipt-Gate's identity binding requires title, branch, and
    Evidence-Ticket to all reference the same OMN-<n> (validator_receipt_gate
    ``_verify_ticket_identity``, axes 1 + 2). A branch or title with no ticket
    token can never satisfy that check, however honest the PR body is.
    """
    vars_script = _step_run("Set branch and PR variables")
    assert "inputs.ticket" in vars_script, vars_script
    assert 'BRANCH="automation/bump-${PKG_HYPHEN}-${VERSION}-${TICKET_SLUG}"' in (
        vars_script
    ), vars_script

    open_pr_script = _step_run("Open pull request")
    assert "(${{ inputs.ticket }})" in open_pr_script, open_pr_script


@pytest.mark.unit
def test_pr_body_cites_evidence_ticket_and_evidence_source() -> None:
    """Bug 2: Receipt-Gate hard-requires an `Evidence-Source:` body line, and
    (once present) a paired `Evidence-Ticket:` line -- both must resolve to
    the real upstream release evidence, not be fabricated or omitted.
    """
    script = _step_run("Open pull request")
    assert "Evidence-Ticket: ${{ inputs.ticket }}" in script, script
    assert "Evidence-Source: ${{ inputs.evidence_source }}" in script, script


@pytest.mark.unit
def test_check_dep_provenance_movable_guard_runs_before_uv_lock() -> None:
    """Bug 3: fail loud on a git-source-overridden pin instead of silently
    re-resolving to a no-op (or, worse, a suspicious full-file rewrite --
    see the omniintelligence#827 incident this guard exists to prevent).
    """
    job = _job_body()
    steps = job["steps"]
    assert isinstance(steps, list)
    names = [s.get("name") for s in steps if isinstance(s, dict)]
    assert "Checkout omnibase_infra dep-provenance script" in names, names

    checkout_idx = names.index("Checkout omnibase_infra dep-provenance script")
    lockfile_idx = names.index("Create branch and upgrade lockfile")
    assert checkout_idx < lockfile_idx, (
        "the provenance script must be checked out before the step that "
        f"invokes it: {names}"
    )

    lockfile_script = _step_run("Create branch and upgrade lockfile")
    assert "check_dep_provenance.py" in lockfile_script, lockfile_script
    assert "--check-movable" in lockfile_script, lockfile_script
    guard_pos = lockfile_script.index("check_dep_provenance.py")
    # The actual invocation, not the explanatory comment above it (which also
    # contains this substring) -- anchor on the real command's argument.
    lock_pos = lockfile_script.index(
        'uv lock --upgrade-package "${{ inputs.package }}"'
    )
    assert guard_pos < lock_pos, (
        "the movable guard must run BEFORE `uv lock --upgrade-package`, not "
        f"after: {lockfile_script}"
    )


@pytest.mark.unit
def test_pyproject_pin_kept_in_sync_with_lockfile_bump() -> None:
    """Implied by the OMN-16286 remediation instructions: a downstream repo
    that pins this package exactly (e.g. omnibase_infra's
    `omnibase-core==0.46.8`) must not be left with a lockfile and a pin that
    silently disagree (the live infra#2805 gap this closes).
    """
    job = _job_body()
    steps = job["steps"]
    assert isinstance(steps, list)
    names = [s.get("name") for s in steps if isinstance(s, dict)]
    assert "Update pyproject.toml pin" in names, names

    commit_script = _step_run("Commit and push")
    assert "git add uv.lock pyproject.toml" in commit_script, commit_script
