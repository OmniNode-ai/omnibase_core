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
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.pull_request_workflow_ratchet_check.model_pull_request_workflow_ratchet_check_input import (
    ModelPullRequestWorkflowRatchetCheckInput,
)
from omnibase_core.nodes.node_pull_request_workflow_ratchet_check_compute.handler import (
    NodePullRequestWorkflowRatchetCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_pull_request_workflow_ratchet import (
    DEFAULT_REGISTRY_PATH,
    current_event_name,
    expiry_horizon_days,
)

_NODE_PULL_REQUEST_WORKFLOW_RATCHET_CHECK_COMPUTE_TOKEN = cast(
    "type[NodePullRequestWorkflowRatchetCheckCompute]",
    NodePullRequestWorkflowRatchetCheckCompute,
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


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (
            _NODE_PULL_REQUEST_WORKFLOW_RATCHET_CHECK_COMPUTE_TOKEN,
            NodePullRequestWorkflowRatchetCheckCompute,
        ),
    ):
        run_coro_sync(
            registry.register_service(
                token,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def main(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run the CLI with container-resolved services."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(argv, container)
    finally:
        if owned:
            container.close()


def _run(argv: list[str] | None, container: ModelONEXContainer) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root: Path = args.repo_root
    registry_path: Path = args.registry or (repo_root / DEFAULT_REGISTRY_PATH)

    try:
        output = container.get_service(
            _NODE_PULL_REQUEST_WORKFLOW_RATCHET_CHECK_COMPUTE_TOKEN
        ).handle(
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
