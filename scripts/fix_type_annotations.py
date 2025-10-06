#!/usr/bin/env python3
"""
Script to automatically add type annotations to functions missing them.

This script processes mypy output to identify functions missing type annotations
and adds appropriate type hints based on common patterns.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple


def get_untyped_functions() -> List[Tuple[str, int, str]]:
    """Get list of untyped functions from mypy output."""
    result = subprocess.run(
        [
            "poetry",
            "run",
            "mypy",
            "src/omnibase_core/models/common/",
            "src/omnibase_core/models/core/",
        ],
        capture_output=True,
        text=True,
    )

    untyped = []
    for line in result.stderr.split("\n"):
        if "[no-untyped-def]" in line:
            # Parse: "file.py:123: error: Function is missing ..."
            match = re.match(r"^([^:]+):(\d+):\s+error:\s+(.+)\[no-untyped-def\]", line)
            if match:
                filepath, lineno, error_msg = match.groups()
                untyped.append((filepath, int(lineno), error_msg))

    return untyped


def fix_validator_method(content: str, lineno: int) -> str:
    """Fix field_validator methods that need type hints."""
    lines = content.split("\n")
    if lineno - 1 >= len(lines):
        return content

    line = lines[lineno - 1]

    # Pattern: def validate_xxx(cls, v):
    if "def " in line and "(cls, v)" in line and "-> " not in line:
        # Add type hints for validator
        lines[lineno - 1] = line.replace("(cls, v)", "(cls, v: Any) -> Any")

    return "\n".join(lines)


def fix_init_method(content: str, lineno: int) -> str:
    """Fix __init__ methods that need type hints."""
    lines = content.split("\n")
    if lineno - 1 >= len(lines):
        return content

    line = lines[lineno - 1]

    # Pattern: def __init__(self, **data):
    if "def __init__" in line and "-> None" not in line:
        # Add type hints for __init__
        lines[lineno - 1] = line.replace("**data)", "**data: Any) -> None")

    return "\n".join(lines)


def fix_dunder_method(content: str, lineno: int, method_name: str) -> str:
    """Fix __dunder__ methods that need type hints."""
    lines = content.split("\n")
    if lineno - 1 >= len(lines):
        return content

    line = lines[lineno - 1]

    # Common dunder methods
    if f"def {method_name}" in line and "-> " not in line:
        if method_name in ["__eq__", "__lt__", "__le__", "__gt__", "__ge__"]:
            # Comparison operators
            lines[lineno - 1] = line.replace("other)", "other: object) -> bool")
        elif method_name in ["__add__", "__sub__", "__mul__", "__truediv__"]:
            # Arithmetic operators - return same type
            class_match = re.search(r"class (\w+)", content[:content.find(line)])
            if class_match:
                class_name = class_match.group(1)
                lines[lineno - 1] = line.replace(
                    "other)", f'other: object) -> "{class_name}"'
                )
        elif method_name == "__str__":
            lines[lineno - 1] = line.replace("__str__(self)", "__str__(self) -> str")
        elif method_name == "__repr__":
            lines[lineno - 1] = line.replace("__repr__(self)", "__repr__(self) -> str")
        elif method_name == "__bool__":
            lines[lineno - 1] = line.replace("__bool__(self)", "__bool__(self) -> bool")
        elif method_name == "__len__":
            lines[lineno - 1] = line.replace("__len__(self)", "__len__(self) -> int")

    return "\n".join(lines)


def fix_classmethod(content: str, lineno: int) -> str:
    """Fix classmethods that need type hints."""
    lines = content.split("\n")
    if lineno - 1 >= len(lines):
        return content

    line = lines[lineno - 1]

    # Check if it's a classmethod by looking at previous line
    if lineno >= 2 and "@classmethod" in lines[lineno - 2]:
        # Pattern: def from_xxx(cls, param):
        if "def from_" in line and "-> " not in line:
            # Find class name
            class_match = re.search(r"class (\w+)", content[:content.find(line)])
            if class_match:
                class_name = class_match.group(1)
                # Add return type hint
                if "):" in line:
                    lines[lineno - 1] = line.replace("):", f') -> "{class_name}":')

    return "\n".join(lines)


def add_any_import(content: str) -> str:
    """Add 'from typing import Any' if not present and needed."""
    if "from typing import" in content and "Any" not in content.split("from typing import")[1].split("\n")[0]:
        # Add Any to existing typing import
        for i, line in enumerate(content.split("\n")):
            if line.startswith("from typing import"):
                if "(" in line:
                    # Multi-line import
                    content = content.replace(line, line.replace("import", "import Any,"))
                else:
                    # Single line import
                    content = content.replace(line, line.replace("import", "import Any,"))
                break
    elif "from typing import" not in content:
        # Add new typing import after docstring
        lines = content.split("\n")
        insert_idx = 0

        # Find end of module docstring
        in_docstring = False
        for i, line in enumerate(lines):
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    in_docstring = True
                else:
                    insert_idx = i + 1
                    break
            elif i == 0 and not line.startswith('"""') and not line.startswith("'''"):
                insert_idx = 0
                break

        # Insert import
        if insert_idx < len(lines):
            lines.insert(insert_idx, "")
            lines.insert(insert_idx, "from typing import Any")
            content = "\n".join(lines)

    return content


