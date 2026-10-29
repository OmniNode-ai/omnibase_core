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

from omnibase_core.models.nodes.transport_import_check.model_transport_import_check_input import (
    ModelTransportImportCheckInput,
)
from omnibase_core.nodes.node_transport_import_check_compute.handler import (
    NodeTransportImportCheckCompute,
)
from omnibase_core.validation.validator_transport_import import _SUPPRESSION_MARKER


def _out(message: str) -> None:
    sys.stdout.write(message + "\n")


def main(argv: list[str] | None = None) -> int:
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

    result = NodeTransportImportCheckCompute().handle(
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
