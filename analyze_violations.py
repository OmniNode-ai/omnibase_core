#!/usr/bin/env python3
"""Script to analyze and categorize single-class-per-file violations."""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


def analyze_file(filepath: Path) -> tuple[int, int, list[str]]:
    """Analyze a Python file for classes and enums."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        classes = []
        enums = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's an enum by looking for Enum inheritance
                is_enum = False
                for base in node.bases:
                    if (isinstance(base, ast.Name) and base.id == "Enum") or (
                        isinstance(base, ast.Attribute) and base.attr == "Enum"
                    ):
                        is_enum = True
                        break

                if is_enum:
                    enums.append(node.name)
                else:
                    classes.append(node.name)

        return len(classes), len(enums), classes + enums
    except Exception:
        return 0, 0, []


def get_violations():
    """Get all violation files and their details."""
    violations = []
    src_dir = Path("src/omnibase_core")

    for py_file in src_dir.rglob("*.py"):
        # Skip exclusions
        if any(
            excluded in str(py_file)
            for excluded in ["tests/", "archived/", "archive/", "scripts/validation/"]
        ):
            continue
        if py_file.name == "__init__.py":
            continue

        class_count, enum_count, all_classes = analyze_file(py_file)

        if class_count > 1 or (class_count > 0 and enum_count > 0):
            violations.append(
                {
                    "file": str(py_file),
                    "class_count": class_count,
                    "enum_count": enum_count,
                    "classes": all_classes,
                }
            )

    return violations


def main():
    """Main function to analyze violations."""
    violations = get_violations()

    print(f"Total violations: {len(violations)}")
    print("\nViolations by category:")

    # Sort by class count (highest first)
    violations.sort(key=lambda x: x["class_count"], reverse=True)

    for i, violation in enumerate(violations, 1):
        print(f"\n{i:3d}. {violation['file']}")
        print(
            f"     Classes: {violation['class_count']}, Enums: {violation['enum_count']}"
        )
        print(f"     Classes: {', '.join(violation['classes'])}")

    return violations


if __name__ == "__main__":
    main()
