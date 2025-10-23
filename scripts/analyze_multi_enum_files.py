#!/usr/bin/env python3
"""
Analyze multi-enum files to determine fix strategy.

Categorizes violations into:
1. Files that should be split (multiple unrelated enums)
2. Files that need simple rename (one enum, wrong name)
3. Files that are intentionally grouped (related enums with __all__ export)
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List


def snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_str.split("_"))


def get_enum_classes(file_path: Path) -> list[str]:
    """
    Get all enum classes in a file.

    Returns:
        List of enum class names
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_enum = False
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        if base.id in ("Enum", "StrEnum", "IntEnum"):
                            is_enum = True
                            break
                    elif isinstance(base, ast.Attribute):
                        if base.attr in ("Enum", "StrEnum", "IntEnum"):
                            is_enum = True
                            break

                if is_enum:
                    classes.append(node.name)

        return classes
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        return []


def has_all_export(file_path: Path) -> bool:
    """Check if file has __all__ export list."""
    try:
        content = file_path.read_text()
        return "__all__" in content
    except Exception:
        return False


def analyze_file(file_path: Path) -> dict:
    """Analyze a multi-enum file."""
    match = re.match(r"enum_(.+)\.py$", file_path.name)
    if not match:
        return {}

    name_part = match.group(1)
    expected_class_name = f"Enum{snake_to_pascal(name_part)}"

    enum_classes = get_enum_classes(file_path)
    has_all = has_all_export(file_path)

    return {
        "file_path": str(file_path),
        "file_name": file_path.name,
        "expected_class": expected_class_name,
        "actual_classes": enum_classes,
        "num_enums": len(enum_classes),
        "has_all_export": has_all,
    }


def categorize_violation(analysis: dict) -> str:
    """
    Categorize the type of violation.

    Categories:
    - single_rename: One enum, just needs rename
    - intentional_group: Multiple related enums with __all__ export
    - split_required: Multiple unrelated enums, should be split
    """
    if analysis["num_enums"] == 1:
        if analysis["actual_classes"][0] == analysis["expected_class"]:
            return "compliant"
        else:
            return "single_rename"
    elif analysis["num_enums"] > 1:
        if analysis["has_all_export"]:
            return "intentional_group"
        else:
            return "split_required"
    else:
        return "unknown"


def main():
    """Main analysis function."""
    src_dir = Path(__file__).parent.parent / "src" / "omnibase_core"

    # Find all enum files
    enum_files = list(src_dir.rglob("enum_*.py"))

    print(f"Analyzing {len(enum_files)} enum files...\n")

    violations = {
        "single_rename": [],
        "intentional_group": [],
        "split_required": [],
        "compliant": [],
        "unknown": [],
    }

    for enum_file in enum_files:
        analysis = analyze_file(enum_file)
        if not analysis:
            continue

        category = categorize_violation(analysis)
        violations[category].append(analysis)

    # Print summary
    print("=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print()

    total_violations = (
        len(violations["single_rename"])
        + len(violations["intentional_group"])
        + len(violations["split_required"])
    )
    print(f"Total violations: {total_violations}")
    print(f"  Single rename needed: {len(violations['single_rename'])}")
    print(f"  Intentionally grouped: {len(violations['intentional_group'])}")
    print(f"  Split required: {len(violations['split_required'])}")
    print(f"Compliant files: {len(violations['compliant'])}")
    print()

    # Print details for each category
    if violations["single_rename"]:
        print("=" * 80)
        print("SINGLE RENAME NEEDED (easy fix)")
        print("=" * 80)
        for v in violations["single_rename"]:
            print(f"File: {v['file_name']}")
            print(f"  Expected: {v['expected_class']}")
            print(f"  Actual:   {v['actual_classes'][0]}")
            print()

    if violations["intentional_group"]:
        print("=" * 80)
        print("INTENTIONALLY GROUPED (need to split per ONEX standards)")
        print("=" * 80)
        for v in violations["intentional_group"]:
            print(f"File: {v['file_name']}")
            print(f"  Contains {v['num_enums']} enums:")
            for cls in v["actual_classes"]:
                print(f"    - {cls}")
            print(f"  Has __all__ export: {v['has_all_export']}")
            print()

    if violations["split_required"]:
        print("=" * 80)
        print("SPLIT REQUIRED (no __all__ export)")
        print("=" * 80)
        for v in violations["split_required"]:
            print(f"File: {v['file_name']}")
            print(f"  Contains {v['num_enums']} enums:")
            for cls in v["actual_classes"]:
                print(f"    - {cls}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
