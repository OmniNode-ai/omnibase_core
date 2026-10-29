# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime for the receipt diff-consistency check (OMN-13927).

Usage::

    git diff --name-status "origin/dev"...HEAD > /tmp/diff_name_status.txt
    python -m omnibase_core.nodes.node_receipt_diff_consistency_check_compute.runtime_receipt_diff_consistency_check \\
        --diff-file /tmp/diff_name_status.txt \\
        drift/dod_receipts/OMN-1234/item/command.yaml ...
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from omnibase_core.models.nodes.receipt_diff_consistency_check.model_receipt_diff_consistency_check_input import (
    ModelReceiptDiffConsistencyCheckInput,
)
from omnibase_core.nodes.node_receipt_diff_consistency_check_compute.handler import (
    NodeReceiptDiffConsistencyCheckCompute,
)
from omnibase_core.validation.validator_receipt_diff_consistency import (
    parse_name_status,
)


def _emit(message: str = "", *, file: TextIO | None = None) -> None:
    """Write one line to stdout (or ``file``), as the old ``print`` did."""
    (file or sys.stdout).write(f"{message}\n")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: check changed receipts' attestations against a name-status diff.

    Exit codes:
        0 — no contradicted attestations
        1 — one or more contradicted attestations, or a missing/unreadable diff file
    """
    parser = argparse.ArgumentParser(
        description=(
            "Receipt-attestation diff-consistency gate (OMN-13927): fail when a "
            "receipt attests a diff-falsifiable claim (NET_NEW_ONLY, "
            "RECEIPTS_UNMODIFIED, CONTRACT_UNMODIFIED) that its own PR diff "
            "contradicts."
        )
    )
    parser.add_argument(
        "--diff-file",
        required=True,
        help="Path to a file containing `git diff --name-status <base>...<head>` output.",
    )
    parser.add_argument(
        "receipt_paths",
        nargs="*",
        help="Receipt YAML files changed on this PR (the receipts to check).",
    )
    args = parser.parse_args(argv)

    diff_path = Path(args.diff_file)
    try:
        diff_text = diff_path.read_text(encoding="utf-8")
    except OSError as exc:
        _emit(f"ERROR: cannot read --diff-file {diff_path}: {exc}", file=sys.stderr)
        return 1
    name_status = parse_name_status(diff_text)

    explicit_paths = [Path(p) for p in args.receipt_paths]
    if not explicit_paths:
        _emit("RECEIPT DIFF-CONSISTENCY GATE PASSED: no changed receipt files to check")
        return 0

    output = NodeReceiptDiffConsistencyCheckCompute().handle(
        ModelReceiptDiffConsistencyCheckInput(
            receipt_paths=[str(p) for p in explicit_paths],
            name_status=name_status,
        )
    )
    if output.passed:
        _emit(
            "RECEIPT DIFF-CONSISTENCY GATE PASSED: "
            f"0 contradicted attestations across {len(explicit_paths)} receipt(s)"
        )
        return 0

    receipt_count = len({v.receipt_path for v in output.violations})
    _emit(
        f"RECEIPT DIFF-CONSISTENCY GATE FAILED: {len(output.violations)} "
        f"contradicted attestation(s) across {receipt_count} receipt(s):\n"
    )
    for v in output.violations:
        _emit(f"  [{v.attestation}] {v.receipt_path}")
        _emit(f"    {v.detail}")
        _emit()
    return 1


if __name__ == "__main__":
    sys.exit(main())
