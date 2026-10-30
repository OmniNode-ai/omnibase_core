# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for the transport-import gate (ARCH-002, OMN-13283, OMN-21520).

Usage::

    python -m omnibase_core.nodes.node_transport_import_check_compute.runtime_transport_import_check file1.py file2.py
    python -m omnibase_core.nodes.node_transport_import_check_compute.runtime_transport_import_check src/
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
from omnibase_core.models.nodes.transport_import_check.model_transport_import_check_input import (
    ModelTransportImportCheckInput,
)
from omnibase_core.nodes.node_transport_import_check_compute.handler import (
    NodeTransportImportCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_transport_import import _SUPPRESSION_MARKER

_NODE_TRANSPORT_IMPORT_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeTransportImportCheckCompute]", NodeTransportImportCheckCompute
)


def _out(message: str) -> None:
    sys.stdout.write(message + "\n")


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_TRANSPORT_IMPORT_CHECK_COMPUTE_TOKEN, NodeTransportImportCheckCompute),
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
    """CLI entrypoint. Accepts files (pre-commit staged mode) or directories.

    Exit codes:
        0 — no violations
        1 — violations found
    """
    parser = argparse.ArgumentParser(
        prog="validate-no-transport-imports",
        description=(
            "Ban transport/I/O library imports in ONEX node code (ARCH-002). "
            "TYPE_CHECKING-guarded imports are allowed."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-violation context lines and summary",
    )
    parsed = parser.parse_args(argv)

    result = container.get_service(_NODE_TRANSPORT_IMPORT_CHECK_COMPUTE_TOKEN).handle(
        ModelTransportImportCheckInput(paths=tuple(str(p) for p in parsed.paths))
    )
    findings = result.findings

    for finding in findings:
        _out(finding.message)
        if not parsed.quiet:
            _out(f"  {finding.context}")

    if not parsed.quiet:
        if findings:
            _out(
                f"\n{len(findings)} transport-import violation(s). "
                f"Nodes must not import transport/I/O libraries at runtime "
                f"(ARCH-002). Use a protocol + DI, a TYPE_CHECKING guard, or add "
                f"`# {_SUPPRESSION_MARKER}: <reason>` to suppress a boundary file."
            )
        else:
            _out("No transport-import violations found.")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
