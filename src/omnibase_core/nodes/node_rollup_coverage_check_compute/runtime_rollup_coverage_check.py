# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for the Model-B rollup-coverage verifier (OMN-13574, OMN-21520).

Usage::

    uv run python -m omnibase_core.nodes.node_rollup_coverage_check_compute.runtime_rollup_coverage_check \\
        --repo omnibase_core --repo-root .

Exit codes:
    0 — rollup is airtight for the repo (or repo not opted in)
    2 — one or more coverage gaps detected
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.models.nodes.rollup_coverage_check.model_rollup_coverage_check_input import (
    ModelRollupCoverageCheckInput,
)
from omnibase_core.models.validation.model_rollup_coverage_gap import (
    ModelRollupCoverageGap,
)
from omnibase_core.nodes.node_rollup_coverage_check_compute.handler import (
    NodeRollupCoverageCheckCompute,
)


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def _format_gaps(gaps: list[ModelRollupCoverageGap]) -> str:
    lines = [f"{len(gaps)} rollup-coverage gap(s):"]
    for gap in gaps:
        lines.append(f"  [{gap.repo}] {gap.validator} — {gap.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Model-B rollup coverage (OMN-13574)."
    )
    parser.add_argument("--repo", required=True, help="Target repo name.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to target repo's working tree (default: cwd).",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Path to validator-requirements.yaml (default: canonical).",
    )
    args = parser.parse_args(argv)

    result = NodeRollupCoverageCheckCompute().handle(
        ModelRollupCoverageCheckInput(
            repo=args.repo,
            repo_root=str(args.repo_root),
            spec_path=str(args.spec) if args.spec else None,
        )
    )

    if not result.opted_in:
        _err(
            f"rollup-coverage: {args.repo} not opted into Model B (pilot scope) — skip"
        )
        return 0

    gaps = list(result.gaps)
    if not gaps:
        _err(f"rollup-coverage: AIRTIGHT ({args.repo} @ {args.repo_root})")
        return 0
    _err(_format_gaps(gaps))
    return 2


if __name__ == "__main__":
    sys.exit(main())
