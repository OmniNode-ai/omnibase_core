#!/usr/bin/env python3
"""Remove SPDX headers from Python files.

This script removes legacy SPDX license headers that were added before
the canonical file header format was established. Per docs/conventions/FILE_HEADERS.md,
files should have docstring-first format with NO SPDX headers.

Usage:
    # Remove from omnibase_core (default target)
    uv run python scripts/remove_spdx_headers.py [--dry-run] [--verbose]

    # Remove from entire src/ directory
    uv run python scripts/remove_spdx_headers.py --path src/

    # Remove from specific subdirectory
    uv run python scripts/remove_spdx_headers.py --path src/some_package/

Default Path:
    The default is src/omnibase_core because this script was originally created
    for the OMN-1360 cleanup. Use --path to target other directories.

    Note: The validator (scripts/validation/validate-no-spdx-headers.py) checks
    all of src/ by default to prevent SPDX headers anywhere in the codebase.

Ticket: OMN-1360
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Patterns to match SPDX header blocks at the start of a file
# Listed in order of specificity (most specific first)

# 3-line format: FileCopyrightText + blank # + License-Identifier
SPDX_PATTERN_3LINE = re.compile(
    r"^# SPDX-FileCopyrightText:.*\n"
    r"#\n"
    r"# SPDX-License-Identifier:.*\n",
    re.MULTILINE,
)

# 2-line format: FileCopyrightText + License-Identifier (no blank line)
SPDX_PATTERN_2LINE = re.compile(
    r"^# SPDX-FileCopyrightText:.*\n"
    r"# SPDX-License-Identifier:.*\n",
    re.MULTILINE,
)

# License-Identifier + Copyright line (MIT style)
SPDX_PATTERN_LICENSE_COPYRIGHT = re.compile(
    r"^# SPDX-License-Identifier:.*\n"
    r"# Copyright.*\n",
    re.MULTILINE,
)

# Just License-Identifier alone
SPDX_PATTERN_LICENSE_ONLY = re.compile(
    r"^# SPDX-License-Identifier:.*\n",
    re.MULTILINE,
)

# Copyright line + License-Identifier (Copyright first)
SPDX_PATTERN_COPYRIGHT_LICENSE = re.compile(
    r"^# Copyright.*\n"
    r"# SPDX-License-Identifier:.*\n",
    re.MULTILINE,
)


def _is_shebang_line(line: str) -> bool:
    """Check if line is a shebang (e.g., #!/usr/bin/env python3)."""
    return line.startswith("#!")


def _is_encoding_line(line: str) -> bool:
    """Check if line is a PEP 263 encoding declaration (e.g., # -*- coding: utf-8 -*-)."""
    return "coding:" in line or "coding=" in line


def remove_spdx_header(content: str) -> tuple[str, bool]:
    """Remove SPDX header from file content.

    Handles files with shebang and/or encoding lines before the SPDX header.
    For example:
        #!/usr/bin/env python3
        # -*- coding: utf-8 -*-
        # SPDX-FileCopyrightText: ...
        # SPDX-License-Identifier: ...

    Args:
        content: The file content as a string.

    Returns:
        Tuple of (modified_content, was_modified).
    """
    lines = content.splitlines(keepends=True)

    # Find prefix lines (shebang and encoding) that come before SPDX
    # These are preserved and not considered part of the SPDX header
    prefix_lines: list[str] = []
    remaining_start_idx = 0

    # Check first few lines for shebang/encoding (max 3 lines to check)
    for i, line in enumerate(lines[:3]):
        if _is_shebang_line(line):
            prefix_lines.append(line)
            remaining_start_idx = i + 1
        elif _is_encoding_line(line):
            prefix_lines.append(line)
            remaining_start_idx = i + 1
        else:
            # Found a line that's not shebang or encoding, stop looking
            break

    # Join remaining content after prefix lines
    remaining_content = "".join(lines[remaining_start_idx:])

    # Check if remaining content starts with SPDX or Copyright header
    if not remaining_content or not (
        remaining_content.startswith("# SPDX-")
        or remaining_content.startswith("# Copyright")
    ):
        return content, False

    # Try patterns in order of specificity (most specific first)
    patterns = [
        SPDX_PATTERN_3LINE,
        SPDX_PATTERN_2LINE,
        SPDX_PATTERN_LICENSE_COPYRIGHT,
        SPDX_PATTERN_COPYRIGHT_LICENSE,
        SPDX_PATTERN_LICENSE_ONLY,
    ]

    for pattern in patterns:
        new_remaining = pattern.sub("", remaining_content, count=1)
        if new_remaining != remaining_content:
            # Reconstruct file: prefix lines + modified remaining content
            new_content = "".join(prefix_lines) + new_remaining
            return new_content, True

    return content, False


def process_file(file_path: Path, dry_run: bool, verbose: bool) -> bool:
    """Process a single file to remove SPDX header.

    Args:
        file_path: Path to the Python file.
        dry_run: If True, don't write changes.
        verbose: If True, print detailed output.

    Returns:
        True if file was modified (or would be in dry-run mode).
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"ERROR: Could not read {file_path}: {e}", file=sys.stderr)
        return False

    new_content, was_modified = remove_spdx_header(content)

    if not was_modified:
        if verbose:
            print(f"SKIP: {file_path} (no SPDX header)")
        return False

    if dry_run:
        print(f"WOULD MODIFY: {file_path}")
        return True

    try:
        file_path.write_text(new_content, encoding="utf-8")
        if verbose:
            print(f"MODIFIED: {file_path}")
        return True
    except OSError as e:
        print(f"ERROR: Could not write {file_path}: {e}", file=sys.stderr)
        return False


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files in directory tree.

    Args:
        root: Root directory to search.

    Returns:
        List of Python file paths.
    """
    return sorted(root.rglob("*.py"))


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for errors).
    """
    parser = argparse.ArgumentParser(
        description="Remove SPDX headers from Python files (default: src/omnibase_core, use --path for broader scope)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output including skipped files",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("src/omnibase_core"),
        help="Path to search for Python files (default: src/omnibase_core). Use --path src/ for full coverage matching the validator.",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"ERROR: Path does not exist: {args.path}", file=sys.stderr)
        return 1

    python_files = find_python_files(args.path)
    print(f"Found {len(python_files)} Python files in {args.path}")

    modified_count = 0
    error_count = 0

    for file_path in python_files:
        try:
            if process_file(file_path, args.dry_run, args.verbose):
                modified_count += 1
        except Exception as e:
            print(f"ERROR: Unexpected error processing {file_path}: {e}", file=sys.stderr)
            error_count += 1

    # Summary
    print()
    if args.dry_run:
        print(f"DRY RUN: Would modify {modified_count} files")
    else:
        print(f"Modified {modified_count} files")

    if error_count > 0:
        print(f"Errors: {error_count}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
