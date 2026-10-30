# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for the validator-requirements consumer (OMN-9115, OMN-21520).

Usage::

    uv run python -m omnibase_core.nodes.node_requirements_consumer_check_compute.runtime_requirements_consumer_check \\
        --repo omnibase_core --repo-root .

Exit codes:
    0 — no gaps
    2 — one or more gaps detected
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
from omnibase_core.models.nodes.requirements_consumer_check.model_requirements_consumer_check_input import (
    ModelRequirementsConsumerCheckInput,
)
from omnibase_core.models.validation.model_validator_requirement_gap import (
    ModelValidatorRequirementGap,
)
from omnibase_core.nodes.node_requirements_consumer_check_compute.handler import (
    NodeRequirementsConsumerCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_requirements_consumer import _load_baseline

_NODE_REQUIREMENTS_CONSUMER_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeRequirementsConsumerCheckCompute]", NodeRequirementsConsumerCheckCompute
)


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def _format_gaps(gaps: list[ModelValidatorRequirementGap]) -> str:
    lines = [f"{len(gaps)} validator-requirement gap(s):"]
    for gap in gaps:
        lines.append(
            f"  [{gap.kind.value}] {gap.repo} :: {gap.validator} — {gap.detail}"
        )
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
        (
            _NODE_REQUIREMENTS_CONSUMER_CHECK_COMPUTE_TOKEN,
            NodeRequirementsConsumerCheckCompute,
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
    parser = argparse.ArgumentParser(
        description="Enforce validator-requirements.yaml (OMN-9115)."
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Target repo name (must match a key in validator-requirements.yaml applies_to_repos)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to target repo's working tree (default: cwd)",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Path to validator-requirements.yaml (default: canonical path under omnibase_core)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help=(
            "Optional baseline YAML listing accepted gaps as "
            "[{repo, validator, kind}, ...]. Any gap NOT in the baseline fails "
            "the check. Baseline entries NOT reproduced by the scan also fail "
            "(stale baseline). Mirrors the check-no-dict-any baseline ratchet."
        ),
    )
    args = parser.parse_args(argv)

    result = container.get_service(
        _NODE_REQUIREMENTS_CONSUMER_CHECK_COMPUTE_TOKEN
    ).handle(
        ModelRequirementsConsumerCheckInput(
            repo=args.repo,
            repo_root=str(args.repo_root),
            spec_path=str(args.spec) if args.spec else None,
        )
    )
    gaps = list(result.gaps)

    if args.baseline is None:
        if not gaps:
            _err(f"validator-requirements: OK ({args.repo} @ {args.repo_root})")
            return 0
        _err(_format_gaps(gaps))
        return 2

    accepted = _load_baseline(args.baseline)
    observed = {(g.repo, g.validator, g.kind.value) for g in gaps}
    new_gaps = observed - accepted
    stale_entries = accepted - observed

    if not new_gaps and not stale_entries:
        _err(
            f"validator-requirements: baseline-clean ({args.repo} — "
            f"{len(observed)} accepted gap(s))"
        )
        return 0

    if new_gaps:
        _err("New validator-requirement gaps not in baseline:")
        for repo, validator, kind in sorted(new_gaps):
            _err(f"  + [{kind}] {repo} :: {validator}")
    if stale_entries:
        _err("Baseline entries no longer reproduced (remove from baseline):")
        for repo, validator, kind in sorted(stale_entries):
            _err(f"  - [{kind}] {repo} :: {validator}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
