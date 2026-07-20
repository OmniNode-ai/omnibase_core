#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# VENDORED COPY (OMN-14863, fan-out from OMN-14854 omniclaude canary).
# Canonical source: OmniNode-ai/omniclaude
# .github/actions/required-check-skip-guard/validate_no_required_check_skip_vectors.py
# Vendored here so the local pre-commit hook can run without a network fetch;
# the CI reusable workflow (required-check-skip-guard-reusable.yml) instead
# fetches the canonical copy live via sparse-checkout at runtime, so CI always
# uses the freshest version. Keep this vendored copy in sync with the
# canonical source by re-copying on drift (same convention as
# reject-deploy-gate-skip-token.sh's per-repo vendored copies).
#
# Required-Check Skip-Vector Guard (OMN-14854) — PR-time validator.
#
# Fails closed on any of the four skip vectors enumerated in the design spec
# (docs/design or ticket OMN-14854; grounded against
# `gh api repos/OmniNode-ai/omniclaude/branches/dev/protection/required_status_checks`,
# 58 contexts, fetched 2026-07-20):
#
#   1. A path-scoped `pull_request` / `pull_request_target` / `merge_group`
#      trigger on the workflow producing (or calling) a REQUIRED context —
#      a PR touching only excluded paths never runs the job, wedging the
#      required check PENDING forever.
#   2. A job-level `if:` on the job that IS the required context (Shape A)
#      that is not provably true for every PR-reachable event — a skipped
#      job counts as "passing" under GitHub branch protection, so this is a
#      silent bypass, not merely a wedge.
#   3. A caller job (`uses:` job) gated by a conditional `if:` that is not
#      provably true — when it evaluates false the reusable workflow never
#      runs, so the composed context is never even created (permanent
#      PENDING, worse than vector 2).
#   4. A required context's producing/caller workflow has no
#      pull_request/pull_request_target/merge_group trigger at all.
#
# Runs identically under pre-commit (local) and CI (the reusable workflow) —
# same script, same manifest, same verdict. Enforcement, not detection
# (CLAUDE.md Rule #5).
#
# Usage:
#   python validate_no_required_check_skip_vectors.py \
#       --manifest .github/required-checks.yaml \
#       --workflows-dir .github/workflows

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _workflow_model import (  # noqa: E402
    ALWAYS_TRUE_FOR_PR,
    PR_REACHABLE_EVENTS,
    ResolvedJob,
    UnresolvedContext,
    classify,
    load_workflows,
    resolve_context_to_job,
)


@dataclass
class Finding:
    context: str
    vector: str
    message: str

    def render(self) -> str:
        return f"[{self.vector}] required context '{self.context}': {self.message}"


def _declared_events(workflow) -> tuple[str, ...]:
    return tuple(e for e in PR_REACHABLE_EVENTS if e in workflow.on_block)


def _check_path_filters(context: str, workflow, label: str) -> list[Finding]:
    findings: list[Finding] = []
    for evt in workflow.path_filtered_pr_events():
        severity = (
            "vector-1-pull_request_target-paths"
            if evt == "pull_request_target"
            else (
                "vector-1-merge_group-paths"
                if evt == "merge_group"
                else "vector-1-paths"
            )
        )
        findings.append(
            Finding(
                context=context,
                vector=severity,
                message=(
                    f"{label} ({workflow.path.name}) has a `paths`/`paths-ignore` filter "
                    f"on its `{evt}` trigger. A PR touching only excluded paths never runs "
                    "this job, so the required check goes PENDING forever (or is silently "
                    "absent depending on branch-protection strict mode)."
                    + (
                        " pull_request_target path filters are also a privilege-escalation "
                        "vector."
                        if evt == "pull_request_target"
                        else ""
                    )
                    + (
                        " A merge_group path filter wedges the whole queue, not just one PR."
                        if evt == "merge_group"
                        else ""
                    )
                ),
            )
        )
    return findings


def _check_job_if(
    context: str,
    workflow,
    job,
    label: str,
    vector: str,
    *,
    skip_semantics: str = "never",
    rationale: str = "",
) -> list[Finding]:
    verdict = classify(job.if_expr, _declared_events(workflow))
    if verdict == ALWAYS_TRUE_FOR_PR:
        return []

    # skip_semantics: neutral_ok — the only sanctioned escape hatch (design
    # spec §3a). It suppresses vector-2/vector-3 (conditional `if:`) findings
    # ONLY — it never suppresses vector-1 (path filter) or vector-4 (missing
    # trigger), which are unconditional wedges/silence, not a documented,
    # reviewed exception. A rationale citing a tracking ticket is mandatory;
    # an unratified `neutral_ok` (no ticket cited) is treated as `never`.
    if skip_semantics == "neutral_ok" and rationale.strip():
        return []

    return [
        Finding(
            context=context,
            vector=vector,
            message=(
                f"{label} '{job.job_id}' in {workflow.path.name} has `if: {job.if_expr}` "
                "that can evaluate false on an ordinary same-repo PR/merge_group event. "
                + (
                    "A skipped job satisfies GitHub branch protection (skipped counts as "
                    "passing) — this is a live silent-pass bypass, not merely a wedge."
                    if vector == "vector-2-ungated-job-if"
                    else "When the caller job is skipped, the reusable workflow never "
                    "starts, so the composed required context is never created at all — "
                    "the PR is PENDING forever, it does not pass."
                )
            ),
        )
    ]


