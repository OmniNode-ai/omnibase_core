# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime for the receipt-honesty check (OMN-12791).

Usage::

    python -m omnibase_core.nodes.node_receipt_honesty_check_compute.runtime_receipt_honesty_check \\
        --receipts-dir drift/dod_receipts
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO, cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_check_input import (
    ModelReceiptHonestyCheckInput,
)
from omnibase_core.nodes.node_receipt_honesty_check_compute.handler import (
    NodeReceiptHonestyCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

_NODE_RECEIPT_HONESTY_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeReceiptHonestyCheckCompute]", NodeReceiptHonestyCheckCompute
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
        (_NODE_RECEIPT_HONESTY_CHECK_COMPUTE_TOKEN, NodeReceiptHonestyCheckCompute),
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
    """CLI: scan a receipts directory and exit non-zero on any violation.

    Exit codes:
        0 — no honesty violations found
        1 — one or more violations found (output lists each with rule + detail)
    """
    parser = argparse.ArgumentParser(
        description=(
            "Receipt-honesty validator (OMN-12791): scan DoD receipts for "
            "gamed probes, deferred evidence, self-attestation, fake human "
            "verifiers, and deploy-keyword echo receipts."
        )
    )
    parser.add_argument(
        "--receipts-dir",
        default="drift/dod_receipts",
        help="Root of the dod_receipts/ tree to scan.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop scanning after the first violation.",
    )
    parser.add_argument(
        "receipt_paths",
        nargs="*",
        help=(
            "Optional explicit receipt YAML files to scan. When provided, "
            "--receipts-dir is used only for display context."
        ),
    )
    args = parser.parse_args(argv)

    receipts_dir = Path(args.receipts_dir)
    explicit_paths = [Path(p) for p in args.receipt_paths]
    if explicit_paths:
        target_description = f"{len(explicit_paths)} explicit receipt file(s)"
    elif not receipts_dir.exists():
        _emit(f"ERROR: receipts-dir does not exist: {receipts_dir}", file=sys.stderr)
        return 1
    else:
        target_description = str(receipts_dir)
    output = container.get_service(_NODE_RECEIPT_HONESTY_CHECK_COMPUTE_TOKEN).handle(
        ModelReceiptHonestyCheckInput(
            receipts_dir=args.receipts_dir,
            receipt_paths=[str(p) for p in explicit_paths],
        )
    )
    findings = output.findings
    if not findings:
        _emit(f"RECEIPT HONESTY GATE PASSED: 0 violations in {target_description}")
        return 0

    total_violations = sum(len(f.violations) for f in findings)
    _emit(
        f"RECEIPT HONESTY GATE FAILED: {total_violations} violation(s) "
        f"across {len(findings)} receipt(s):\n"
    )
    for finding in findings:
        for v in finding.violations:
            _emit(f"  [{v.rule}] {finding.receipt_path}")
            _emit(f"    {v.detail}")
            _emit()
        if args.fail_fast:
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
