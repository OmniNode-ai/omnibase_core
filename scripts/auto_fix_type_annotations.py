#!/usr/bin/env python3
"""
Automated Type Annotation Fixer

This script automatically adds type annotations to functions based on common patterns
observed in the omnibase_core models.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def run_mypy(paths: List[str]) -> List[Tuple[str, int, str]]:
    """Run mypy and extract no-untyped-def errors."""
    cmd = ["poetry", "run", "mypy"] + paths
    result = subprocess.run(cmd, capture_output=True, text=True)

    errors = []
    # Check both stdout and stderr
    output = result.stdout + result.stderr
    for line in output.split("\n"):
        if "[no-untyped-def]" in line:
            match = re.match(r"^([^:]+):(\d+):\s+error:\s+(.+)\[no-untyped-def\]", line)
            if match:
                filepath, lineno, msg = match.groups()
                errors.append((filepath, int(lineno), msg))

    return errors


def read_file_lines(filepath: str) -> List[str]:
    """Read file into lines."""
    return Path(filepath).read_text().split("\n")


def write_file_lines(filepath: str, lines: List[str]) -> None:
    """Write lines back to file."""
    Path(filepath).write_text("\n".join(lines))


def ensure_imports(lines: List[str], imports_needed: set[str]) -> List[str]:
    """Ensure necessary imports are present."""
    # Find imports section
    import_idx = None
    typing_import_idx = None

    for i, line in enumerate(lines):
        if line.startswith("from typing import"):
            typing_import_idx = i
        elif line.startswith("from pydantic"):
            import_idx = i

    # Add missing imports
    if "Any" in imports_needed:
        if typing_import_idx is not None:
            # Add to existing typing import
            if "Any" not in lines[typing_import_idx]:
                lines[typing_import_idx] = lines[typing_import_idx].replace(
                    "import ", "import Any, "
                )
        else:
            # Add new typing import
            insert_pos = import_idx if import_idx else 0
            lines.insert(insert_pos, "from typing import Any")

    if "ValidationInfo" in imports_needed:
        # Check if pydantic_core import exists
        has_pydantic_core = any(
            "from pydantic_core import" in line for line in lines
        )
        if not has_pydantic_core:
            insert_pos = typing_import_idx + 1 if typing_import_idx else 0
            lines.insert(insert_pos, "from pydantic_core import ValidationInfo")

    return lines


def fix_function_at_line(lines: List[str], lineno: int, error_msg: str) -> Tuple[List[str], set[str]]:
    """Fix function at specific line number."""
    imports_needed = set()
    idx = lineno - 1

    if idx >= len(lines):
        return lines, imports_needed

    line = lines[idx]

    # Pattern: field_validator with info parameter
    if "@field_validator" in "\n".join(lines[max(0, idx - 3):idx]):
        # Fix validator: def validate_xxx(cls, v, info) -> type:
        if "(cls, v, info)" in line or "(cls, v," in line:
            # Determine return type from field name
            if "str" in line or "string" in line.lower():
                return_type = "str | None"
            elif "int" in line or "integer" in line.lower():
                return_type = "int | None"
            elif "float" in line.lower():
                return_type = "float | None"
            elif "bool" in line.lower():
                return_type = "bool | None"
            elif "list" in line.lower():
                if "string" in line.lower():
                    return_type = "list[str] | None"
                elif "int" in line.lower():
                    return_type = "list[int] | None"
                else:
                    return_type = "Any"
            else:
                return_type = "Any"

            # Fix the signature
            if "(cls, v, info)" in line:
                lines[idx] = line.replace(
                    "(cls, v, info)",
                    f"(cls, v: {return_type}, info: ValidationInfo) -> {return_type}"
                )
            elif "(cls, v," in line:
                lines[idx] = re.sub(
                    r'\(cls, v,([^)]*)\)',
                    f'(cls, v: {return_type}, info: ValidationInfo) -> {return_type}',
                    line
                )
            imports_needed.add("Any")
            imports_needed.add("ValidationInfo")

        # Fix validator: def validate_xxx(cls, v) -> type:
        elif "(cls, v)" in line and "-> " not in line:
            # Simple validator
            lines[idx] = line.replace("(cls, v)", "(cls, v: Any) -> Any")
            imports_needed.add("Any")

    # Pattern: classmethod with **kwargs
    elif "@classmethod" in "\n".join(lines[max(0, idx - 3):idx]):
        if "**kwargs)" in line and "**kwargs: Any)" not in line:
            lines[idx] = line.replace("**kwargs)", "**kwargs: Any)")
            imports_needed.add("Any")

    # Pattern: __init__ method
    elif "def __init__" in line:
        if "**data)" in line and "-> None" not in line:
            lines[idx] = line.replace("**data)", "**data: Any) -> None")
            imports_needed.add("Any")

    # Pattern: comparison operators
    elif any(f"def {op}" in line for op in ["__eq__", "__lt__", "__le__", "__gt__", "__ge__"]):
        if "other)" in line and "-> bool" not in line:
            lines[idx] = line.replace("other)", "other: object) -> bool")

    # Pattern: arithmetic operators
    elif any(f"def {op}" in line for op in ["__add__", "__sub__", "__mul__", "__truediv__"]):
        if "other)" in line and "-> " not in line:
            # Extract class name
            class_name = None
            for i in range(idx, -1, -1):
                if lines[i].startswith("class "):
                    class_name = lines[i].split("(")[0].replace("class ", "").strip()
                    break
            if class_name:
                lines[idx] = line.replace("other)", f'other: object) -> "{class_name}"')

    # Pattern: methods missing return type
    elif "def " in line and "):" in line and "-> " not in line:
        # Add -> None as default for void functions
        lines[idx] = line.replace("):", ") -> None:")

    return lines, imports_needed


def fix_file(filepath: str, errors: List[Tuple[int, str]]) -> int:
    """Fix all errors in a file."""
    lines = read_file_lines(filepath)
    all_imports_needed = set()

    # Sort errors by line number (descending) to avoid index shifts
    errors_sorted = sorted(errors, key=lambda x: x[0], reverse=True)

    for lineno, error_msg in errors_sorted:
        lines, imports_needed = fix_function_at_line(lines, lineno, error_msg)
        all_imports_needed.update(imports_needed)

    # Add necessary imports
    if all_imports_needed:
        lines = ensure_imports(lines, all_imports_needed)

    write_file_lines(filepath, lines)
    return len(errors)


def main():
    """Main entry point."""
    print("🔍 Scanning for untyped functions...")

    paths = ["src/omnibase_core/models/common/", "src/omnibase_core/models/core/"]
    errors = run_mypy(paths)

    if not errors:
        print("✅ No untyped functions found!")
        return 0

    print(f"📝 Found {len(errors)} untyped functions")

    # Group by file
    by_file: Dict[str, List[Tuple[int, str]]] = {}
    for filepath, lineno, error_msg in errors:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append((lineno, error_msg))

    # Fix each file
    total_fixed = 0
    for filepath, file_errors in sorted(by_file.items()):
        print(f"  Fixing {Path(filepath).name} ({len(file_errors)} errors)...", end=" ")
        fixed = fix_file(filepath, file_errors)
        total_fixed += fixed
        print(f"✓ {fixed} fixed")

    print(f"\n✅ Fixed {total_fixed} function annotations!")

    # Verify
    print("\n🔍 Verifying fixes...")
    remaining = run_mypy(paths)
    if remaining:
        print(f"⚠️  {len(remaining)} errors remain (may need manual review)")
        return 1
    else:
        print("✅ All type annotation errors fixed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
