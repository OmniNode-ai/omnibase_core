#!/usr/bin/env python3
"""
Audit script to check ONEX naming convention violations.

ONEX Naming Standards:
- Enum files: enum_<name>.py → Class: Enum<Name> (PascalCase)
- Service files: service_<name>.py → Class: Service<Name> (PascalCase)

This script audits:
1. All enum_*.py files for class name violations
2. All service*.py files for class name violations
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_str.split("_"))


def check_enum_file(file_path: Path) -> List[Tuple[str, str, str]]:
    """
    Check if enum file follows ONEX naming conventions.

    Returns:
        List of violations: [(file_path, expected_class, actual_class)]
    """
    violations = []

    # Extract the name part from enum_<name>.py
    match = re.match(r"enum_(.+)\.py$", file_path.name)
    if not match:
        return violations

    name_part = match.group(1)
    expected_class_name = f"Enum{snake_to_pascal(name_part)}"

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        # Find all class definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's an Enum class (inherits from Enum or StrEnum)
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
                    actual_class_name = node.name
                    if actual_class_name != expected_class_name:
                        violations.append(
                            (str(file_path), expected_class_name, actual_class_name)
                        )
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)

    return violations


def check_service_file(file_path: Path) -> List[Tuple[str, str, str]]:
    """
    Check if service file follows ONEX naming conventions.

    Returns:
        List of violations: [(file_path, expected_class, actual_class)]
    """
    violations = []

    # Extract the name part from service_<name>.py or service<name>.py
    match = re.match(r"service_?(.+)\.py$", file_path.name)
    if not match:
        return violations

    name_part = match.group(1)
    expected_class_name = f"Service{snake_to_pascal(name_part)}"

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        # Find all class definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                actual_class_name = node.name
                # Check if class name starts with expected pattern
                if "service" in file_path.name.lower():
                    # For service files, check if any class should follow the pattern
                    # Only flag if the class name contains "Service" but doesn't match
                    if (
                        "Service" in actual_class_name
                        or "service" in actual_class_name.lower()
                    ):
                        if actual_class_name != expected_class_name:
                            violations.append(
                                (str(file_path), expected_class_name, actual_class_name)
                            )
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)

    return violations


def main():
    """Main audit function."""
    src_dir = Path(__file__).parent.parent / "src" / "omnibase_core"

    # Find all enum files
    enum_files = list(src_dir.rglob("enum_*.py"))

    # Find all service files
    service_files = list(src_dir.rglob("service*.py"))

    print(f"Auditing {len(enum_files)} enum files...")
    print(f"Auditing {len(service_files)} service files...")
    print()

    all_violations: Dict[str, List[Tuple[str, str, str]]] = {"enum": [], "service": []}

    # Check enum files
    for enum_file in enum_files:
        violations = check_enum_file(enum_file)
        all_violations["enum"].extend(violations)

    # Check service files
    for service_file in service_files:
        violations = check_service_file(service_file)
        all_violations["service"].extend(violations)

    # Report violations
    total_violations = sum(len(v) for v in all_violations.values())

    if total_violations == 0:
        print("✅ No naming violations found!")
        return 0

    print(f"❌ Found {total_violations} naming violations:\n")

    if all_violations["enum"]:
        print("ENUM VIOLATIONS:")
        print("-" * 80)
        for file_path, expected, actual in all_violations["enum"]:
            print(f"File: {file_path}")
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            print()

    if all_violations["service"]:
        print("SERVICE VIOLATIONS:")
        print("-" * 80)
        for file_path, expected, actual in all_violations["service"]:
            print(f"File: {file_path}")
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
