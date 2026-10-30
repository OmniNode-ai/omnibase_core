# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime for the receipt re-probe check.

Usage::

    python -m omnibase_core.nodes.node_receipt_reprobe_check_compute.runtime_receipt_reprobe_check
"""

from __future__ import annotations

import argparse
import sys
from typing import TextIO, cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.contracts.ticket.model_receipt_reprobe_result import (
    ReprobeStatus,
)
from omnibase_core.models.nodes.receipt_reprobe_check.model_receipt_reprobe_check_input import (
    ModelReceiptReprobeCheckInput,
)
from omnibase_core.nodes.node_receipt_reprobe_check_compute.handler import (
    NodeReceiptReprobeCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

_NODE_RECEIPT_REPROBE_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeReceiptReprobeCheckCompute]", NodeReceiptReprobeCheckCompute
)


def _emit(message: str = "", *, file: TextIO | None = None) -> None:
    """Write one line to stdout (or ``file``), as the old ``print`` did."""
    (file or sys.stdout).write(f"{message}\n")


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_RECEIPT_REPROBE_CHECK_COMPUTE_TOKEN, NodeReceiptReprobeCheckCompute),
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
    """CLI entry: re-probe every receipt under ``--receipts-dir``.

    Exit codes:
        0 — every receipt re-verifies (PASS)
        1 — at least one receipt failed re-verification
    """
    parser = argparse.ArgumentParser(
        description=(
            "Re-probe verification — re-run every recorded probe_command "
            "and verify the current exit_code matches the recorded one. "
            "Defense against fabricated receipts (active-drive lesson F92)."
        )
    )
    parser.add_argument(
        "--receipts-dir",
        default="drift/dod_receipts",
        help="Directory tree containing ModelDodReceipt YAML files.",
    )
    args = parser.parse_args(argv)

    report = container.get_service(_NODE_RECEIPT_REPROBE_CHECK_COMPUTE_TOKEN).handle(
        ModelReceiptReprobeCheckInput(receipts_dir=args.receipts_dir)
    )

    if not report.results:
        _emit(f"::notice::no receipts found under {args.receipts_dir}")
        return 0

    failures = [r for r in report.results if r.status != ReprobeStatus.PASS]
    for r in report.results:
        line = (
            f"{r.status.value}: {r.ticket_id}/{r.evidence_item_id}/{r.check_type} "
            f"({r.receipt_path}): {r.detail}"
        )
        if r.status == ReprobeStatus.PASS:
            _emit(f"::notice::{line}")
        else:
            _emit(f"::error::{line}")

    if failures:
        _emit(
            f"::error::RE-PROBE FAILED: {len(failures)} of {len(report.results)} "
            "receipt(s) did not re-verify. Receipts may be drifted or fabricated."
        )
        return 1
    _emit(
        f"::notice::RE-PROBE PASSED: all {len(report.results)} receipt(s) re-verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
