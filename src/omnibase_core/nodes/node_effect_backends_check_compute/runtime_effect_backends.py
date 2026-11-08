# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Local run of the effect-backends validator (OMN-23114).

Every operation the node contract advertises is dispatched from the contract's own
``handler_routing`` table, so ``load_contracts`` is reached by a local run and not only advertised::

    python -m omnibase_core.nodes.node_effect_backends_check_compute.runtime_effect_backends \
        --contract <path to this node's contract.yaml> <root>

The contract reaches the runtime through the caller, never located from this module. ``<root>`` is a directory of node folders, each holding a ``contract.yaml``. The report is printed as
JSON. The exit code is 0 for a scanned inventory and 2 when the root is unavailable.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from omnibase_core.models.validation.model_effect_backends_load_request import (
    ModelEffectBackendsLoadRequest,
)
from omnibase_core.models.validation.model_effect_backends_report import (
    ModelEffectBackendsReport,
)
from omnibase_core.models.validation.model_effect_backends_request import (
    ModelEffectBackendsRequest,
)
from omnibase_core.models.validation.model_loaded_contracts import ModelLoadedContracts
from omnibase_core.nodes.node_effect_backends_check_compute.handler_effect_backends import (
    HandlerEffectBackends,
)
from omnibase_core.nodes.node_effect_backends_check_compute.handler_effect_backends_loader import (
    HandlerEffectBackendsLoader,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

LOAD_OPERATION = "load_contracts"
JUDGE_OPERATION = "effect_backends"
EXIT_UNAVAILABLE = 2


def dispatch_table(contract_path: Path) -> dict[str, object]:
    """One handler instance per operation of the contract's ``handler_routing`` table."""
    contract = load_yaml_mapping_no_duplicates(
        contract_path.read_text(encoding="utf-8"), source=str(contract_path)
    )
    routing = contract["handler_routing"]
    table: dict[str, object] = {}
    for entry in routing["handlers"]:
        handler = entry["handler"]
        cls = getattr(importlib.import_module(handler["module"]), handler["name"])
        table[entry["operation"]] = cls()
    return table


def run_local(root: str, contract_path: Path) -> ModelEffectBackendsReport:
    """Load the contracts under ``root`` then judge them, both through the dispatch table."""
    table = dispatch_table(contract_path)
    loader = cast(HandlerEffectBackendsLoader, table[LOAD_OPERATION])
    judge = cast(HandlerEffectBackends, table[JUDGE_OPERATION])
    loaded: ModelLoadedContracts = loader.handle(
        ModelEffectBackendsLoadRequest(root=root)
    )
    return judge.handle(
        ModelEffectBackendsRequest(
            contracts=loaded.documents,
            unreadable=loaded.unreadable,
            root_unavailable=loaded.root_unavailable,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; prints the report as JSON."""
    parser = argparse.ArgumentParser(
        description="Effect-backends validator (OMN-22911)"
    )
    parser.add_argument(
        "--contract",
        required=True,
        type=Path,
        help="This node's contract.yaml, whose handler_routing is dispatched",
    )
    parser.add_argument("root", help="Directory whose children are node folders")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = run_local(args.root, args.contract)
    sys.stdout.write(f"{report.model_dump_json(indent=2)}\n")
    return 0 if report.inventory_available else EXIT_UNAVAILABLE


if __name__ == "__main__":
    sys.exit(main())
