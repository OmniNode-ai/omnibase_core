#!/usr/bin/env python3
"""
Pre-commit hook to validate ONEX enum naming conventions.

This script validates:
1. Enum files follow pattern: enum_<name>.py → Enum<Name> (PascalCase)
2. Service files follow pattern: service_<name>.py → Service<Name> (PascalCase)
3. No acronyms in uppercase (RSD→Rsd, LLM→Llm, etc.)
4. No redundant suffixes (EnumIssueTypeEnum → EnumIssueType)

Returns:
    0 if all files are compliant
    1 if violations found
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


def snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_str.split("_"))


def check_enum_file(file_path: Path) -> List[str]:
    """
    Check if enum file follows ONEX naming conventions.

    Returns:
        List of violation messages
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

        # Find all enum class definitions
        enum_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's an Enum class
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
                    enum_classes.append(node.name)

        # Check violations
        if len(enum_classes) == 0:
            violations.append(f"{file_path}: No enum class found")
        elif len(enum_classes) > 1:
            violations.append(
                f"{file_path}: Multiple enums found ({len(enum_classes)}). "
                f"ONEX standard: one enum per file. "
                f"Found: {', '.join(enum_classes)}"
            )
        else:
            actual_class_name = enum_classes[0]
            if actual_class_name != expected_class_name:
                violations.append(
                    f"{file_path}: Expected class '{expected_class_name}', "
                    f"found '{actual_class_name}'"
                )

            # Check for acronym violations (all uppercase in class name)
            if re.search(r"[A-Z]{3,}", actual_class_name):
                violations.append(
                    f"{file_path}: Class name contains uppercase acronym. "
                    f"Use PascalCase: {actual_class_name}"
                )

            # Check for redundant suffix
            if actual_class_name.endswith("Enum") and actual_class_name != "Enum":
                violations.append(
                    f"{file_path}: Redundant 'Enum' suffix in '{actual_class_name}'"
                )

    except Exception as e:
        violations.append(f"{file_path}: Parse error - {e}")

    return violations


def check_service_file(file_path: Path) -> List[str]:
    """
    Check if service file follows ONEX naming conventions.

    Returns:
        List of violation messages
    """
    violations = []

    # Extract the name part from service_<name>.py
    match = re.match(r"service_?(.+)\.py$", file_path.name)
    if not match:
        return violations

    name_part = match.group(1)
    expected_class_name = f"Service{snake_to_pascal(name_part)}"

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        # Find all class definitions with "Service" in name
        service_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if "Service" in node.name or "service" in node.name.lower():
                    service_classes.append(node.name)

        # Check violations
        if service_classes:
            for class_name in service_classes:
                if class_name != expected_class_name:
                    violations.append(
                        f"{file_path}: Expected class '{expected_class_name}', "
                        f"found '{class_name}'"
                    )

    except Exception as e:
        violations.append(f"{file_path}: Parse error - {e}")

    return violations


def main(files: List[str] = None):
    """
    Main validation function.

    Args:
        files: List of file paths to check. If None, checks all enum/service files in src/
    """
    if files is None:
        # Check all files in src/omnibase_core
        src_dir = Path(__file__).parent.parent / "src" / "omnibase_core"
        enum_files = list(src_dir.rglob("enum_*.py"))
        service_files = list(src_dir.rglob("service*.py"))
        all_files = [str(f) for f in enum_files + service_files]
    else:
        all_files = files

    all_violations = []

    for file_path_str in all_files:
        file_path = Path(file_path_str)

        if not file_path.exists():
            continue

        if file_path.name.startswith("enum_"):
            violations = check_enum_file(file_path)
            all_violations.extend(violations)
        elif file_path.name.startswith("service"):
            violations = check_service_file(file_path)
            all_violations.extend(violations)

    if all_violations:
        print("❌ ONEX Naming Convention Violations Found:\n")
        for violation in all_violations:
            print(f"  {violation}")
        print()
        print("Run scripts/audit_naming_conventions.py for detailed analysis")
        return 1

    print("✅ All enum and service files follow ONEX naming conventions")
    return 0


if __name__ == "__main__":
    # If called with file arguments, check those files
    # Otherwise, check all enum/service files
    files = sys.argv[1:] if len(sys.argv) > 1 else None
    sys.exit(main(files))
