#!/usr/bin/env python3
"""
ONEX Dict Methods Anti-Pattern Detection

Prevents usage of from_dict, to_dict, and from_legacy_dict methods.
We use ONLY Pydantic serialization with .model_dump() and .model_validate().

This is part of the ONEX Framework validation pipeline.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_dict_method_violations(file_path: Path) -> List[Tuple[int, str]]:
    """
    Find dict method anti-patterns in a Python file.

    Banned patterns:
    - def from_dict(
    - def to_dict(
    - def from_legacy_dict(
    - @classmethod ... from_dict
    - @classmethod ... to_dict
    - @classmethod ... from_legacy_dict
    """
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Pattern to match banned dict methods
        dict_method_patterns = [
            r"def\s+(from_dict|to_dict|from_legacy_dict)\s*\(",
            r"@classmethod.*\n.*def\s+(from_dict|to_dict|from_legacy_dict)\s*\(",
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern in dict_method_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append((line_num, line.strip()))

                # Handle multiline @classmethod patterns
                if line_num < len(lines) and "@classmethod" in line:
                    next_line = lines[line_num] if line_num < len(lines) else ""
                    combined = f"{line}\n{next_line}"
                    if re.search(
                        r"@classmethod.*\n.*def\s+(from_dict|to_dict|from_legacy_dict)\s*\(",
                        combined,
                        re.IGNORECASE | re.MULTILINE,
                    ):
                        violations.append((line_num + 1, next_line.strip()))

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

    return violations


def validate_directory(directory: Path, max_violations: int = 0) -> bool:
    """Validate all Python files in directory for dict method anti-patterns."""
    total_violations = 0
    violation_files = []

    # Find all Python files
    py_files = list(directory.rglob("*.py"))

    for py_file in py_files:
        # Skip test files and excluded directories
        if any(
            part in str(py_file)
            for part in ["test_", "tests/", "archive/", "archived/", "scripts/"]
        ):
            continue

        violations = find_dict_method_violations(py_file)
        if violations:
            violation_files.append((py_file, violations))
            total_violations += len(violations)

    # Report results
    if total_violations > max_violations:
        print(f"❌ ONEX Dict Methods Anti-Pattern Detection FAILED")
        print(f"Found {total_violations} violations (max allowed: {max_violations})")
        print()

        for file_path, violations in violation_files:
            print(f"File: {file_path}")
            for line_num, line in violations:
                print(f"  Line {line_num}: {line}")
            print()

        print(
            "❌ SOLUTION: Remove all from_dict, to_dict, and from_legacy_dict methods."
        )
        print("   Use ONLY Pydantic serialization:")
        print("   - .model_dump() for serialization")
        print("   - .model_validate() for deserialization")
        print()
        return False

    print(f"✅ ONEX Dict Methods Anti-Pattern Detection PASSED")
    print(f"Found {total_violations} violations (max allowed: {max_violations})")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Detect dict method anti-patterns in Python code"
    )
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0)",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )

    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)

    success = validate_directory(directory, args.max_violations)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
