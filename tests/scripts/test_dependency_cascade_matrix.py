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


def _step_env(step_name: str) -> dict[str, object]:
    job = _job_body()
    steps = job["steps"]
    assert isinstance(steps, list)
    for step in steps:
        if isinstance(step, dict) and step.get("name") == step_name:
            env = step.get("env", {})
            assert isinstance(env, dict)
            return env
    raise AssertionError(
        f"open-bump-pr job has no step named {step_name!r}; steps present: "
        f"{[s.get('name') for s in steps if isinstance(s, dict)]}"
    )


@pytest.mark.unit
def test_pr_title_branch_and_body_all_carry_the_same_ticket() -> None:
    """Bug 2: Receipt-Gate's identity binding requires title, branch, and
    Evidence-Ticket to all reference the same OMN-<n> (validator_receipt_gate
    ``_verify_ticket_identity``, axes 1 + 2). A branch or title with no ticket
    token can never satisfy that check, however honest the PR body is.
    """
    vars_env = _step_env("Set branch and PR variables")
    assert vars_env.get("RAW_TICKET") == "${{ inputs.ticket }}", vars_env
    vars_script = _step_run("Set branch and PR variables")
    assert 'BRANCH="automation/bump-${PKG_HYPHEN}-${VERSION}-${TICKET_SLUG}"' in (
        vars_script
    ), vars_script
    assert 'echo "ticket=$TICKET" >> $GITHUB_OUTPUT' in vars_script, vars_script

    open_pr_script = _step_run("Open pull request")
    assert "(${{ steps.vars.outputs.ticket }})" in open_pr_script, open_pr_script


@pytest.mark.unit
def test_pr_body_cites_evidence_ticket_and_evidence_source() -> None:
    """Bug 2: Receipt-Gate hard-requires an `Evidence-Source:` body line, and
    (once present) a paired `Evidence-Ticket:` line -- both must resolve to
    the real upstream release evidence, not be fabricated or omitted.
    """
    script = _step_run("Open pull request")
    assert "Evidence-Ticket: ${{ steps.vars.outputs.ticket }}" in script, script
    assert "Evidence-Source: ${{ steps.vars.outputs.evidence_source }}" in script, (
        script
    )


@pytest.mark.unit
def test_workflow_inputs_are_validated_before_use() -> None:
    """CodeRabbit finding (template-injection, zizmor): `inputs.ticket` /
    `inputs.evidence_source` / `inputs.package` / `inputs.version` are
    threaded from release.yml's grep-extracted PR-body values, which are
    less trusted than a hardcoded workflow literal. They must be bound
    through `env:` (never template-expanded directly into a `run:` body)
    and validated against a strict safe-charset pattern before any
    downstream step reuses them in a branch name, PR title, or PR body.
    """
    vars_env = _step_env("Set branch and PR variables")
    for key in ("RAW_VERSION", "RAW_PACKAGE", "RAW_TICKET", "RAW_EVIDENCE_SOURCE"):
        assert key in vars_env, vars_env

    vars_script = _step_run("Set branch and PR variables")
    assert '"$PACKAGE" =~ ^[A-Za-z0-9_-]+$' in vars_script, vars_script
    assert '"$TICKET" =~ ^OMN-[0-9]+$' in vars_script, vars_script
    assert '"$EVIDENCE_SOURCE" =~ ^(OCC#[0-9]+|[0-9a-fA-F]{7,40})$' in vars_script, (
        vars_script
    )
    # Every validation branch must fail loud, not warn-and-continue.
    assert vars_script.count("exit 1") >= 4, vars_script

    # No step in this job may template-expand a raw `inputs.*` value
    # directly into a run body -- only the compute-matrix job's own
    # closed-set `case` statement (never executed as a shell subcommand)
    # is exempt.
    job = _job_body()
    job_steps = job["steps"]
    assert isinstance(job_steps, list)
    for step in job_steps:
        if not isinstance(step, dict):
            continue
        run = step.get("run", "")
        if isinstance(run, str):
            assert "${{ inputs." not in run, (
                step.get("name"),
                run,
            )


