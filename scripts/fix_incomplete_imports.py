#!/usr/bin/env python3
"""Fix incomplete import statements created by linter."""

import re
import subprocess
from pathlib import Path


def find_incomplete_imports():
    """Find all files with syntax errors from incomplete imports."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/"],
        capture_output=True,
        text=True,
        check=False,
    )

    errors = []
    for line in result.stderr.split("\n"):
        if "error:" in line and "syntax" in line:
            match = re.match(r"^([^:]+):(\d+):", line)
            if match:
                errors.append((match.group(1), int(match.group(2))))

    return errors


def fix_incomplete_import(file_path, line_num):
    """Fix incomplete import at the given line."""
    with open(file_path) as f:
        lines = f.readlines()

    # Check if this line is part of an incomplete import
    if line_num > len(lines):
        return False

    line_idx = line_num - 1
    line = lines[line_idx]

    # Check if it's a closing paren with nothing before it
    if line.strip() == ")":
        # Look backwards to find the from ... import ( statement
        for i in range(line_idx - 1, max(0, line_idx - 10), -1):
            if "from " in lines[i] and "import (" in lines[i]:
                # Remove the incomplete import block
                del lines[i : line_idx + 1]
                with open(file_path, "w") as f:
                    f.writelines(lines)
                return True

    return False


def main():
    """Main function."""
    print("Finding incomplete imports...")
    errors = find_incomplete_imports()

    if not errors:
        print("No syntax errors found!")
        return

    print(f"Found {len(errors)} syntax errors")

    fixed = 0
    for file_path, line_num in errors:
        if fix_incomplete_import(file_path, line_num):
            fixed += 1
            print(f"Fixed: {file_path}:{line_num}")

    print(f"\nFixed {fixed} incomplete imports")


if __name__ == "__main__":
    main()
