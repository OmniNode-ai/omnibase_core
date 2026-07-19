# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence-shape CLI — local pre-push fail-fast check (OMN-14682).

`uv run python -m omnibase_core.validation.validator_evidence_shape_cli ...`

Validates only the SHAPE of a PR body's Evidence-Source block — that a real
stamp is a single, canonical, top-level line (not an example quoted inside a
fenced code block / blockquote), that it is a well-formed reference or a
recognized disclaimer, and that a valid reference is paired with a canonical
``Evidence-Ticket:`` line. It does NOT verify receipts, contracts, or OCC
ancestry (that needs the onex_change_control checkout and stays the CI
receipt-gate's job). The goal is to give authors fail-fast feedback locally
instead of discovering the mismatch at CI or via manual body normalization.

Body source (in order): ``--pr-body`` > ``--pr-body-file`` > ``--pr-body-file -``
(stdin). Exactly one non-empty source is required.

Exit codes:
    0  — shape is valid (or no Evidence-Source stamp is present at all)
    1  — shape violation (stamp only inside a code block/quote, multiple
         canonical stamps, malformed reference, or missing paired
         Evidence-Ticket)
    2  — usage error (no body source provided)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.validator_receipt_gate import check_evidence_source_shape


def _resolve_pr_body(args: argparse.Namespace) -> str | None:
    """Return the PR body from the highest-precedence provided source, else None."""
    if args.pr_body is not None:
        return args.pr_body
    if args.pr_body_file is not None:
        if args.pr_body_file == "-":
            return sys.stdin.read()
        return Path(args.pr_body_file).read_text(encoding="utf-8")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evidence-shape pre-push check: validate the Evidence-Source block "
            "shape of a PR body before push (OMN-14682)."
        )
    )
    parser.add_argument(
        "--pr-body",
        default=None,
        help="Full PR description text (highest precedence).",
    )
    parser.add_argument(
        "--pr-body-file",
        default=None,
        help="Path to a file containing the PR body, or '-' to read stdin.",
    )
    args = parser.parse_args(argv)

    body = _resolve_pr_body(args)
    if body is None:
        parser.error("provide --pr-body, --pr-body-file <path>, or --pr-body-file -")

    result = check_evidence_source_shape(body)
    if result.passed:
        print(f"::notice::{result.message}")
        return 0
    print(f"::error::{result.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
