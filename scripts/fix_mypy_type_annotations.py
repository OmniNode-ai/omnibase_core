#!/usr/bin/env python3
"""
Automation script to fix MyPy no-untyped-def errors.

This script:
1. Runs mypy to find all no-untyped-def errors
2. Analyzes each error to determine the fix pattern
3. Applies appropriate type annotations
4. Verifies fixes with mypy

Usage:
    poetry run python scripts/fix_mypy_type_annotations.py [--dry-run] [--file FILE]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Common type annotation patterns
VALIDATOR_PATTERN = r"@field_validator\(['\"].*?['\"]\)"
SERIALIZER_PATTERN = r"@field_serializer\(['\"].*?['\"]\)"
CLASSMETHOD_PATTERN = r"@classmethod"
DECORATOR_PATTERN = r"def decorator\(func:"


def run_mypy(file_path: str | None = None) -> list[dict[str, Any]]:
    """Run mypy and parse no-untyped-def errors."""
    cmd = ["poetry", "run", "mypy"]
    if file_path:
        cmd.append(file_path)
    else:
        cmd.append("src/omnibase_core/")

    result = subprocess.run(cmd, capture_output=True, text=True)

    errors = []
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        if "no-untyped-def" in line:
            match = re.match(r"(.+?):(\d+):\s*error:\s*(.+)", line)
            if match:
                errors.append(
                    {
                        "file": match.group(1),
                        "line": int(match.group(2)),
                        "message": match.group(3),
                    }
                )

    return errors


def read_file_lines(file_path: str) -> list[str]:
    """Read file and return lines."""
    with open(file_path) as f:
        return f.readlines()


def write_file_lines(file_path: str, lines: list[str]) -> None:
    """Write lines to file."""
    with open(file_path, "w") as f:
        f.writelines(lines)


def detect_function_pattern(lines: list[str], line_num: int) -> str:
    """Detect the pattern of function at given line."""
    # Check preceding lines for decorators
    check_start = max(0, line_num - 5)
    preceding = "".join(lines[check_start:line_num])

    if re.search(VALIDATOR_PATTERN, preceding):
        return "validator"
    if re.search(SERIALIZER_PATTERN, preceding):
        return "serializer"
    if re.search(CLASSMETHOD_PATTERN, preceding):
        return "classmethod"
    if "def decorator(" in preceding or "def wrapper(" in preceding:
        return "decorator"

    return "method"


def fix_validator(lines: list[str], line_num: int) -> list[str]:
    """Fix field_validator type annotations."""
    line = lines[line_num]

    # Pattern: def validate_xxx(cls, v, info=None):
    if "info=" in line:
        line = re.sub(
            r"def (\w+)\(cls, v, info=None\):",
            r"def \1(cls, v: Any, info: Any = None) -> Any:",
            line,
        )
    # Pattern: def validate_xxx(cls, v):
    else:
        line = re.sub(
            r"def (\w+)\(cls, v\):",
            r"def \1(cls, v: Any) -> Any:",
            line,
        )

    lines[line_num] = line

    # Ensure typing.Any is imported
    ensure_typing_import(lines, ["Any"])

    return lines


def fix_serializer(lines: list[str], line_num: int) -> list[str]:
    """Fix field_serializer type annotations."""
    line = lines[line_num]

    # Pattern: def serialize_xxx(self, value):
    line = re.sub(
        r"def (\w+)\(self, value\):",
        r"def \1(self, value: Any) -> Any:",
        line,
    )

    lines[line_num] = line

    # Ensure typing.Any is imported
    ensure_typing_import(lines, ["Any"])

    return lines


def fix_method(lines: list[str], line_num: int) -> list[str]:
    """Fix method type annotations."""
    line = lines[line_num]

    # Extract function signature
    match = re.match(r"(\s*)def (\w+)\((.*?)\):", line)
    if not match:
        return lines

    indent, func_name, params = match.groups()

    # Parse parameters
    param_list = [p.strip() for p in params.split(",") if p.strip()]
    typed_params = []

    for param in param_list:
        if ":" in param or param in ("self", "cls"):
            # Already typed or is self/cls
            typed_params.append(param)
        elif "=" in param:
            # Has default value
            name = param.split("=")[0].strip()
            default = param.split("=", 1)[1].strip()
            typed_params.append(f"{name}: Any = {default}")
        else:
            # Needs type annotation
            typed_params.append(f"{param}: Any")

    # Check if return type is needed
    next_lines = "".join(lines[line_num : line_num + 10])
    has_return = "return" in next_lines
    return_type = " -> Any" if has_return else " -> None"

    # Reconstruct line
    new_line = f"{indent}def {func_name}({', '.join(typed_params)}){return_type}:\n"
    lines[line_num] = new_line

    # Ensure typing.Any is imported
    ensure_typing_import(lines, ["Any"])

    return lines


def fix_decorator(lines: list[str], line_num: int) -> list[str]:
    """Fix decorator function type annotations."""
    line = lines[line_num]

    # Pattern: def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
    if "wrapper(" in line:
        # Pattern: def wrapper(*args, **kwargs):
        line = re.sub(
            r"def wrapper\((.*?)\):",
            r"def wrapper(\1) -> Any:",
            line,
        )

    lines[line_num] = line

    # Ensure typing imports
    ensure_typing_import(lines, ["Any", "Callable"])

    return lines


def ensure_typing_import(lines: list[str], types_needed: list[str]) -> None:
    """Ensure typing imports are present."""
    # Find existing typing imports
    typing_import_line = None
    existing_types = set()

    for i, line in enumerate(lines):
        if line.startswith("from typing import"):
            typing_import_line = i
            # Parse existing imports
            imports = line.replace("from typing import", "").strip()
            existing_types = {t.strip() for t in imports.split(",")}
            break

    # Add missing types
    missing_types = [t for t in types_needed if t not in existing_types]

    if not missing_types:
        return

    if typing_import_line is not None:
        # Update existing import
        all_types = sorted(existing_types | set(missing_types))
        new_import = f"from typing import {', '.join(all_types)}\n"
        lines[typing_import_line] = new_import
    else:
        # Add new import after module docstring or at top
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                # Find end of docstring
                if '"""' in line[3:] or "'''" in line[3:]:
                    insert_pos = i + 1
                    break
                for j in range(i + 1, len(lines)):
                    if '"""' in lines[j] or "'''" in lines[j]:
                        insert_pos = j + 1
                        break
                break
            if line.strip() and not line.startswith("#"):
                insert_pos = i
                break

        new_import = f"from typing import {', '.join(sorted(missing_types))}\n"
        lines.insert(insert_pos, new_import)


