# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime for the report-only merge-side receipt check (OMN-21926).

Resolves the gather EFFECT and the COMPUTE node from the container, hands the gathered
facts to the check and prints the report lines. It never fails: the exit code is zero
whatever the check finds, and it is not wired as a required context.
"""

from __future__ import annotations

import argparse
import sys
from functools import cache
from pathlib import Path

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_check_input import (
    ModelMergeReceiptCheckInput,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_gather_input import (
    ModelMergeReceiptGatherInput,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_rules import (
    ModelMergeReceiptRules,
)
from omnibase_core.nodes.node_merge_receipt_check_compute.handler import (
    NodeMergeReceiptCheckCompute,
)
from omnibase_core.nodes.node_merge_receipt_gather_effect.facts_merge_receipt import (
    percentile,
)
from omnibase_core.nodes.node_merge_receipt_gather_effect.handler import (
    NodeMergeReceiptGatherEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_merge_receipt import ValidatorMergeReceipt


@cache
def _container() -> ModelONEXContainer:
    """Bind this runtime's EFFECT and COMPUTE nodes in a container, built once."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for implementation in (NodeMergeReceiptCheckCompute, NodeMergeReceiptGatherEffect):
        run_coro_sync(
            registry.register_service(
                implementation,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def _say(line: str) -> None:
    sys.stdout.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    """Print would-refuse and slot-time lines for the open pull requests; always exit 0."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state", type=Path, required=True, help="PR watcher state JSON"
    )
    parser.add_argument(
        "--clone-root", type=Path, required=True, help="Directory of canonical clones"
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        action="append",
        required=True,
        help="Ledger file; repeatable",
    )
    parser.add_argument(
        "--repo",
        action="append",
        required=True,
        help="Repository to examine; repeatable",
    )
    args = parser.parse_args(argv)

    contract = ValidatorMergeReceipt().contract
    rules = ModelMergeReceiptRules.from_contract(contract)
    slot_row = rules.row("slot_time")
    gathered = (
        _container()
        .get_service(NodeMergeReceiptGatherEffect)
        .handle(
            ModelMergeReceiptGatherInput(
                state_path=args.state,
                clone_root=args.clone_root,
                ledger_paths=tuple(args.ledger),
                repos=tuple(args.repo),
                check_names=rules.row("receipt_sources").lists["watcher_check_names"],
                surface_pattern=slot_row.texts["surface_pattern"],
            )
        )
    )
    result = (
        _container()
        .get_service(NodeMergeReceiptCheckCompute)
        .handle(
            ModelMergeReceiptCheckInput(
                source_name="open-pull-requests.merge-receipt-facts.json",
                pull_requests=gathered.pull_requests,
                contract=contract,
            )
        )
    )
    _say(
        f"would-refuse={result.would_refuse} of {result.examined} examined={result.examined}"
    )
    pairs = list(gathered.slot_seconds)
    if pairs:
        minimum = int(slot_row.texts["min_pairs"])
        note = "" if len(pairs) >= minimum else f" (fewer than {minimum} pairs)"
        _say(
            f"slot-seconds median={percentile(pairs, 0.5):.0f} "
            f"p90={percentile(pairs, 0.9):.0f} pairs={len(pairs)}{note}"
        )
    else:
        _say("slot-seconds median=unreadable p90=unreadable pairs=0")
    causes: dict[str, int] = {}
    for verdict in result.verdicts:
        for cause in verdict.causes:
            causes[cause] = causes.get(cause, 0) + 1
    _say(
        f"detail: readable={len(gathered.pull_requests)} runtime-affecting={result.examined} "
        f"not-runtime={result.skipped} paths-unreadable={len(gathered.unreadable)} "
        f"unreadable={list(gathered.unreadable)} causes={causes}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
