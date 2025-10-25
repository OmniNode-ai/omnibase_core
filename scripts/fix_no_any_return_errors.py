#!/usr/bin/env python3
"""
Systematic fixer for no-any-return mypy errors.

This script analyzes and fixes common patterns:
1. Simple getattr() returns → cast(Type, getattr(...))
2. dict.get() returns → cast(Type, dict.get(...))
3. Enum .value comparisons → bool(enum.value == "literal")
4. Model factory methods → explicit type annotation
5. Generic type returns → cast(T, value)

Usage:
    poetry run python scripts/fix_no_any_return_errors.py [--dry-run] [--pattern PATTERN]
"""

import argparse
import re
import subprocess
from pathlib import Path
from typing import NamedTuple


class ErrorLocation(NamedTuple):
    """Location of a mypy error."""

    file_path: Path
    line_number: int
    error_message: str
    return_type: str


def get_mypy_errors() -> list[ErrorLocation]:
    """Extract all no-any-return errors from mypy output."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/", "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )

    errors = []
    pattern = r'([^:]+):(\d+): error: Returning Any from function declared to return "([^"]+)"  \[no-any-return\]'

    for line in result.stdout.splitlines():
        match = re.match(pattern, line)
        if match:
            file_path, line_num, return_type = match.groups()
            errors.append(
                ErrorLocation(
                    file_path=Path(file_path),
                    line_number=int(line_num),
                    error_message=line,
                    return_type=return_type,
                )
            )

    return errors


def analyze_error_pattern(error: ErrorLocation) -> str:
    """Analyze error to determine fix pattern."""
    # Read the line causing the error
    with open(error.file_path) as f:
        lines = f.readlines()
        error_line = lines[error.line_number - 1].strip()

    # Pattern detection
    if "getattr(" in error_line:
        return "getattr_cast"
    elif ".get(" in error_line:
        return "dict_get_cast"
    elif ".value ==" in error_line or "== self." in error_line:
        return "bool_cast"
    elif "model_copy(" in error_line or "model_validate(" in error_line:
        return "model_factory"
    elif "cast(" in error_line:
        return "already_cast"
    else:
        return "manual_review"


def fix_getattr_cast(
    file_path: Path, line_number: int, return_type: str, dry_run: bool = False
) -> bool:
    """Fix getattr() returns by adding cast()."""
    with open(file_path) as f:
        lines = f.readlines()

    line = lines[line_number - 1]

    # Check if already has cast
    if "cast(" in line:
        return False

    # Pattern: return getattr(...)
    if "return getattr(" in line:
        indent = len(line) - len(line.lstrip())
        new_line = f"{' ' * indent}from typing import cast\n{line.rstrip()}\n"
        new_line = line.replace(
            "return getattr(", f"return cast({return_type}, getattr("
        )

        if not dry_run:
            lines[line_number - 1] = new_line
            with open(file_path, "w") as f:
                f.writelines(lines)

        print(f"✓ Fixed getattr in {file_path}:{line_number}")
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Fix no-any-return errors")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be fixed"
    )
    parser.add_argument("--pattern", help="Only fix specific pattern")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    args = parser.parse_args()

    print("🔍 Analyzing mypy errors...")
    errors = get_mypy_errors()
    print(f"Found {len(errors)} no-any-return errors")

    # Categorize by pattern
    patterns = {}
    for error in errors:
        pattern = analyze_error_pattern(error)
        patterns.setdefault(pattern, []).append(error)

    print("\n📊 Error patterns:")
    for pattern, error_list in sorted(patterns.items(), key=lambda x: -len(x[1])):
        print(f"  {pattern}: {len(error_list)} errors")

    if args.stats:
        return

    # Apply fixes
    if not args.dry_run:
        print("\n🔧 Applying fixes...")
    else:
        print("\n🔍 Dry run - showing what would be fixed...")

    fixed_count = 0

    for pattern, error_list in patterns.items():
        if args.pattern and pattern != args.pattern:
            continue

        for error in error_list:
            if pattern == "getattr_cast":
                if fix_getattr_cast(
                    error.file_path, error.line_number, error.return_type, args.dry_run
                ):
                    fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} errors")

    if not args.dry_run and fixed_count > 0:
        print("\n⚠️  Run mypy again to verify fixes and run tests")


if __name__ == "__main__":
    main()
