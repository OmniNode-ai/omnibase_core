# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wave D CI gate: runtime-change PRs must cite a ticket with deploy evidence.

Ticket: OMN-8912
Meta-audit root cause: Code could ship to main touching runtime paths (Dockerfiles,
node handlers, runtime kernel) with no ticket deploy DoD item, leaving .201 stale.
Today's incident: Dockerfile.runtime merged — deploy never dispatched (OMN-8841).

Usage (CI):
    python scripts/validation/validate_pr_deploy_required.py \
        --changed-files "docker/Dockerfile.runtime src/omnibase_infra/runtime/service_kernel.py" \
        --pr-body "$(gh pr view $PR --json body -q .body)" \
        --contracts-dir contracts/

Exit codes:
    0  - Gate passed (no runtime change, or deploy evidence found)
    1  - Gate failed (runtime change detected but no deploy evidence)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from re import Pattern

import yaml

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
    # Contract files trigger deploy (behavior change)
    "**/contract.yaml",
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


@dataclass
class DeployGateResult:
    passed: bool
    skipped: bool = False
    message: str = ""
    runtime_paths_hit: list[str] = field(default_factory=list)
    tickets_checked: list[str] = field(default_factory=list)


def find_runtime_paths(changed_files: list[str]) -> list[str]:
    """Return subset of changed_files that match runtime path patterns."""
    hits: list[str] = []
    for f in changed_files:
        for regex in _COMPILED_RUNTIME_PATTERNS:
            if regex.match(f):
                hits.append(f)
                break
    return hits


def has_deploy_evidence(contract_path: Path) -> bool:
    """Return True if the ticket contract has at least one deploy DoD evidence item."""
    if not contract_path.exists():
        return False
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

    # Extract cited ticket IDs from PR body
    ticket_ids = [f"OMN-{m}" for m in TICKET_PATTERN.findall(pr_body)]

    if not ticket_ids:
        return DeployGateResult(
            passed=False,
            runtime_paths_hit=runtime_hits,
            message=(
                "DEPLOY GATE FAILED: PR touches runtime paths but cites no OMN-XXXX ticket. "
                f"Runtime paths: {runtime_hits}. "
                "Add a dod_evidence item with check_value containing 'deploy', "
                "'docker exec', or 'rpk topic produce' to the cited ticket contract. "
                "See OMN-8912 and OMN-9685."
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
        parts.append(f"Tickets with no contract file: {missing}.")
    if no_deploy:
        parts.append(
            f"Tickets found but missing deploy evidence (check_value must contain "
            f"'docker exec', 'rpk topic produce', or 'deploy'): {no_deploy}."
        )
    parts.append(
        "Add a dod_evidence item with check_value containing 'deploy', 'docker exec', or "
        "'rpk topic produce' to the cited ticket contract. "
        "Root cause: OMN-8841 (deploy-agent inactive 2 days post-Dockerfile change). "
        "Gate: OMN-8912."
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

    args = parser.parse_args(argv)
    changed = [f for f in args.changed_files.split() if f]
    contracts_dir = Path(args.contracts_dir)

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
