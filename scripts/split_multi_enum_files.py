#!/usr/bin/env python3
"""
Split multi-enum files into individual files per ONEX standards.

For each multi-enum file:
1. Extract each enum class
2. Create a new file enum_<snake_case_name>.py for each enum
3. Update imports across the codebase
4. Remove or update the original file
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    # Remove 'Enum' prefix if present
    if name.startswith("Enum"):
        name = name[4:]

    # Insert underscores before uppercase letters
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def extract_enum_class_code(file_path: Path, class_name: str) -> tuple[str, list[str]]:
    """
    Extract the code for a specific enum class from a file.

    Returns:
        (class_code, imports) - The class definition code and required imports
    """
    content = file_path.read_text()
    tree = ast.parse(content)

    # Find the class definition
    class_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            class_node = node
            break

    if not class_node:
        raise ValueError(f"Class {class_name} not found in {file_path}")

    # Extract the class code (including decorators)
    lines = content.split("\n")

    # Find decorator start line (if any)
    decorator_start = class_node.lineno - 1
    if class_node.decorator_list:
        # Get the first decorator's line number
        decorator_start = class_node.decorator_list[0].lineno - 1

    class_end = class_node.end_lineno

    class_code = "\n".join(lines[decorator_start:class_end])

    # Determine required imports based on bases, decorators, and code content
    import_set = set()

    # Check class bases for special enum types
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            if base.id in ("Enum", "StrEnum", "IntEnum"):
                import_set.add(base.id)
        elif isinstance(base, ast.Attribute):
            if base.attr in ("Enum", "StrEnum", "IntEnum"):
                import_set.add(base.attr)

    # Check decorators for enum-specific decorators like @unique
    for decorator in class_node.decorator_list:
        if isinstance(decorator, ast.Name):
            if decorator.id in ("unique",):
                import_set.add(decorator.id)
        elif isinstance(decorator, ast.Attribute):
            if decorator.attr in ("unique",):
                import_set.add(decorator.attr)

    # Check if auto() is used in the class code
    if "auto()" in class_code:
        import_set.add("auto")

    # Build import statement
    if not import_set:
        # Fallback: assume basic Enum
        imports = ["from enum import Enum"]
    else:
        imports = [f"from enum import {', '.join(sorted(import_set))}"]

    return class_code, imports


def create_enum_file(
    output_dir: Path,
    class_name: str,
    class_code: str,
    imports: list[str],
    original_file: Path,
) -> Path:
    """
    Create a new enum file for a single enum class.

    Returns:
        Path to the created file
    """
    snake_name = pascal_to_snake(class_name)
    filename = f"enum_{snake_name}.py"
    file_path = output_dir / filename

    # Build file content
    docstring = f'"""\n{class_name} enumeration.\n\nExtracted from {original_file.name} per ONEX naming standards.\n"""'

    content_parts = [docstring, "", "\n".join(imports), "", "", class_code, ""]

    content = "\n".join(content_parts)

    file_path.write_text(content)
    print(f"  Created: {file_path.name}")

    return file_path


def get_enum_classes(file_path: Path) -> list[str]:
    """Get all enum class names in a file."""
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


def update_imports_in_file(
    file_path: Path, old_module: str, enum_map: dict[str, str]
) -> bool:
    """
    Update imports in a file to use new enum files.

    Args:
        file_path: File to update
        old_module: Old module path (e.g., 'omnibase_core.enums.enum_metadata')
        enum_map: Map of class names to new module paths
    """
    try:
        content = file_path.read_text()
        modified = False

        # Pattern: from omnibase_core.enums.enum_metadata import EnumLifecycle, EnumMetaType
        for class_name, new_module in enum_map.items():
            # Replace specific imports
            old_import_pattern = rf"from {re.escape(old_module)} import ([^;\n]*{re.escape(class_name)}[^;\n]*)"

            if re.search(old_import_pattern, content):
                # This is complex - need to handle multi-class imports
                # For now, let's handle simple case: from X import Y
                simple_pattern = (
                    rf"from {re.escape(old_module)} import {re.escape(class_name)}\b"
                )
                new_import = f"from {new_module} import {class_name}"

                if re.search(simple_pattern, content):
                    content = re.sub(simple_pattern, new_import, content)
                    modified = True

        if modified:
            file_path.write_text(content)
            return True

        return False
    except Exception as e:
        print(f"Error updating imports in {file_path}: {e}")
        return False


def split_multi_enum_file(file_path: Path, dry_run: bool = False) -> list[Path]:
    """
    Split a multi-enum file into individual files.

    Returns:
        List of created files
    """
    print(f"\nProcessing: {file_path.name}")

    enum_classes = get_enum_classes(file_path)
    if len(enum_classes) <= 1:
        print(f"  Skipping (only {len(enum_classes)} enum)")
        return []

    print(f"  Found {len(enum_classes)} enums: {', '.join(enum_classes)}")

    if dry_run:
        print("  [DRY RUN] Would create:")
        for class_name in enum_classes:
            snake_name = pascal_to_snake(class_name)
            print(f"    - enum_{snake_name}.py")
        return []

    output_dir = file_path.parent
    created_files = []

    for class_name in enum_classes:
        try:
            class_code, imports = extract_enum_class_code(file_path, class_name)
            new_file = create_enum_file(
                output_dir, class_name, class_code, imports, file_path
            )
            created_files.append(new_file)
        except Exception as e:
            print(f"  Error extracting {class_name}: {e}")

    return created_files


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Split multi-enum files per ONEX standards"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--file", help="Specific file to split (relative to src/omnibase_core/enums)"
    )
    args = parser.parse_args()

    src_dir = Path(__file__).parent.parent / "src" / "omnibase_core"

    # Files to split (from our analysis)
    files_to_split = [
        "nodes/enum_effect_types.py",
        "nodes/enum_reducer_types.py",
        "nodes/enum_orchestrator_types.py",
        "enums/enum_metadata.py",
        "enums/enum_validation.py",
        "enums/enum_workflow_testing.py",
        "enums/enum_workflow_execution.py",
        "enums/enum_execution.py",
        "enums/enum_document_freshness_actions.py",
        "enums/enum_device_type.py",
        "enums/enum_schema_types.py",
        "enums/enum_ignore_pattern_source.py",
        "enums/enum_state_management.py",
        "enums/enum_workflow_coordination.py",
    ]

    if args.file:
        files_to_split = [args.file]

    print(f"Splitting {len(files_to_split)} multi-enum files...")
    print()

    total_created = 0

    for rel_path in files_to_split:
        file_path = src_dir / rel_path
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping")
            continue

        created = split_multi_enum_file(file_path, dry_run=args.dry_run)
        total_created += len(created)

    print()
    print(f"Total files created: {total_created}")

    if not args.dry_run:
        print()
        print("Next steps:")
        print("1. Review the created files")
        print("2. Update imports across the codebase")
        print("3. Delete or update the original multi-enum files")
        print("4. Run tests to verify everything works")


if __name__ == "__main__":
    main()
