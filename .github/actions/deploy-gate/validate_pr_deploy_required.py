# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wave D CI gate: runtime-change PRs must cite a ticket with deploy evidence.

Ticket: OMN-8912
Root cause: OMN-8841 — Dockerfile.runtime changed, deploy never dispatched,
            deploy-agent inactive 2 days undetected.
Canonical source: OMN-9685 (omnibase_core PR #902) — narrowed path patterns,
                  removed skip-token bypass.
DGM-Phase6: moved here for single-source reuse across all repos.

Usage (CI):
    python validate_pr_deploy_required.py \
        --changed-files "docker/Dockerfile.runtime src/omnibase_infra/runtime/service_kernel.py" \
        --pr-body "$(gh pr view $PR --json body -q .body)" \
        --contracts-dir contracts/

Exit codes:
    0  - Gate passed (no runtime change, or deploy evidence found)
    1  - Gate failed (runtime change detected but no deploy evidence)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from re import Pattern

# ---------------------------------------------------------------------------
# Runtime path patterns — ANY file matching these triggers the gate.
# Extend this list when new runtime-touching paths are discovered.
# ---------------------------------------------------------------------------
RUNTIME_PATH_PATTERNS = [
    # Docker layer
    "docker/Dockerfile*",
    "docker/docker-compose*.yml",
    "docker/docker-compose*.yaml",
    "docker/**/*.Dockerfile",
    "Dockerfile*",
    # Node handlers + contracts (omnibase_infra)
    "src/omnibase_infra/nodes/*/handlers/*.py",
    "src/omnibase_infra/nodes/*/handlers/*/*.py",
    "src/omnibase_infra/nodes/*/contract.yaml",
    "src/omnibase_infra/nodes/*/*/contract.yaml",
    # Runtime kernel
    "src/omnibase_infra/runtime/**/*.py",
    # Alert daemon (today's incident path — OMN-8870/OMN-8841)
    "scripts/monitor_logs.py",
    # omnimarket node handlers + runtime-touching paths only
    "src/omnimarket/nodes/*/handlers/*.py",
    "src/omnimarket/nodes/*/contract.yaml",
    "src/omnimarket/nodes/*/runtime/**/*.py",
    "src/omnimarket/services/**/*.py",
    # Cross-repo node handlers and runtime paths (OMN-9685: narrowed from catch-all)
    # Use both flat and nested forms since ** requires at least one path segment
    "src/*/nodes/*.py",
    "src/*/nodes/**/*.py",
    "src/*/runtime/*.py",
    "src/*/runtime/**/*.py",
    "src/*/handlers/*.py",
    "src/*/handlers/**/*.py",
    "src/*/services/*.py",
    "src/*/services/**/*.py",
    "src/*/cli/*.py",
    "src/*/cli/**/*.py",
    # Contract files trigger deploy (behavior change) — scoped to src/ to avoid
    # matching test fixtures and example directories.
    "src/**/contract.yaml",
]

# Deploy evidence: a dod_evidence check whose check_value contains one of these.
DEPLOY_KEYWORDS = ["docker exec", "rpk topic produce", "deploy"]


def _glob_to_regex(pattern: str) -> Pattern[str]:
    """Convert a glob pattern (with ** support) to a compiled regex."""
    # Escape everything except * and ?
    parts = re.split(r"(\*\*|\*|\?)", pattern)
    regex_parts: list[str] = []
    for part in parts:
        if part == "**":
            regex_parts.append(".*")
        elif part == "*":
            regex_parts.append("[^/]*")
        elif part == "?":
            regex_parts.append("[^/]")
        else:
            regex_parts.append(re.escape(part))
    return re.compile("^" + "".join(regex_parts) + "$")


_COMPILED_RUNTIME_PATTERNS: list[Pattern[str]] = [
    _glob_to_regex(p) for p in RUNTIME_PATH_PATTERNS
]

# Ticket ID pattern in PR body / commit messages
TICKET_PATTERN = re.compile(r"\bOMN-(\d+)\b", re.IGNORECASE)
EVIDENCE_SOURCE_PATTERN = re.compile(
    r"^Evidence-Source:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE
)
EVIDENCE_TICKET_PATTERN = re.compile(
    r"^Evidence-Ticket:\s*(OMN-\d+)\s*$", re.IGNORECASE | re.MULTILINE
)

DEFAULT_OCC_REF = "dev"


@dataclass
class DeployGateResult:
    passed: bool
    skipped: bool = False
    message: str = ""
    runtime_paths_hit: list[str] = field(default_factory=list)
    tickets_checked: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceMetadata:
    source: str | None = None
    ticket: str | None = None


@dataclass(frozen=True)
class OccEvidenceResolution:
    passed: bool
    occ_ref: str = DEFAULT_OCC_REF
    deploy_gate_required: bool = False
    skipped: bool = False
    source_kind: str = "canonical"
    evidence_ticket: str | None = None
    message: str = ""


def find_runtime_paths(changed_files: list[str]) -> list[str]:
    """Return subset of changed_files that match runtime path patterns."""
    hits: list[str] = []
    for f in changed_files:
        for regex in _COMPILED_RUNTIME_PATTERNS:
            if regex.match(f):
                hits.append(f)
                break
    return hits


def parse_evidence_metadata(pr_body: str) -> EvidenceMetadata:
    """Extract deploy-gate Evidence-* metadata from a PR body."""
    source_match = EVIDENCE_SOURCE_PATTERN.search(pr_body)
    ticket_match = EVIDENCE_TICKET_PATTERN.search(pr_body)
    return EvidenceMetadata(
        source=source_match.group(1).strip() if source_match else None,
        ticket=ticket_match.group(1).upper() if ticket_match else None,
    )


def _run_gh_json(args: list[str]) -> dict | list | str | int | float | bool | None:
    """Run gh and parse JSON output. Separated for focused unit tests."""
    completed = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def _resolve_occ_pr_source(source: str) -> tuple[str | None, str]:
    occ_pr_num = re.sub(r"^OCC#", "", source, flags=re.IGNORECASE)
    pr_json = _run_gh_json(
        [
            "pr",
            "view",
            occ_pr_num,
            "--repo",
            "OmniNode-ai/onex_change_control",
            "--json",
            "state,headRefOid,mergeCommit",
        ]
    )
    if not isinstance(pr_json, dict):
        return None, "open-pr"
    if pr_json.get("state") == "MERGED":
        merge_commit = pr_json.get("mergeCommit")
        if isinstance(merge_commit, dict):
            return merge_commit.get("oid"), "merged"
        return None, "merged"
    head_ref_oid = pr_json.get("headRefOid")
    return head_ref_oid if isinstance(head_ref_oid, str) else None, "open-pr"


def _resolve_occ_sha_source(source: str) -> tuple[str | None, str]:
    compare_json = _run_gh_json(
        [
            "api",
            f"repos/OmniNode-ai/onex_change_control/compare/HEAD...{source}",
        ]
    )
    if isinstance(compare_json, dict) and compare_json.get("status") in {
        "behind",
        "identical",
    }:
        commit_json = _run_gh_json(
            ["api", f"repos/OmniNode-ai/onex_change_control/commits/{source}"]
        )
        if isinstance(commit_json, dict):
            commit_sha = commit_json.get("sha")
            return commit_sha if isinstance(commit_sha, str) else None, "merged"
        return None, "merged"

    open_prs_json = _run_gh_json(
        [
            "pr",
            "list",
            "--repo",
            "OmniNode-ai/onex_change_control",
            "--state",
            "open",
            "--json",
            "headRefOid",
        ]
    )
    if isinstance(open_prs_json, list):
        for item in open_prs_json:
            if not isinstance(item, dict):
                continue
            head_ref_oid = item.get("headRefOid")
            if isinstance(head_ref_oid, str) and head_ref_oid.startswith(source):
                return head_ref_oid, "open-pr"
    return None, "unknown"


def resolve_occ_evidence_source(
    changed_files: list[str],
    pr_body: str,
    default_occ_ref: str = DEFAULT_OCC_REF,
) -> OccEvidenceResolution:
    """Resolve deploy-gate OCC checkout ref from PR Evidence-* metadata."""
    runtime_hits = find_runtime_paths(changed_files)
    metadata = parse_evidence_metadata(pr_body)

    if not runtime_hits:
        return OccEvidenceResolution(
            passed=True,
            occ_ref=default_occ_ref,
            skipped=True,
            deploy_gate_required=False,
            message="No runtime paths touched — deploy-gate OCC checkout skipped.",
        )

    if not metadata.source:
        return OccEvidenceResolution(
            passed=True,
            occ_ref=default_occ_ref,
            deploy_gate_required=True,
            message=(
                "Evidence-Source not present — using canonical OCC contract source."
            ),
        )

    if not metadata.ticket:
        return OccEvidenceResolution(
            passed=False,
            deploy_gate_required=True,
            source_kind="invalid",
            message=(
                "DEPLOY GATE FAILED: PR body has Evidence-Source but is missing "
                "Evidence-Ticket: OMN-XXXX. Add Evidence-Ticket so deploy-gate "
                "can validate the contract at the pinned OCC source."
            ),
        )

    if re.match(r"^OCC#[0-9]+$", metadata.source, re.IGNORECASE):
        occ_ref, source_kind = _resolve_occ_pr_source(metadata.source)
    elif re.match(r"^[0-9a-f]{7,40}$", metadata.source, re.IGNORECASE):
        occ_ref, source_kind = _resolve_occ_sha_source(metadata.source.lower())
    else:
        return OccEvidenceResolution(
            passed=False,
            deploy_gate_required=True,
            source_kind="invalid",
            evidence_ticket=metadata.ticket,
            message=(
                f"DEPLOY GATE FAILED: Evidence-Source value {metadata.source!r} "
                "is not valid. Accepted forms: OCC#<number> or a 7-40 "
                "character OCC commit SHA."
            ),
        )

    if not occ_ref:
        return OccEvidenceResolution(
            passed=False,
            deploy_gate_required=True,
            source_kind=source_kind,
            evidence_ticket=metadata.ticket,
            message=(
                f"DEPLOY GATE FAILED: Evidence-Source {metadata.source!r} "
                "could not be resolved to an OCC PR head or merged OCC commit."
            ),
        )

    return OccEvidenceResolution(
        passed=True,
        occ_ref=occ_ref,
        deploy_gate_required=True,
        source_kind=source_kind,
        evidence_ticket=metadata.ticket,
        message=(
            f"Evidence-Source resolved to OCC ref {occ_ref} "
            f"for {metadata.ticket} ({source_kind})."
        ),
    )


def has_deploy_evidence(contract_path: Path) -> bool:
    """Return True if the ticket contract has at least one deploy DoD evidence item."""
    if not contract_path.exists():
        return False
    import yaml

    try:
        with contract_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (yaml.YAMLError, OSError):
        return False

    dod_evidence = data.get("dod_evidence", []) if isinstance(data, dict) else []
    for item in dod_evidence:
        checks = item.get("checks", []) if isinstance(item, dict) else []
        for check in checks:
            value = check.get("check_value", "") if isinstance(check, dict) else ""
            if isinstance(value, str):
                if any(kw in value.lower() for kw in DEPLOY_KEYWORDS):
                    return True
    return False


def validate_pr_deploy_gate(
    changed_files: list[str],
    pr_body: str,
    contracts_dir: Path,
) -> DeployGateResult:
    """Check runtime-change PRs for deploy evidence in cited ticket contracts."""
    runtime_hits = find_runtime_paths(changed_files)

    if not runtime_hits:
        return DeployGateResult(
            passed=True,
            skipped=True,
            message="No runtime paths touched — deploy gate skipped.",
        )

    metadata = parse_evidence_metadata(pr_body)
    if metadata.source and not metadata.ticket:
        return DeployGateResult(
            passed=False,
            runtime_paths_hit=runtime_hits,
            message=(
                "DEPLOY GATE FAILED: PR body has Evidence-Source but is missing "
                "Evidence-Ticket: OMN-XXXX. Add Evidence-Ticket so deploy-gate "
                "can validate the contract at the pinned OCC source."
            ),
        )

    # Extract cited ticket IDs from PR body
    if metadata.source and metadata.ticket:
        ticket_ids = [metadata.ticket]
    else:
        ticket_ids = [f"OMN-{m}" for m in TICKET_PATTERN.findall(pr_body)]

    if not ticket_ids:
        return DeployGateResult(
            passed=False,
            runtime_paths_hit=runtime_hits,
            message=(
                "DEPLOY GATE FAILED: PR touches runtime paths but cites no OMN-XXXX ticket. "
                f"Runtime paths: {runtime_hits}. "
                "Add a dod_evidence item with check_value containing 'deploy', "
                "'docker exec', or 'rpk topic produce' to the ticket contract in "
                "onex_change_control/contracts/OMN-XXXX.yaml. "
                "See OMN-8912, OMN-9685, and OMN-11423."
            ),
        )

    # Check each cited ticket for deploy evidence
    tickets_checked: list[str] = []
    for ticket_id in ticket_ids:
        contract_path = contracts_dir / f"{ticket_id}.yaml"
        tickets_checked.append(ticket_id)
        if has_deploy_evidence(contract_path):
            return DeployGateResult(
                passed=True,
                runtime_paths_hit=runtime_hits,
                tickets_checked=tickets_checked,
                message=(
                    f"DEPLOY GATE PASSED: {ticket_id} has deploy evidence. "
                    f"Runtime paths: {runtime_hits}."
                ),
            )

    # No ticket had deploy evidence
    missing = [t for t in ticket_ids if not (contracts_dir / f"{t}.yaml").exists()]
    no_deploy = [
        t
        for t in ticket_ids
        if (contracts_dir / f"{t}.yaml").exists()
        and not has_deploy_evidence(contracts_dir / f"{t}.yaml")
    ]

    parts: list[str] = [
        "DEPLOY GATE FAILED: PR touches runtime paths but no cited ticket has deploy DoD evidence.",
        f"Runtime paths: {runtime_hits}.",
    ]
    if missing:
        parts.append(
            f"Tickets with no contract file in onex_change_control/contracts/: {missing}. "
            "Create the contract YAML in the onex_change_control repo, not in the caller repo."
        )
    if no_deploy:
        parts.append(
            f"Tickets found but missing deploy evidence (check_value must contain "
            f"'docker exec', 'rpk topic produce', or 'deploy'): {no_deploy}."
        )
    parts.append(
        "Add a dod_evidence item with check_value containing 'deploy', 'docker exec', or "
        "'rpk topic produce' to onex_change_control/contracts/OMN-XXXX.yaml. "
        "Root cause: OMN-8841 (deploy-agent inactive 2 days post-Dockerfile change). "
        "Gate: OMN-8912. Contract source fix: OMN-11423."
    )

    return DeployGateResult(
        passed=False,
        runtime_paths_hit=runtime_hits,
        tickets_checked=tickets_checked,
        message=" ".join(parts),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave D: validate that runtime-change PRs have deploy evidence.",
    )
    parser.add_argument(
        "--changed-files",
        required=True,
        help="Space-separated list of changed file paths (from gh pr diff --name-only)",
    )
    parser.add_argument(
        "--pr-body",
        required=True,
        help="Full PR description text",
    )
    parser.add_argument(
        "--contracts-dir",
        default="contracts",
        help="Directory containing OMN-XXXX.yaml ticket contracts (default: contracts/)",
    )
    parser.add_argument(
        "--resolve-occ-ref",
        action="store_true",
        help=(
            "Resolve deploy-gate Evidence-Source metadata to an OCC checkout ref "
            "and exit without validating contracts."
        ),
    )
    parser.add_argument(
        "--default-occ-ref",
        default=DEFAULT_OCC_REF,
        help="Fallback OCC ref when no Evidence-Source is present (default: dev).",
    )
    parser.add_argument(
        "--github-output",
        default="",
        help="Optional path to append GitHub Actions output values.",
    )

    args = parser.parse_args(argv)
    changed = [f for f in args.changed_files.split() if f]
    contracts_dir = Path(args.contracts_dir)

    if args.resolve_occ_ref:
        resolution = resolve_occ_evidence_source(
            changed_files=changed,
            pr_body=args.pr_body,
            default_occ_ref=args.default_occ_ref,
        )
        if args.github_output:
            with Path(args.github_output).open("a", encoding="utf-8") as fh:
                fh.write(f"occ_ref={resolution.occ_ref}\n")
                fh.write(
                    "deploy_gate_required="
                    f"{str(resolution.deploy_gate_required).lower()}\n"
                )
                fh.write(f"occ_source_kind={resolution.source_kind}\n")
                if resolution.evidence_ticket:
                    fh.write(f"evidence_ticket={resolution.evidence_ticket}\n")
        if resolution.passed:
            print(f"::notice::{resolution.message}")
        else:
            print(f"::error::{resolution.message}")
        return 0 if resolution.passed else 1

    result = validate_pr_deploy_gate(
        changed_files=changed,
        pr_body=args.pr_body,
        contracts_dir=contracts_dir,
    )

    if result.passed:
        print(f"::notice::{result.message}")
    else:
        print(f"::error::{result.message}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
