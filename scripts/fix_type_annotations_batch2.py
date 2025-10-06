#!/usr/bin/env python3
"""
Script to automatically fix missing type annotations in mixins batch 2.
Adds type hints to functions missing them based on mypy errors.
"""

import re
import subprocess
from pathlib import Path


def get_mypy_errors(file_path: str) -> list[tuple[int, str]]:
    """Get line numbers and error types for missing type annotations."""
    result = subprocess.run(
        ["poetry", "run", "mypy", file_path], capture_output=True, text=True
    )

    errors = []
    for line in result.stderr.split("\n") + result.stdout.split("\n"):
        if "missing a type annotation" in line or "missing a return type" in line:
            # Extract line number from error
            match = re.match(r"(.+):(\d+):", line)
            if match:
                line_num = int(match.group(2))
                error_type = "args" if "one or more arguments" in line else "return"
                errors.append((line_num, error_type))

    return errors


def fix_function_annotation(
    lines: list[str], line_num: int, error_type: str
) -> list[str]:
    """Fix missing type annotation at specified line."""
    idx = line_num - 1  # Convert to 0-based index

    if idx >= len(lines):
        return lines

    line = lines[idx]

    # Check if it's a function definition
    if "def " not in line:
        return lines

    # Pattern for function with parameters but no type hints
    if error_type == "args" or (error_type == "return" and "->" not in line):
        # Add type hints to parameters and return type
        if "self, " in line:
            # Method with parameters
            if error_type == "args":
                # Replace untyped parameters with Any
                line = re.sub(r"\(self, ([^)]+)\)", r"(self, \1: Any)", line)
                # Handle multiple parameters
                line = re.sub(r", ([a-zA-Z_][a-zA-Z0-9_]*)\)", r", \1: Any)", line)
                line = re.sub(r", ([a-zA-Z_][a-zA-Z0-9_]*),", r", \1: Any,", line)

            if "->" not in line and ":" in line:
                # Add return type
                line = re.sub(r":(\s*)$", r" -> None:\1", line)
                line = re.sub(r":(\s*)#", r" -> None:\1#", line)

        elif "__init__" in line:
            # __init__ method
            if "*args" in line and "**kwargs" in line:
                line = re.sub(r"\*args, \*\*kwargs", "*args: Any, **kwargs: Any", line)
            if "->" not in line:
                line = re.sub(r"\):", ") -> None:", line)

        lines[idx] = line

    return lines


def process_file(file_path: Path):
    """Process a single file to fix type annotations."""
    print(f"Processing {file_path}...")

    errors = get_mypy_errors(str(file_path))
    if not errors:
        print(f"  No errors found in {file_path}")
        return

    print(f"  Found {len(errors)} errors")

    # Read file
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Add imports if needed
    needs_any = any("args" in err[1] for err in errors)
    if needs_any:
        # Check if typing.Any is already imported
        has_any_import = any(
            "from typing import" in line and "Any" in line for line in lines[:20]
        )
        if not has_any_import:
            # Find first import line and add Any
            for i, line in enumerate(lines[:20]):
                if line.startswith("from typing import"):
                    if "Any" not in line:
                        lines[i] = line.rstrip().rstrip(",") + ", Any\n"
                    break
            else:
                # No typing import found, add it
                lines.insert(0, "from typing import Any\n\n")

    # Fix each error (process in reverse order to maintain line numbers)
    for line_num, error_type in sorted(errors, reverse=True):
        lines = fix_function_annotation(lines, line_num, error_type)

    # Write back
    with open(file_path, "w") as f:
        f.writelines(lines)

    print(f"  Fixed {len(errors)} errors in {file_path}")


def main():
    """Main function to process all mixin files."""
    mixins_dir = Path("src/omnibase_core/mixins")

    # Get all mixin Python files
    mixin_files = sorted(mixins_dir.glob("mixin_*.py"))

    for mixin_file in mixin_files:
        process_file(mixin_file)

    print("\nDone! Run 'poetry run mypy src/omnibase_core/mixins/' to verify.")


if __name__ == "__main__":
    main()
