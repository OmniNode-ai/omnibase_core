#!/usr/bin/env python3
"""
Comprehensive Circular Import Test

Tests all Python modules in the codebase for circular import issues.
This script now uses the reusable CircularImportValidator from omnibase_core.validation.
"""

import sys
from pathlib import Path

from omnibase_core.validation import CircularImportValidator


def main() -> int:
    """Run circular import tests and return exit code."""
    # Get the source directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_path = project_root / "src"

    if not src_path.exists():
        print(f"Error: Source path not found: {src_path}")
        return 1

    # Create validator and run validation with reporting
    validator = CircularImportValidator(
        source_path=src_path,
        verbose=True,
        exclude_patterns=["__pycache__", "archived"],
    )

    return validator.validate_and_report()


if __name__ == "__main__":
    sys.exit(main())
