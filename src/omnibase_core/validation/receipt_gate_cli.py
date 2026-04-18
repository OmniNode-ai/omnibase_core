# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Receipt-Gate CLI — `uv run python -m omnibase_core.validation.receipt_gate_cli ...`.

Importable CLI entrypoint for the receipt-gate GitHub Actions workflow. Keeps
the gate logic discoverable as a module (not buried under scripts/).

See `omnibase_core.validation.receipt_gate.validate_pr_receipts` for the
decision matrix.

Exit codes:
    0  — gate passed (all receipts present + PASS, or override accepted)
    1  — gate failed (missing/failing receipts, no ticket ref, corrupt artifacts)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.receipt_gate import validate_pr_receipts


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
    args = parser.parse_args(argv)

    result = validate_pr_receipts(
        pr_body=args.pr_body,
        contracts_dir=Path(args.contracts_dir),
        receipts_dir=Path(args.receipts_dir),
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
