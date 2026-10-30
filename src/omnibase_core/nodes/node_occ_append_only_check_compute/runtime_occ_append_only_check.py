# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime of the OCC append-only enforcement gate (OMN-13888, OMN-21520).

Usage::

    python -m omnibase_core.nodes.node_occ_append_only_check_compute.runtime_occ_append_only_check \\
        --repo <occ-repo-root> --ticket-id OMN-XXXX [--base-ref origin/dev]

Performs the git and filesystem reads, then hands the parsed inputs to the pure
evaluation in ``omnibase_core.validation.validator_occ_append_only``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.validation.validator_occ_append_only import (
    branch_history_from_git,
    evaluate_append_only,
    load_yaml_file,
    load_yaml_from_git,
    receipt_diff_from_git,
)

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OCC append-only enforcement gate (OMN-13888)"
    )
    parser.add_argument("--repo", required=True, help="Path to the OCC repo root.")
    parser.add_argument("--ticket-id", required=True)
    parser.add_argument(
        "--base-ref",
        default="origin/dev",
        help="Merge-base ref to compare against (default origin/dev).",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo)
    contract_rel = f"contracts/{args.ticket_id}.yaml"
    base_contract = load_yaml_from_git(repo, args.base_ref, contract_rel)
    head_contract = load_yaml_file(repo / contract_rel)
    receipt_diff = receipt_diff_from_git(repo, args.base_ref, args.ticket_id)
    branch_history, history_error = branch_history_from_git(
        repo, args.base_ref, args.ticket_id
    )
    if history_error is not None:
        sys.stderr.write(
            f"append-only gate cannot read the branch history: {history_error}\n"
        )
        return 1

    result = evaluate_append_only(
        base_contract, head_contract, receipt_diff, branch_history
    )
    sys.stdout.write(f"{result.to_json()}\n")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
