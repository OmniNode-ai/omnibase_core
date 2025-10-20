#!/usr/bin/env python3
"""
Comprehensive fix for missing 'self' parameters in instance methods.

This script analyzes method definitions and adds missing 'self' parameters
when methods use 'self' in their body but don't declare it as a parameter.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set

ROOT_DIR = Path("/Volumes/PRO-G40/Code/omnibase_core")


def run_mypy() -> str:
    """Run MyPy and return output."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/", "--no-error-summary"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
        check=False,
    )
    return result.stdout + result.stderr


def find_self_errors_by_file() -> dict[str, list[int]]:
    """Find all files with missing 'self' parameter errors, grouped by file."""
    output = run_mypy()
    files_errors = {}

    pattern = r'^(.+?):(\d+): error: Name "self" is not defined'

    for line in output.split("\n"):
        match = re.match(pattern, line)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            if file_path not in files_errors:
                files_errors[file_path] = []
            files_errors[file_path].append(line_num)

    return files_errors


def find_method_for_line(lines: list[str], error_line_idx: int) -> int | None:
    """
    Find the method definition line for a given error line.

    Returns the line index of the method definition, or None if not found.
    """
    # Search backwards from error line
    for i in range(error_line_idx, max(0, error_line_idx - 100), -1):
        line = lines[i].strip()

        # Look for method definition
        if line.startswith("def ") and "(" in line:
            return i

    return None


def method_needs_self(lines: list[str], method_line_idx: int) -> bool:
    """
    Check if a method definition needs 'self' parameter.

    Returns True if:
    - Method doesn't have 'self' or 'cls' as first parameter
    - Method doesn't have @staticmethod or @classmethod decorator
    """
    method_line = lines[method_line_idx]

    # Parse method signature
    match = re.match(r"\s*def\s+(\w+)\s*\((.*?)\)", method_line)
    if not match:
        return False

    params = match.group(2).strip()

    # Already has self or cls
    if params.startswith(("self", "cls")):
        return False

    # Check for decorators above method
    for i in range(method_line_idx - 1, max(0, method_line_idx - 10), -1):
        line = lines[i].strip()

        # Stop at class definition or another method
        if line.startswith("class ") or (line.startswith("def ") and "(" in line):
            break

        # Check for static/class method decorators
        if "@staticmethod" in line or "@classmethod" in line:
            return False

        # Stop at non-decorator, non-empty line
        if line and not line.startswith("@") and not line.startswith("#"):
            break

    return True


def add_self_to_method(lines: list[str], method_line_idx: int) -> bool:
    """
    Add 'self' parameter to a method definition.

    Returns True if modification was made.
    """
    method_line = lines[method_line_idx]

    # Parse method signature
    match = re.match(r"(\s*def\s+\w+\s*\()(.*)(\).*)", method_line)
    if not match:
        return False

    before = match.group(1)  # "    def method_name("
    params = match.group(2).strip()  # existing parameters
    after = match.group(3)  # ") -> ReturnType:"

    # Add self
    if params:
        new_line = f"{before}self, {params}{after}"
    else:
        new_line = f"{before}self{after}"

    lines[method_line_idx] = new_line
    return True


def fix_file(file_path: str, error_lines: list[int]) -> int:
    """
    Fix missing 'self' parameters in a file.

    Returns number of fixes applied.
    """
    path = Path(file_path)
    if not path.exists():
        return 0

    content = path.read_text()
    lines = content.split("\n")

    fixed_count = 0
    processed_methods = set()

    # Process each error line
    for error_line_num in sorted(set(error_lines)):
        # Convert to 0-based index
        error_line_idx = error_line_num - 1

        # Find the method definition for this error
        method_line_idx = find_method_for_line(lines, error_line_idx)

        if method_line_idx is None:
            continue

        # Skip if we already processed this method
        if method_line_idx in processed_methods:
            continue

        processed_methods.add(method_line_idx)

        # Check if method needs self
        if not method_needs_self(lines, method_line_idx):
            continue

        # Add self to method
        if add_self_to_method(lines, method_line_idx):
            method_match = re.match(r"\s*def\s+(\w+)", lines[method_line_idx])
            method_name = method_match.group(1) if method_match else "unknown"
            print(f"    Fixed method '{method_name}' at line {method_line_idx + 1}")
            fixed_count += 1

    if fixed_count > 0:
        path.write_text("\n".join(lines))

    return fixed_count


def main():
    """Main function."""
    print("=" * 80)
    print("FIXING MISSING 'SELF' PARAMETERS")
    print("=" * 80)

    files_errors = find_self_errors_by_file()

    if not files_errors:
        print("\nNo files with missing 'self' errors found!")
        return

    print(f"\nFound {len(files_errors)} files with missing 'self' errors")

    total_fixed = 0

    for file_path in sorted(files_errors.keys()):
        error_lines = files_errors[file_path]
        print(f"\nProcessing: {file_path}")
        print(f"  {len(error_lines)} error lines")

        fixed = fix_file(file_path, error_lines)
        total_fixed += fixed

        if fixed > 0:
            print(f"  ✓ Fixed {fixed} methods")
        else:
            print("  ⚠ No fixes applied (methods may already be correct)")

    print("\n" + "=" * 80)
    print(f"TOTAL METHODS FIXED: {total_fixed}")
    print("=" * 80)

    # Verify
    print("\nVerifying fixes...")
    remaining = len(
        [
            line
            for line in run_mypy().split("\n")
            if 'Name "self" is not defined' in line
        ]
    )
    print(f"Remaining 'self' errors: {remaining}")


if __name__ == "__main__":
    main()
