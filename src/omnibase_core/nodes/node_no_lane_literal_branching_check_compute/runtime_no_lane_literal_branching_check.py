# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime of the lane-literal branching guard (OMN-19760, OMN-21520).

Usage::

    python -m omnibase_core.nodes.node_no_lane_literal_branching_check_compute.runtime_no_lane_literal_branching_check \\
        --repo-root . --baseline <baseline.json> src/

Exit codes: ``0`` clean, ``1`` new findings, ``2`` usage or baseline error.
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
from omnibase_core.models.nodes.text_file_write.model_text_file_write_input import (
    ModelTextFileWriteInput,
)
from omnibase_core.models.validation.model_lane_literal_branching_violation import (
    ModelLaneLiteralBranchingViolation,
)
from omnibase_core.nodes.node_text_file_write_effect.handler import (
    NodeTextFileWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_no_lane_literal_branching import (
    _serialize_baseline,
    load_baseline,
    partition_against_baseline,
    scan_paths,
)

__all__ = ["main"]


_NODE_TEXT_FILE_WRITE_EFFECT_TOKEN = cast(
    "type[NodeTextFileWriteEffect]", NodeTextFileWriteEffect
)


def _out(message: str) -> None:
    sys.stdout.write(message + "\n")


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def _update_baseline(
    container: ModelONEXContainer,
    violations: list[ModelLaneLiteralBranchingViolation],
    scanned: list[str],
    baseline_path: Path,
) -> int:
    prior = load_baseline(baseline_path) if baseline_path.exists() else None
    scanned_set = set(scanned)
    fresh = [
        {"path": v.path, "rule": v.rule, "fingerprint": v.fingerprint}
        for v in violations
    ]
    if prior is not None:
        prior_fps = {e["fingerprint"] for e in prior}
        grown = [e for e in fresh if e["fingerprint"] not in prior_fps]
        if grown:
            _err(
                f"[lane-literal-gate] refused: the baseline would grow by {len(grown)} "
                "finding(s). The baseline only shrinks; branch on a lane role "
                "(EnumRuntimeLaneRole) instead:"
            )
            for e in grown:
                _err(f"  {e['path']}: {e['rule']}")
            return 2
        kept = [e for e in prior if e["path"] not in scanned_set]
        fresh = kept + fresh
    container.get_service(_NODE_TEXT_FILE_WRITE_EFFECT_TOKEN).handle(
        ModelTextFileWriteInput(
            path=str(baseline_path), text=_serialize_baseline(fresh)
        )
    )
    _out(
        f"[lane-literal-gate] baseline written: {len(fresh)} entr(y/ies) -> {baseline_path}"
    )
    return 0


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_TEXT_FILE_WRITE_EFFECT_TOKEN, NodeTextFileWriteEffect),
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
    """CLI entry point for pre-commit and standalone use."""
    parser = argparse.ArgumentParser(
        description=(
            "Refuse branching on a runtime lane NAME (OMN-19760). Branch on the "
            "lane's role from its runtime.lane overlay document instead."
        )
    )
    parser.add_argument("targets", nargs="*", type=Path, help="files or directories")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(),
        help="root that finding paths and fingerprints are relative to",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="ratchet baseline JSON; without it every finding fails",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite the baseline from the scanned targets (shrink only)",
    )
    args = parser.parse_args(argv)

    if not args.targets:
        return 0

    violations, scanned = scan_paths(args.targets, args.repo_root)

    if args.update_baseline:
        if args.baseline is None:
            _err("[lane-literal-gate] --update-baseline needs --baseline")
            return 2
        return _update_baseline(container, violations, scanned, args.baseline)

    baseline_fps: set[str] = set()
    if args.baseline is not None:
        if not args.baseline.exists():
            _err(f"[lane-literal-gate] baseline not found: {args.baseline}")
            return 2
        baseline_fps = {e["fingerprint"] for e in load_baseline(args.baseline)}

    new, _old = partition_against_baseline(violations, baseline_fps)
    if not new:
        return 0
    _out(f"[lane-literal-gate] [FAIL] {len(new)} branch(es) on a runtime lane name:")
    for v in new:
        shown = v.snippet if len(v.snippet) <= 160 else v.snippet[:157] + "..."
        _out(f"  {v.path}:{v.line}: {v.rule}: {shown}")
    _out(
        "\nA lane's name belongs to one deployment. Declare what the lane is for "
        "as a role in its runtime.lane overlay document and branch on "
        "EnumRuntimeLaneRole; per-lane data belongs in that deployment's overlay "
        "(OMN-19760)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