def validate_gate(context: str, gate: dict, workflows: dict) -> list[Finding]:
    findings: list[Finding] = []
    producer_kind = gate.get("producer_kind", "local")
    skip_semantics = gate.get("skip_semantics", "never")
    rationale = gate.get("rationale", "")

    try:
        resolved: ResolvedJob = resolve_context_to_job(context, workflows)
    except UnresolvedContext:
        if producer_kind == "local":
            findings.append(
                Finding(
                    context=context,
                    vector="vector-unresolved",
                    message=(
                        "does not resolve to any job in .github/workflows/ — manifest "
                        "drift or a renamed job. Fail-closed per design spec §1."
                    ),
                )
            )
        return findings

    if resolved.cross_repo_ref is not None:
        # Only the local caller side is checkable from this repo.
        assert resolved.caller_job_id is not None  # noqa: S101 - invariant of resolve_context_to_job
        caller_wf = resolved.workflow
        caller_job = caller_wf.jobs[resolved.caller_job_id]
        findings.extend(
            _check_path_filters(
                context, caller_wf, "producing workflow (cross-repo caller)"
            )
        )
        findings.extend(
            _check_job_if(
                context,
                caller_wf,
                caller_job,
                "caller job",
                "vector-3-ungated-caller-if",
                skip_semantics=skip_semantics,
                rationale=rationale,
            )
        )
        if not caller_wf.triggers_on_pr_or_merge_group():
            findings.append(
                Finding(
                    context=context,
                    vector="vector-4-no-pr-trigger",
                    message=(
                        f"caller workflow {caller_wf.path.name} has no pull_request/"
                        "merge_group trigger — the cross-repo call can never fire on a PR."
                    ),
                )
            )
        return findings

    if not resolved.is_nested:
        wf = resolved.workflow
        job = wf.jobs[resolved.job_id]
        findings.extend(_check_path_filters(context, wf, "producing workflow"))
        findings.extend(
            _check_job_if(
                context,
                wf,
                job,
                "producing job",
                "vector-2-ungated-job-if",
                skip_semantics=skip_semantics,
                rationale=rationale,
            )
        )
        if not wf.triggers_on_pr_or_merge_group():
            findings.append(
                Finding(
                    context=context,
                    vector="vector-4-no-pr-trigger",
                    message=(
                        f"{wf.path.name} has no pull_request/pull_request_target/"
                        "merge_group trigger in its `on:` block — it can never fire on a "
                        "PR, so branch protection can never see it satisfied."
                    ),
                )
            )
        return findings

    caller_wf = resolved.workflow
    caller_job = caller_wf.jobs[resolved.job_id]
    findings.extend(_check_path_filters(context, caller_wf, "caller workflow"))
    findings.extend(
        _check_job_if(
            context,
            caller_wf,
            caller_job,
            "caller job",
            "vector-3-ungated-caller-if",
            skip_semantics=skip_semantics,
            rationale=rationale,
        )
    )
    if not caller_wf.triggers_on_pr_or_merge_group():
        findings.append(
            Finding(
                context=context,
                vector="vector-4-no-pr-trigger",
                message=(
                    f"{caller_wf.path.name} (caller) has no pull_request/merge_group "
                    "trigger — the composed context can never be created."
                ),
            )
        )
    return findings


def run(manifest_path: Path, workflows_dir: Path) -> list[Finding]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    workflows = load_workflows(workflows_dir)

    findings: list[Finding] = []
    for gate in manifest.get("gates", []):
        if gate.get("mode") != "REQUIRED":
            continue
        context = gate["name"]
        findings.extend(validate_gate(context, gate, workflows))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--workflows-dir", required=True, type=Path)
    args = parser.parse_args()

    findings = run(args.manifest, args.workflows_dir)

    if findings:
        print(f"FAIL: {len(findings)} required-check skip vector(s) found:\n")
        for f in findings:
            print(f"  - {f.render()}")
        print(
            "\nFix: remove the path filter / job-level if: for these required checks, "
            "or register an explicit skip_semantics contract in "
            ".github/required-checks.yaml with a cited ticket."
        )
        return 1

    print("PASS: no required-check skip vectors found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