@pytest.mark.unit
def test_python_invocations_use_uv_run() -> None:
    """Coding guideline: run all Python commands through `uv run`, never a
    bare `python3` / `python` interpreter (CodeRabbit finding).
    """
    content = WORKFLOW_PATH.read_text()
    assert re.search(r"(?<!uv run )\bpython3\b", content) is None, (
        "bare `python3` invocation found; use `uv run python` instead"
    )
    assert "uv run python" in content


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
    assert "Check dependency is movable" in names, names
    assert "Upgrade lockfile" in names, names

    checkout_idx = names.index("Checkout omnibase_infra dep-provenance script")
    guard_idx = names.index("Check dependency is movable")
    lockfile_idx = names.index("Upgrade lockfile")
    assert checkout_idx < guard_idx < lockfile_idx, (
        "the provenance script must be checked out, then the movable guard "
        f"must run, then the lockfile upgrade: {names}"
    )

    guard_script = _step_run("Check dependency is movable")
    assert "check_dep_provenance.py" in guard_script, guard_script
    assert "--check-movable" in guard_script, guard_script

    lock_script = _step_run("Upgrade lockfile")
    assert "uv lock" in lock_script, lock_script
    assert '--upgrade-package "$BUMP_PACKAGE"' in lock_script, lock_script


@pytest.mark.unit
def test_upgrade_lockfile_step_sanitizes_uv_env_omn16517() -> None:
    """OMN-16517 (cloud-ci-offload-plan.md Stage 1, S1-2): the ONLY
    `uv lock` invocation in this workflow must run in a sanitized
    environment. Per uv's documented precedence, an ambient `UV_INDEX` env
    var on the runner always outranks a repo-level index pin -- this is the
    exact channel the 2026-08-23 mirror-leak incident (OMN-16162) used to
    bake 783 private-mirror `source.registry` lines into
    onex_change_control/uv.lock. `--index` (the ADDITIONAL-index flag) does
    NOT sanitize anything and must never be used in place of
    `--default-index`.
    """
    job = _job_body()
    steps = job["steps"]
    assert isinstance(steps, list)
    lockfile_step = next(
        s for s in steps if isinstance(s, dict) and s.get("name") == "Upgrade lockfile"
    )

    env = lockfile_step.get("env")
    assert isinstance(env, dict), lockfile_step
    for var in ("UV_INDEX", "UV_DEFAULT_INDEX", "UV_INDEX_URL", "UV_EXTRA_INDEX_URL"):
        assert var in env, (
            f"Upgrade lockfile step env is missing {var} -- an ambient "
            f"runner-level {var} would leak into the committed lockfile "
            "unsanitized (OMN-16162 regression class)"
        )
        assert env[var] == "", f"{var} must be cleared to empty, got {env[var]!r}"

    lock_script = _step_run("Upgrade lockfile")
    assert "uv lock --no-config" in lock_script, lock_script
    assert "--default-index https://pypi.org/simple" in lock_script, lock_script
    assert " --index " not in f" {lock_script} ", (
        "must use --default-index, never the ADDITIONAL-index --index flag "
        f"(sanitizes nothing): {lock_script}"
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


@pytest.mark.unit
def test_pyproject_pin_updated_before_lockfile_upgrade() -> None:
    """CodeRabbit finding: `uv lock --upgrade-package` cannot select a
    version outside an exact `==` requirement in `pyproject.toml`. The pin
    must be brought forward BEFORE the lock step runs, not after -- doing it
    after means the lock step silently re-resolves to the SAME old version
    while the pin update step (gated on `SKIP == 'false'`, computed from a
    diff that already happened) never even fires.
    """
    job = _job_body()
    steps = job["steps"]
    assert isinstance(steps, list)
    names = [s.get("name") for s in steps if isinstance(s, dict)]
    pin_idx = names.index("Update pyproject.toml pin")
    lockfile_idx = names.index("Upgrade lockfile")
    assert pin_idx < lockfile_idx, (
        "the pyproject.toml pin must be updated BEFORE `uv lock "
        f"--upgrade-package` runs, not after: {names}"
    )

    lock_script = _step_run("Upgrade lockfile")
    assert "git diff --quiet uv.lock pyproject.toml" in lock_script, lock_script
