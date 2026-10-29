# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the contract check value linter (OMN-17427).

Usage::

    uv run python -m omnibase_core.nodes.node_contract_evidence_check_effect.runtime_contract_check_values_lint contracts/OMN-1234.yaml [...]

Exits non-zero if any fail-open, legacy-gh-pr, or mutable-state-pin pattern is found.
"""

from __future__ import annotations

import sys
from pathlib import Path

from omnibase_core.models.nodes.contract_evidence_check.model_contract_check_values_lint_request import (
    ModelContractCheckValuesLintRequest,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_check_values_lint import (
    HandlerContractCheckValuesLint,
)

__all__ = ["main"]


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def main(argv: list[str]) -> int:
    if len(argv) <= 1:
        _err("usage: lint_contract_check_values.py <contract.yaml> [...]")
        return 2

    report = HandlerContractCheckValuesLint().handle(
        ModelContractCheckValuesLintRequest(paths=tuple(Path(arg) for arg in argv[1:]))
    )
    all_findings = [(f.path, f.pattern, f.fragment) for f in report.findings]
    all_warnings = [(f.path, f.pattern, f.fragment) for f in report.warnings]

    # OMN-15411 Rule E is WARNING tier: printed, never fatal. Emitted before
    # the hard findings so it is not buried under a failure block.
    if all_warnings:
        _err(
            "WARN: SIGPIPE-fragile early-exit consumers found in contract "
            "check_value fields (OMN-15411 Rule E -- advisory, does NOT fail "
            "this hook):"
        )
        for path_str, pattern_label, fragment in all_warnings:
            _err(f"  {path_str}: {pattern_label}")
            _err(f"    ...{fragment}...")
        _err(
            "\nFix SIGPIPE-fragile pipelines by buffering the producer:\n"
            "  BAD:  gh api '...?ref=SHA' --jq .content | base64 -d"
            " | grep -q 'MARKER'\n"
            "  GOOD: body=\"$(gh api '...?ref=SHA' --jq .content | base64 -d)\""
            " && printf '%s' \"$body\" | grep -qF 'MARKER'\n"
        )

    # The OCC copy filtered findings through its frozen corpus baselines
    # (OMN-16007); core carries no such baseline, so every finding blocks.
    blocking = all_findings

    if blocking:
        _err("FAIL: invalid patterns found in contract check_value fields:")
        for path_str, pattern_label, fragment in blocking:
            _err(f"  {path_str}: {pattern_label}")
            _err(f"    ...{fragment}...")
        _err(
            "\nFix fail-open guards with fail-closed form, e.g.:\n"
            '  BAD:  [ -z "$result" ] || [ "$result" = "SUCCESS" ]\n'
            '  GOOD: [ "$result" = "SUCCESS" ]\n'
            "\nFix legacy gh pr commands with canonical placeholder form, e.g.:\n"
            "  BAD:  gh pr checks {pr} --repo {repo}\n"
            "  BAD:  gh pr checks --watch\n"
            "  GOOD (own PR):       gh pr checks ${PR_NUMBER} --repo ${REPO}\n"
            "  GOOD (cross-PR pin): gh pr checks 1721 --repo OmniNode-ai/omnimarket"
            "  (standalone hardcoded PR + literal --repo, NO ${PR_NUMBER}"
            " anywhere in the value)\n"
            "  BAD (OMN-14431):     PR_NUMBER=1721 REPO=org/repo gh pr checks"
            " ${PR_NUMBER} --repo ${REPO}  (the ${PR_NUMBER} token is"
            " pre-substituted with the runner's OWN PR before the assignment"
            " could ever apply -- the 1721 literal is silently discarded)\n"
            "\nFix tautological self-comparisons (OMN-15391 Rule C):\n"
            "  BAD:  gh pr view 5408 --repo O/R --json number"
            " --jq '.number == 5408' | grep -qx true   (asserts N == N)\n"
            "  GOOD: gh api repos/O/R/pulls/5408/files --paginate"
            " --jq '.[].filename' | grep -qx 'contracts/OMN-14979.yaml'\n"
            "\nFix fail-open absence controls (OMN-15391 Rule D):\n"
            "  BAD:  gh api '...?ref=PARENT' | grep -c 'MARKER' | grep -qx 0"
            "   (a failed fetch prints 0 and passes)\n"
            "  GOOD: body=$(gh api '...?ref=PARENT')"
            " && printf '%s' \"$body\" | grep -qF 'ANCHOR'"
            " && ! printf '%s' \"$body\" | grep -qF 'MARKER'\n"
            "  GOOD (path absent at parent): gh api 'repos/O/R/commits/PARENT'"
            " --jq '.sha' | grep -qx 'PARENT'"
            " && ! gh api 'repos/O/R/contents/FILE?ref=PARENT' --silent\n"
            "\nFix predicates pinned to MUTABLE state (OMN-15540 Rule F):\n"
            "  BAD:  gh api repos/O/R/actions/runs/30565261108/jobs"
            " --jq '...|.conclusion' | grep -qx failure"
            "   (a re-run rewrites the conclusion -- permanent BLOCK)\n"
            "  GOOD: assert a receipt under drift/dod_receipts/ that RECORDED"
            " the conclusion, or assert a monotone property of the run\n"
            "  BAD:  gh api '...?ref=user/omn-1234-my-feature'"
            "   (the head branch is deleted on merge -- 404s forever)\n"
            "  GOOD: gh api '...?ref=<squash-commit-sha-on-dev>'\n"
            "  BAD:  COUNT=\"$(gh api 'search/issues?q=...' --jq .total_count)\""
            ' && [ "$COUNT" -eq 2 ]'
            "   (the set only grows -- the next re-mint falsifies it)\n"
            "  GOOD: anchor the query to a closed window"
            " (`created:A..B`), scope it `is:open`, or assert `>= N`\n"
            "\nRun: uv run python scripts/migrate_dod_contracts.py"
            " --apply --tickets <ID>"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
