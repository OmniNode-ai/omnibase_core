#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Receipt-Gate CI check — thin CLI wrapper over `receipt_gate.validate_pr_receipts`.

See `omnibase_core.validation.receipt_gate` for the decision matrix.

Exit codes:
    0 — gate passed (all receipts present + PASS, or approved skip token accepted)
    1 — gate failed (missing/failing receipts, no ticket ref, corrupt artifacts)

Usage (CI):
    uv run python scripts/validation/validate_pr_receipts.py \
        --pr-body "$(gh pr view $PR --json body -q .body)" \
        --contracts-dir onex_change_control/contracts \
        --receipts-dir onex_change_control/drift/dod_receipts
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.receipt_gate import (
    parse_pr_opened_at,
    validate_pr_receipts,
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
        "--pr-opened-at",
        default=None,
        help=(
            "UTC ISO-8601 timestamp when the PR was opened. Used to enforce "
            "post-cutoff contract_sha256 receipt binding."
        ),
    )
    args = parser.parse_args(argv)
    try:
        pr_opened_at = parse_pr_opened_at(args.pr_opened_at)
    except ValueError as exc:
        parser.error(str(exc))

    result = validate_pr_receipts(
        pr_body=args.pr_body,
        contracts_dir=Path(args.contracts_dir),
        receipts_dir=Path(args.receipts_dir),
        pr_opened_at=pr_opened_at,
    )

    if result.friction_logged:
        print(f"::warning::{result.message}")
    elif result.passed:
        print(f"::notice::{result.message}")
    else:
        print(f"::error::{result.message}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
