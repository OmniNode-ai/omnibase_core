# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Enum member casing check CLI runtime.

Does the file and directory I/O and runs the pure checker in
``omnibase_core.validation.checker_enum_member_casing``.
Keeps the pre-node command-line flags, output and exit codes.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from omnibase_core.validation.checker_enum_member_casing import (
    validate_directory,
    validate_file,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for command-line validation.

    Parses command-line arguments and validates enum member casing
    in the specified files or directory.

    CLI Usage:
        Default (validates src/omnibase_core)::

            python -m omnibase_core.nodes.node_enum_member_casing_check_compute.runtime_enum_member_casing_check

        With specific files (for pre-commit)::

            python -m omnibase_core.nodes.node_enum_member_casing_check_compute.runtime_enum_member_casing_check file1.py file2.py

        With verbose output::

            python -m omnibase_core.nodes.node_enum_member_casing_check_compute.runtime_enum_member_casing_check -v

    Returns:
        int: Exit code for shell integration.

            - 0: All enum members conform to UPPER_SNAKE_CASE (success)
            - 1: Violations found or error occurred (failure)
    """
    parser = argparse.ArgumentParser(
        description="Check enum member casing conventions (UPPER_SNAKE_CASE) in Python files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Check src/omnibase_core (default)
  %(prog)s file1.py file2.py        Check specific files (for pre-commit)
  %(prog)s -v                       Check with verbose output
  %(prog)s --directory path/to/dir  Check a specific directory

Valid member names (UPPER_SNAKE_CASE):
  ACTIVE, HTTP_2, V1_BETA, SHA256, SOME_LONG_NAME

Invalid member names:
  active, Active, someValue, camelCase, mixed_CASE
""",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Files to check (if none specified, checks src/omnibase_core)",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=None,
        help="Directory to check recursively (alternative to file list)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress for each file checked",
    )

    args = parser.parse_args(argv)

    # Configure logging for CLI usage
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

    all_issues: list[str] = []

    # Determine what to check
    if args.files:
        # Check specific files (pre-commit mode)
        for file_path in args.files:
            if not file_path.exists():
                logger.error("File not found: %s", file_path)
                continue

            if file_path.suffix != ".py":
                if args.verbose:
                    logger.debug("Skipping non-Python file: %s", file_path)
                continue

            issues = validate_file(file_path)
            all_issues.extend(issues)

    elif args.directory:
        # Check specified directory
        if not args.directory.exists():
            logger.error("Directory not found: %s", args.directory)
            return 1

        logger.info("Checking enum member casing in: %s", args.directory)
        logger.info("-" * 60)
        all_issues = validate_directory(args.directory, verbose=args.verbose)

    else:
        # Default: check src/omnibase_core
        this_file = Path(__file__)
        target_dir = this_file.parents[
            2
        ]  # Go up from node dir and nodes/ to omnibase_core/

        if not target_dir.exists():
            logger.error("Directory not found: %s", target_dir)
            return 1

        logger.info("Checking enum member casing in: %s", target_dir)
        logger.info("-" * 60)
        all_issues = validate_directory(target_dir, verbose=args.verbose)

    if all_issues:
        logger.warning("Found %d enum member casing violation(s):", len(all_issues))
        for issue in sorted(all_issues):
            logger.warning("  %s", issue)
        return 1

    if not args.files:  # Only print success message in directory mode
        logger.info("All enum members conform to UPPER_SNAKE_CASE!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
