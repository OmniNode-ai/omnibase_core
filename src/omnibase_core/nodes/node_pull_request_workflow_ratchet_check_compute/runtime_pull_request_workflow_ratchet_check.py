# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime for the pull-request workflow ratchet (C7 / OMN-14907).

Usage::

    python -m omnibase_core.nodes.node_pull_request_workflow_ratchet_check_compute.runtime_pull_request_workflow_ratchet_check --repo-root .
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.models.nodes.pull_request_workflow_ratchet_check.model_pull_request_workflow_ratchet_check_input import (
    ModelPullRequestWorkflowRatchetCheckInput,
)
from omnibase_core.nodes.node_pull_request_workflow_ratchet_check_compute.handler import (
    NodePullRequestWorkflowRatchetCheckCompute,
)
from omnibase_core.validation.validator_pull_request_workflow_ratchet import (
    DEFAULT_REGISTRY_PATH,
    current_event_name,
    expiry_horizon_days,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Count-locked ratchet over pull_request-triggered workflow files "
            "(C7 / OMN-14907). A NEW PR-triggered workflow must retire an existing "
            "one or carry an expiring waiver; the budget count only moves DOWN."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: cwd).",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help=(
            "Path to the budget registry YAML "
            "(default: <repo-root>/architecture-handshakes/pull-request-workflow-budget.yaml)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root: Path = args.repo_root
    registry_path: Path = args.registry or (repo_root / DEFAULT_REGISTRY_PATH)

    try:
        output = NodePullRequestWorkflowRatchetCheckCompute().handle(
            ModelPullRequestWorkflowRatchetCheckInput(
                repo_root=str(repo_root),
                registry_path=str(registry_path),
                horizon_days=expiry_horizon_days(current_event_name()),
            )
        )
    except (ValueError, FileNotFoundError) as exc:
        sys.stderr.write(f"pull-request-workflow-ratchet: registry error: {exc}\n")
        return 1

    if output.gaps:
        sys.stderr.write(
            "pull-request-workflow-ratchet: the count-locked ratchet over "
            "pull_request-triggered workflows is broken:\n"
        )
        for gap in output.gaps:
            sys.stderr.write(f"{gap.format()}\n")
        sys.stderr.write(
            "\n  This is CLAUDE.md's net-negative-surface rule as a mechanism. A "
            "NEW\n  PR-triggered workflow file must retire an existing one, or be "
            "added to\n  the waivers bucket (ticket + expires + justification + "
            "retires) in\n  architecture-handshakes/pull-request-workflow-budget.yaml. "
            "See C7 /\n  OMN-14907.\n\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
