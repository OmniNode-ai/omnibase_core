# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Literal duplication check CLI runtime.

Does the file and directory I/O and runs the pure checker in
``omnibase_core.validation.checker_literal_duplication``.
Keeps the pre-node command-line flags, output and exit codes.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from omnibase_core.validation.checker_literal_duplication import (
    KNOWN_ENUM_NAMES,
    find_enums_directory,
    get_enum_names_from_directory,
    validate_paths,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for command-line validation.

    Parses command-line arguments and validates Python files for Literal
    type alias duplications that could be replaced with existing enums.

    CLI Usage:
        Default (validates src/omnibase_core)::

            python -m omnibase_core.nodes.node_literal_duplication_check_compute.runtime_literal_duplication_check

        Validate specific paths::

            python -m omnibase_core.nodes.node_literal_duplication_check_compute.runtime_literal_duplication_check src/

        With verbose output::

            python -m omnibase_core.nodes.node_literal_duplication_check_compute.runtime_literal_duplication_check -v

    Returns:
        int: Exit code for shell integration.

            - 0: No duplications found (success)
            - 1: Duplications detected or error (failure)

    Note:
        This function is designed for CI/CD integration. A non-zero exit code
        will cause pre-commit hooks and CI pipelines to fail, preventing
        merges of code that introduces Literal duplication.
    """
    parser = argparse.ArgumentParser(
        description="Check for Literal type alias duplication with existing enums",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Check src/omnibase_core (default)
  %(prog)s src/               Check the src directory
  %(prog)s file1.py file2.py  Check specific files
  %(prog)s -v                 Check with verbose output

This checker prevents creating Literal type aliases that duplicate
existing enums in omnibase_core.enums/. Using Literal aliases creates
synchronization problems when enum values change.

Instead of:
    LiteralValidationLevel = Literal["BASIC", "STANDARD", "COMPREHENSIVE"]

Use:
    from omnibase_core.enums import EnumValidationLevel
""",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=None,
        help="Files or directories to check (default: src/omnibase_core)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress for each file checked",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Additional path patterns to exclude",
    )

    args = parser.parse_args(argv)

    # Configure logging for CLI usage
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

    # Determine target paths
    if args.paths:
        target_paths = args.paths
    else:
        # Find omnibase_core relative to this file
        this_file = Path(__file__)
        # Go up from node dir and nodes/ to omnibase_core/
        target_dir = this_file.parents[2]
        target_paths = [target_dir]

    # Validate paths exist
    for path in target_paths:
        if not path.exists():
            logger.error("Path not found: %s", path)
            return 1

    # Find enum names from the enums directory
    enums_dir = find_enums_directory()
    if enums_dir:
        known_enums = get_enum_names_from_directory(enums_dir)
        logger.debug("Loaded %d enum names from %s", len(known_enums), enums_dir)
    else:
        known_enums = KNOWN_ENUM_NAMES
        logger.debug("Using built-in enum names (%d)", len(known_enums))

    logger.info("Checking for Literal type alias duplication...")
    if args.verbose:
        logger.info("Paths: %s", [str(p) for p in target_paths])
    logger.info("-" * 60)

    errors = validate_paths(
        target_paths,
        known_enums,
        exclude_patterns=args.exclude,
        verbose=args.verbose,
    )

    if errors:
        logger.warning("Found %d Literal duplication(s):", len(errors))
        for error in sorted(errors):
            logger.warning("  %s", error)
        logger.info("")
        logger.info("Action: Replace Literal aliases with enum imports.")
        logger.info("Example:")
        logger.info("  - LiteralValidationLevel = Literal[...]")
        logger.info("  + from omnibase_core.enums import EnumValidationLevel")
        return 1

    logger.info("No Literal duplications found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
