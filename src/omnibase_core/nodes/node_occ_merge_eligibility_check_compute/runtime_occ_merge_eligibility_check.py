# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime for the OCC-first merge eligibility gate.

Usage::

    python -m omnibase_core.nodes.node_occ_merge_eligibility_check_compute.runtime_occ_merge_eligibility_check \\
        --repo OWNER/REPO --pr-number N --pr-title T --pr-branch B \\
        --occ-commit-sha SHA --contracts-dir DIR --receipts-dir DIR
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
from omnibase_core.models.validation.model_occ_eligibility_input import (
    ModelOccEligibilityInput,
)
from omnibase_core.nodes.node_occ_merge_eligibility_check_compute.handler import (
    NodeOccMergeEligibilityCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

_NODE_OCC_MERGE_ELIGIBILITY_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeOccMergeEligibilityCheckCompute]", NodeOccMergeEligibilityCheckCompute
)


def _read_file(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


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
            _NODE_OCC_MERGE_ELIGIBILITY_CHECK_COMPUTE_TOKEN,
            NodeOccMergeEligibilityCheckCompute,
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
    parser = argparse.ArgumentParser(description="OCC-first merge eligibility gate")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--pr-title", required=True)
    parser.add_argument("--pr-body", default=None)
    parser.add_argument("--pr-body-file", default=None)
    parser.add_argument("--pr-branch", required=True)
    parser.add_argument("--pr-commit-sha", action="append", default=[])
    parser.add_argument("--pr-commit-text", action="append", default=[])
    parser.add_argument("--occ-commit-sha", required=True)
    parser.add_argument("--contracts-dir", required=True)
    parser.add_argument("--receipts-dir", required=True)
    args = parser.parse_args(argv)

    body = args.pr_body if args.pr_body is not None else _read_file(args.pr_body_file)
    snapshot = ModelOccEligibilityInput(
        repo=args.repo,
        pr_number=args.pr_number,
        pr_title=args.pr_title,
        pr_body=body,
        pr_branch=args.pr_branch,
        pr_commit_shas=tuple(args.pr_commit_sha),
        pr_commit_texts=tuple(args.pr_commit_text),
        occ_commit_sha=args.occ_commit_sha,
        contracts_dir=Path(args.contracts_dir),
        receipts_dir=Path(args.receipts_dir),
    )
    result = container.get_service(
        _NODE_OCC_MERGE_ELIGIBILITY_CHECK_COMPUTE_TOKEN
    ).handle(snapshot)
    sys.stdout.write(f"{result.to_json()}\n")
    return 0 if result.eligible else 1


if __name__ == "__main__":
    sys.exit(main())
