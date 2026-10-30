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
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.rollup_coverage_check.model_rollup_coverage_check_input import (
    ModelRollupCoverageCheckInput,
)
from omnibase_core.models.validation.model_rollup_coverage_gap import (
    ModelRollupCoverageGap,
)
from omnibase_core.nodes.node_rollup_coverage_check_compute.handler import (
    NodeRollupCoverageCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

_NODE_ROLLUP_COVERAGE_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeRollupCoverageCheckCompute]", NodeRollupCoverageCheckCompute
)


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def _format_gaps(gaps: list[ModelRollupCoverageGap]) -> str:
    lines = [f"{len(gaps)} rollup-coverage gap(s):"]
    for gap in gaps:
        lines.append(f"  [{gap.repo}] {gap.validator} — {gap.detail}")
    return "\n".join(lines)


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_ROLLUP_COVERAGE_CHECK_COMPUTE_TOKEN, NodeRollupCoverageCheckCompute),
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

    result = container.get_service(_NODE_ROLLUP_COVERAGE_CHECK_COMPUTE_TOKEN).handle(
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