def fix_error(error: dict[str, Any], dry_run: bool = False) -> bool:
    """Fix a single error."""
    file_path = error["file"]
    line_num = error["line"] - 1  # Convert to 0-indexed

    try:
        lines = read_file_lines(file_path)

        # Detect pattern
        pattern = detect_function_pattern(lines, line_num)

        # Apply fix
        if pattern == "validator":
            lines = fix_validator(lines, line_num)
        elif pattern == "serializer":
            lines = fix_serializer(lines, line_num)
        elif pattern == "decorator":
            lines = fix_decorator(lines, line_num)
        else:
            lines = fix_method(lines, line_num)

        if not dry_run:
            write_file_lines(file_path, lines)

        return True
    except Exception as e:
        print(f"Error fixing {file_path}:{line_num + 1}: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fix MyPy no-untyped-def errors")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--file", help="Fix specific file only")
    args = parser.parse_args()

    print("🔍 Finding no-untyped-def errors...")
    errors = run_mypy(args.file)

    if not errors:
        print("✅ No no-untyped-def errors found!")
        return 0

    print(f"📋 Found {len(errors)} errors")

    # Group errors by file
    by_file: dict[str, list[dict[str, Any]]] = {}
    for error in errors:
        by_file.setdefault(error["file"], []).append(error)

    print(f"📁 Affected files: {len(by_file)}")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be written\n")

    fixed = 0
    failed = 0

    for file_path, file_errors in sorted(by_file.items()):
        print(f"\n📝 {file_path} ({len(file_errors)} errors)")

        for error in sorted(file_errors, key=lambda e: e["line"]):
            if fix_error(error, args.dry_run):
                print(f"  ✓ Line {error['line']}")
                fixed += 1
            else:
                print(f"  ✗ Line {error['line']}")
                failed += 1

    print(f"\n{'📊 DRY RUN SUMMARY' if args.dry_run else '📊 SUMMARY'}")
    print(f"  Fixed: {fixed}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(errors)}")

    if not args.dry_run and fixed > 0:
        print("\n🔍 Verifying fixes...")
        remaining = run_mypy(args.file)
        print(f"  Remaining errors: {len(remaining)}")
        print(f"  Reduction: {len(errors) - len(remaining)} errors")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