def fix_file(filepath: str, errors: List[Tuple[int, str]]) -> None:
    """Fix all type annotation errors in a file."""
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return

    content = path.read_text()
    original_content = content

    # Track if we need Any import
    needs_any = False

    # Sort errors by line number (descending) to avoid line number shifts
    errors_sorted = sorted(errors, key=lambda x: x[0], reverse=True)

    for lineno, error_msg in errors_sorted:
        lines = content.split("\n")
        if lineno - 1 >= len(lines):
            continue

        line = lines[lineno - 1]

        # Determine fix strategy based on error message and line content
        if "__init__" in line:
            content = fix_init_method(content, lineno)
            needs_any = True
        elif any(f"def {m}" in line for m in ["__eq__", "__lt__", "__le__", "__gt__", "__ge__", "__add__", "__sub__", "__mul__", "__truediv__"]):
            for method in ["__eq__", "__lt__", "__le__", "__gt__", "__ge__", "__add__", "__sub__", "__mul__", "__truediv__"]:
                if f"def {method}" in line:
                    content = fix_dunder_method(content, lineno, method)
                    break
        elif "@field_validator" in "\n".join(lines[max(0, lineno - 3):lineno]):
            content = fix_validator_method(content, lineno)
            needs_any = True
        elif "@classmethod" in "\n".join(lines[max(0, lineno - 3):lineno]):
            content = fix_classmethod(content, lineno)
        else:
            # Generic function - add -> None if no return type
            if "-> " not in line and "def " in line:
                # Check if function has parameters
                if "(**" in line or "(self, " in line or "(cls, " in line:
                    needs_any = True
                # Add -> None as default
                content = content.replace(line, line.replace("):", ") -> None:"))

    # Add Any import if needed
    if needs_any and content != original_content:
        content = add_any_import(content)

    # Only write if changed
    if content != original_content:
        path.write_text(content)
        print(f"✓ Fixed {len(errors)} annotations in {filepath}")


def main():
    """Main entry point."""
    print("Gathering untyped functions...")
    untyped_functions = get_untyped_functions()

    if not untyped_functions:
        print("No untyped functions found!")
        return

    print(f"Found {len(untyped_functions)} untyped functions")

    # Group by file
    by_file: Dict[str, List[Tuple[int, str]]] = {}
    for filepath, lineno, error_msg in untyped_functions:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append((lineno, error_msg))

    # Fix each file
    for filepath, errors in sorted(by_file.items()):
        print(f"\nProcessing {filepath} ({len(errors)} errors)...")
        fix_file(filepath, errors)

    print("\n✅ Type annotation fixes complete!")
    print("\nVerifying with mypy...")
    subprocess.run(
        [
            "poetry",
            "run",
            "mypy",
            "src/omnibase_core/models/common/",
            "src/omnibase_core/models/core/",
        ]
    )


if __name__ == "__main__":
    main()
