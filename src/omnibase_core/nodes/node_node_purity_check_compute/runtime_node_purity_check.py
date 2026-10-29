# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime of the node-purity check (OMN-21520).

Usage::

    python -m omnibase_core.nodes.node_node_purity_check_compute.runtime_node_purity_check node_a.py node_b.py
    python -m omnibase_core.nodes.node_node_purity_check_compute.runtime_node_purity_check src/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.validator_node_purity import (
    _REMEDIATION,
    _SUPPRESSION_MARKER,
    ValidatorNodePurity,
)

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Accepts files (pre-commit staged mode) or directories.

    Exit codes:
        0 — no violations
        1 — violations found
    """
    parser = argparse.ArgumentParser(
        prog="node-purity",
        description=(
            "Enforce the pure-compute / no-I/O invariant in ONEX node code. "
            "Only files under a 'nodes' directory are checked."
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
        help="Suppress per-violation hint lines and summary",
    )
    parsed = parser.parse_args(argv)

    validator = ValidatorNodePurity()
    violations = validator.check_paths(parsed.paths)

    for v in violations:
        sys.stdout.write(f"{v}\n")
        if not parsed.quiet:
            hint = _REMEDIATION.get(v.rule, "")
            if hint:
                sys.stdout.write(f"  -> Hint: {hint}\n")

    if not parsed.quiet:
        if violations:
            sys.stdout.write(
                f"\n{len(violations)} node-purity violation(s). Nodes must be "
                f"pure (no network/DB clients, no env reads, no file I/O). Move "
                f"I/O to an EFFECT node, inject via DI, or add "
                f"`# {_SUPPRESSION_MARKER}: <reason>` to suppress a boundary line.\n"
            )
        else:
            sys.stdout.write("No node-purity violations found.\n")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
