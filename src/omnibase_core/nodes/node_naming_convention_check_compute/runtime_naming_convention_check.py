# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Naming convention check CLI runtime.

Does the file and directory I/O and runs the pure checker in
``omnibase_core.validation.checker_naming_convention``.
Keeps the pre-node command-line flags, output and exit codes.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from omnibase_core.validation.checker_naming_convention import validate_directory

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for command-line validation.

    Parses command-line arguments and validates Python file naming conventions
    in the specified directory (or src/omnibase_core by default).

    CLI Usage:
        Default (validates src/omnibase_core)::

            python -m omnibase_core.nodes.node_naming_convention_check_compute.runtime_naming_convention_check

        With verbose output::

            python -m omnibase_core.nodes.node_naming_convention_check_compute.runtime_naming_convention_check -v

        Validate a specific directory::

            python -m omnibase_core.nodes.node_naming_convention_check_compute.runtime_naming_convention_check /path/to/dir

        Validate specific directory with verbose output::

            python -m omnibase_core.nodes.node_naming_convention_check_compute.runtime_naming_convention_check /path/to/dir -v

    Returns:
        int: Exit code for shell integration.

            - 0: All files conform to naming conventions (success)
            - 1: Violations found or directory not found (failure)

    Note:
        This function is designed for CI/CD integration. A non-zero exit code
        will cause pre-commit hooks and CI pipelines to fail, preventing
        merges of non-conforming code.
    """
    parser = argparse.ArgumentParser(
        description="Check file naming conventions in omnibase_core",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Check src/omnibase_core (default)
  %(prog)s -v                 Check with verbose output (show each file)
  %(prog)s path/to/dir        Check a specific directory
  %(prog)s path/to/dir -v     Check specific directory with verbose output
""",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=None,
        help="Directory to check (default: src/omnibase_core)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress for each file checked",
    )
    parser.add_argument(
        "--warning-mode",
        action="store_true",
        help="Report naming violations without failing the process.",
    )

    args = parser.parse_args(argv)

    # Configure logging for CLI usage
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

    # Determine target directory
    if args.directory:
        target_dir = args.directory
    else:
        # Find omnibase_core relative to this file
        this_file = Path(__file__)
        target_dir = this_file.parents[
            2
        ]  # Go up from node dir and nodes/ to omnibase_core/

    if not target_dir.exists():
        logger.error("Directory not found: %s", target_dir)
        return 1

    logger.info("Checking naming conventions in: %s", target_dir)
    logger.info("-" * 60)

    errors = validate_directory(target_dir, verbose=args.verbose)

    if errors:
        logger.warning("Found %d naming convention violation(s):", len(errors))
        for error in sorted(errors):
            logger.warning("  %s", error)
        if args.warning_mode:
            logger.warning("Warning mode enabled; not failing on violations.")
            return 0
        return 1

    logger.info("All files conform to naming conventions!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
