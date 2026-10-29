# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Normalization symmetry check CLI runtime.

Does the file and directory I/O and runs the pure checker in
``omnibase_core.validation.checker_normalization_symmetry``.
Keeps the pre-node command-line flags, output and exit codes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.checker_normalization_symmetry import (
    SymmetryFinding,
    scan_source_tree,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="checker-normalization-symmetry",
        description=(
            "Verify producer/consumer topic-normalization symmetry for the ONEX "
            "event bus. Fails on OMN-9215-class asymmetries (e.g. producer "
            "strips whitespace, consumer does not)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["src"],
        help="Directories to scan recursively for .py files (default: src)",
    )
    args = parser.parse_args(argv)

    all_issues: list[SymmetryFinding] = []
    for path_str in args.paths:
        root = Path(path_str)
        if not root.exists():
            continue
        all_issues.extend(scan_source_tree(root))

    if not all_issues:
        return 0

    for issue in all_issues:
        sys.stderr.write(issue.message + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
