# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Receipt-Gate CLI — `uv run python -m omnibase_core.validation.receipt_gate_cli ...`.

Importable CLI entrypoint for the receipt-gate GitHub Actions workflow. Keeps
the gate logic discoverable as a module (not buried under scripts/).

See `omnibase_core.validation.receipt_gate.validate_pr_receipts` for the
decision matrix.

The optional ``--reexecute-probes`` flag (OMN-9789) chains in re-probe
verification after the static gate passes: every recorded ``probe_command``
is re-run and its current ``exit_code`` is compared against the recorded
one. Default OFF in CI (slow; may have side effects), default ON in the
manual scaffold's session-end ritual.

Exit codes:
    0  — gate passed (all receipts present + PASS, or override accepted),
         and (when ``--reexecute-probes`` is set) every recorded probe
         re-verified
    1  — gate failed (missing/failing receipts, no ticket ref, corrupt
         artifacts, or — under ``--reexecute-probes`` — at least one probe
         did not re-verify)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.receipt_gate import validate_pr_receipts
from omnibase_core.validation.validator_receipt_reprobe import (
    verify_receipts_by_reexecuting_probes,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Receipt-Gate: every cited ticket's dod_evidence must have PASS "
            "receipts on disk for the PR to merge."
        )
    )
    parser.add_argument("--pr-body", required=True, help="Full PR description text.")
    parser.add_argument(
        "--pr-title",
        default=None,
        help="PR title text (used as fallback when body has no closing keywords).",
    )
    parser.add_argument(
        "--contracts-dir",
        default="onex_change_control/contracts",
        help="Directory containing OMN-XXXX.yaml ticket contracts.",
    )
    parser.add_argument(
        "--receipts-dir",
        default="onex_change_control/drift/dod_receipts",
        help="Directory tree containing ModelDodReceipt YAML files.",
    )
    parser.add_argument(
        "--reexecute-probes",
        action="store_true",
        default=False,
        help=(
            "OMN-9789: after the static gate passes, re-run every recorded "
            "probe_command and verify exit_code parity. Default OFF (slow; "
            "may have side effects). Recommended ON in the manual "
            "scaffold's session-end ritual; OFF in CI."
        ),
    )
    args = parser.parse_args(argv)

    result = validate_pr_receipts(
        pr_body=args.pr_body,
        contracts_dir=Path(args.contracts_dir),
        receipts_dir=Path(args.receipts_dir),
        pr_title=args.pr_title,
    )

    if result.friction_logged:
        print(f"::warning::{result.message}")
    elif result.passed:
        print(f"::notice::{result.message}")
    else:
        print(f"::error::{result.message}")

    if not result.passed:
        return 1

    if args.reexecute_probes:
        report = verify_receipts_by_reexecuting_probes(Path(args.receipts_dir))
        for r in report.results:
            line = (
                f"{r.status}: {r.ticket_id}/{r.evidence_item_id}/{r.check_type} "
                f"({r.receipt_path}): {r.detail}"
            )
            if r.status == "PASS":
                print(f"::notice::{line}")
            else:
                print(f"::error::{line}")
        if not report.passed:
            failures = report.failures
            print(
                f"::error::RE-PROBE FAILED: {len(failures)} of "
                f"{len(report.results)} receipt(s) did not re-verify "
                "(active-drive lesson F92)."
            )
            return 1
        print(
            f"::notice::RE-PROBE PASSED: all {len(report.results)} receipt(s) "
            "re-verified."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
