#!/usr/bin/env python3
"""
ONEX SPDX Header Prevention Validation.

This pre-commit hook prevents SPDX license headers from being (re)introduced
to the codebase. ONEX uses a centralized LICENSE file instead of per-file
headers to reduce boilerplate.

Detected Patterns (in first 10 lines):
1. # SPDX-FileCopyrightText:
2. # SPDX-License-Identifier:
3. # Copyright followed by # SPDX-License-Identifier:

Usage:
    # Check specific files (pre-commit mode)
    poetry run python scripts/validation/validate-no-spdx-headers.py <file1> [file2] ...

    # Check entire src/ directory (default)
    poetry run python scripts/validation/validate-no-spdx-headers.py

    # Check specific directory
    poetry run python scripts/validation/validate-no-spdx-headers.py src/omnibase_core/

    To allow SPDX headers in specific files (rare cases), add comment:
    # spdx-ok: reason for exception

Default Path:
    This validator defaults to src/ to check ALL source files, ensuring no
    SPDX headers exist anywhere in the codebase.

    Note: The removal script (scripts/remove_spdx_headers.py) defaults to
    src/omnibase_core for historical reasons (OMN-1360 targeted cleanup).
    Use --path src/ with the removal script for full coverage.

Rationale:
    - SPDX headers add ~440 lines of boilerplate across the codebase
    - Centralized LICENSE file is the single source of truth
    - Headers become outdated when license terms change
    - Reduces noise in file headers (see docs/conventions/FILE_HEADERS.md)

Reference:
    - OMN-1360: Remove SPDX headers from codebase
    - docs/conventions/FILE_HEADERS.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Number of lines to check at the start of each file
HEADER_CHECK_LINES = 10

# SPDX patterns to detect (compiled for efficiency)
SPDX_PATTERNS = [
    re.compile(r"^\s*#\s*SPDX-FileCopyrightText:", re.IGNORECASE),
    re.compile(r"^\s*#\s*SPDX-License-Identifier:", re.IGNORECASE),
]

# Pattern for Copyright followed by SPDX (multi-line detection)
COPYRIGHT_PATTERN = re.compile(r"^\s*#\s*Copyright\b", re.IGNORECASE)

# Bypass comment pattern
BYPASS_PATTERN = re.compile(r"#\s*spdx-ok:", re.IGNORECASE)


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a Python file for SPDX header patterns.

    Args:
        filepath: Path to the Python file to check

    Returns:
        List of (line_number, pattern_type, line_content) tuples for violations
    """
    violations: list[tuple[int, str, str]] = []

    try:
        with open(filepath, encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= HEADER_CHECK_LINES:
                    break
                lines.append(line)
    except (OSError, UnicodeDecodeError) as e:
        # Skip files that can't be read (will be caught by other tools)
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return violations

    # Check for bypass comment in the header
    for line in lines:
        if BYPASS_PATTERN.search(line):
            return violations  # File has explicit bypass

    # Track if we've seen a Copyright line (for multi-line pattern)
    seen_copyright = False
    copyright_line_num = 0
    copyright_line_content = ""

    for line_num, line in enumerate(lines, start=1):
        # Check for direct SPDX patterns
        for pattern in SPDX_PATTERNS:
            if pattern.match(line):
                pattern_name = "SPDX-FileCopyrightText" if "Copyright" in line.upper() else "SPDX-License-Identifier"
                violations.append((line_num, pattern_name, line.rstrip()))
                break

        # Track Copyright lines for multi-line pattern
        if COPYRIGHT_PATTERN.match(line) and "SPDX" not in line.upper():
            seen_copyright = True
            copyright_line_num = line_num
            copyright_line_content = line.rstrip()

    # Check for Copyright + SPDX-License-Identifier pattern (separate lines)
    # This catches headers where Copyright comes before SPDX-License-Identifier
    if seen_copyright:
        for line_num, line in enumerate(lines, start=1):
            if "SPDX-License-Identifier" in line.upper() and line_num != copyright_line_num:
                # Only report if we haven't already reported the SPDX line
                already_reported = any(v[0] == line_num for v in violations)
                if not already_reported:
                    violations.append(
                        (
                            copyright_line_num,
                            "Copyright+SPDX pattern",
                            f"{copyright_line_content} (followed by SPDX-License-Identifier on line {line_num})",
                        )
                    )
                break

    return violations


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Prevent SPDX license headers from being introduced to the codebase"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to check (defaults to src/ if none provided)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Default to src/ if no paths provided
    paths = args.paths if args.paths else [Path("src/")]

    # Collect all Python files to check
    files_to_check: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files_to_check.append(path)
        elif path.is_dir():
            files_to_check.extend(path.rglob("*.py"))
        elif not path.exists():
            print(f"Warning: Path does not exist: {path}", file=sys.stderr)

    if not files_to_check:
        if args.verbose:
            print("No Python files found to check")  # print-ok: CLI output
        return 0

    all_violations: list[tuple[Path, int, str, str]] = []

    for filepath in sorted(files_to_check):
        violations = check_file(filepath)
        for line_num, pattern_type, line_content in violations:
            all_violations.append((filepath, line_num, pattern_type, line_content))

    if all_violations:
        print(f"\n{'=' * 70}")  # print-ok: CLI output
        print("ONEX SPDX Header Prevention Failed")  # print-ok: CLI output
        print(f"{'=' * 70}\n")  # print-ok: CLI output

        print(f"Found {len(all_violations)} SPDX header(s) that must be removed:\n")  # print-ok: CLI output

        for filepath, line_num, pattern_type, line_content in all_violations:
            print(f"  {filepath}:{line_num}")  # print-ok: CLI output
            print(f"    Pattern: {pattern_type}")  # print-ok: CLI output
            print(f"    Content: {line_content[:80]}{'...' if len(line_content) > 80 else ''}")  # print-ok: CLI output
            print()  # print-ok: CLI output

        print("-" * 70)  # print-ok: CLI output
        print("\nWhy SPDX headers are not allowed:")  # print-ok: CLI output
        print("  - ONEX uses a centralized LICENSE file as the single source of truth")  # print-ok: CLI output
        print("  - Per-file headers add boilerplate without additional legal value")  # print-ok: CLI output
        print("  - See docs/conventions/FILE_HEADERS.md for canonical header format")  # print-ok: CLI output
        print("\nTo fix:")  # print-ok: CLI output
        print("  1. Remove the SPDX header lines from the affected file(s)")  # print-ok: CLI output
        print("  2. Ensure the file starts with a module docstring (PEP 257)")  # print-ok: CLI output
        print("\nFor rare legitimate exceptions, add this comment in the first 10 lines:")  # print-ok: CLI output
        print("  # spdx-ok: <reason for exception>")  # print-ok: CLI output

        return 1

    if args.verbose:
        print(f"Checked {len(files_to_check)} files - no SPDX headers found")  # print-ok: CLI output

    return 0


if __name__ == "__main__":
    sys.exit(main())
