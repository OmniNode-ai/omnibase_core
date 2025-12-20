#!/usr/bin/env python3
"""
Script to fix dict[str, Any] violations in specified directories.

This script replaces dict[str, Any] patterns with strongly-typed alternatives.
"""

import re
import sys
from pathlib import Path


def fix_file(filepath: Path) -> tuple[bool, list[str]]:
    """
    Fix dict[str, Any] violations in a single file.

    Returns:
        Tuple of (was_modified, list_of_changes)
    """
    content = filepath.read_text()
    original_content = content
    changes: list[str] = []

    # Track if we need to add imports
    needs_typed_dict_metadata = False
    needs_typed_dict_serialized = False
    needs_typed_dict_additional = False

    # Pattern 1: get_metadata return type
    if "def get_metadata(self) -> dict[str, Any]:" in content:
        content = content.replace(
            "def get_metadata(self) -> dict[str, Any]:",
            "def get_metadata(self) -> TypedDictMetadataDict:",
        )
        needs_typed_dict_metadata = True
        changes.append("Fixed get_metadata return type")

    # Pattern 2: set_metadata parameter type
    if "def set_metadata(self, metadata: dict[str, Any]) -> bool:" in content:
        content = content.replace(
            "def set_metadata(self, metadata: dict[str, Any]) -> bool:",
            "def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:",
        )
        needs_typed_dict_metadata = True
        changes.append("Fixed set_metadata parameter type")

    # Pattern 3: serialize return type
    if "def serialize(self) -> dict[str, Any]:" in content:
        content = content.replace(
            "def serialize(self) -> dict[str, Any]:",
            "def serialize(self) -> TypedDictSerializedModel:",
        )
        needs_typed_dict_serialized = True
        changes.append("Fixed serialize return type")

    # Pattern 4: from_node_info parameter (specific to model_node_metadata_info.py)
    pattern_from_node_info = r"def from_node_info\(cls, node_info: dict\[str, Any\]\)"
    if re.search(pattern_from_node_info, content):
        content = re.sub(
            pattern_from_node_info,
            "def from_node_info(cls, node_info: TypedDictSerializedModel)",
            content,
        )
        needs_typed_dict_serialized = True
        changes.append("Fixed from_node_info parameter type")

    # Pattern 5: additional_fields field definition
    if "additional_fields: dict[str, Any]" in content:
        content = content.replace(
            "additional_fields: dict[str, Any]",
            "additional_fields: TypedDictAdditionalFields",
        )
        needs_typed_dict_additional = True
        changes.append("Fixed additional_fields field type")

    # Add imports if needed
    if (
        needs_typed_dict_metadata
        or needs_typed_dict_serialized
        or needs_typed_dict_additional
    ):
        # Build import statement
        imports_needed = []
        if needs_typed_dict_metadata:
            imports_needed.append("TypedDictMetadataDict")
        if needs_typed_dict_serialized:
            imports_needed.append("TypedDictSerializedModel")
        if needs_typed_dict_additional:
            imports_needed.append("TypedDictAdditionalFields")

        import_line = (
            f"from omnibase_core.types import {', '.join(sorted(imports_needed))}"
        )

        # Check if import already exists
        if "from omnibase_core.types import" in content:
            # Try to add to existing import
            existing_import_match = re.search(
                r"from omnibase_core\.types import \(([^)]+)\)", content
            )
            if existing_import_match:
                # Multi-line import
                existing_imports = existing_import_match.group(1)
                for imp in imports_needed:
                    if imp not in existing_imports:
                        # Add before closing paren
                        content = content.replace(
                            f"from omnibase_core.types import ({existing_imports})",
                            f"from omnibase_core.types import ({existing_imports.rstrip()}\n    {imp},)",
                        )
            else:
                # Single line import - check if types already imported
                single_import_match = re.search(
                    r"from omnibase_core\.types import ([^\n]+)", content
                )
                if single_import_match:
                    existing = single_import_match.group(1).strip()
                    for imp in imports_needed:
                        if imp not in existing:
                            # Add to existing import
                            new_import = f"{existing.rstrip(',')}, {imp}"
                            content = re.sub(
                                r"from omnibase_core\.types import [^\n]+",
                                f"from omnibase_core.types import {new_import}",
                                content,
                                count=1,
                            )
        else:
            # Add new import after other imports
            # Find the last import line
            import_section_end = 0
            for match in re.finditer(r"^(from|import) .+$", content, re.MULTILINE):
                import_section_end = match.end()

            if import_section_end > 0:
                content = (
                    content[:import_section_end]
                    + f"\n{import_line}"
                    + content[import_section_end:]
                )
            else:
                # Add at the beginning after docstring
                docstring_match = re.search(r'^""".*?"""', content, re.DOTALL)
                if docstring_match:
                    insert_pos = docstring_match.end()
                    content = (
                        content[:insert_pos]
                        + f"\n\n{import_line}"
                        + content[insert_pos:]
                    )
                else:
                    content = import_line + "\n\n" + content

        changes.append(f"Added imports: {', '.join(imports_needed)}")

    # Remove unused 'Any' import if no longer needed
    if (
        "dict[str, Any]" not in content
        and "list[Any]" not in content
        and ": Any" not in content
    ):
        # Check if Any is still used
        if (
            ", Any" in content
            or "Any," in content
            or "Any)" in content
            or "(Any" in content
        ):
            pass  # Any is still used
        elif "from typing import Any" in content:
            content = content.replace("from typing import Any\n", "")
            changes.append("Removed unused Any import")
        elif re.search(r"from typing import [^,\n]+, Any", content):
            content = re.sub(r", Any", "", content)
            changes.append("Removed Any from typing import")
        elif re.search(r"from typing import Any,", content):
            content = re.sub(r"Any, ", "", content)
            changes.append("Removed Any from typing import")

    if content != original_content:
        filepath.write_text(content)
        return True, changes

    return False, changes


def main() -> int:
    """Main entry point."""
    directories = [
        Path("src/omnibase_core/models/node_metadata"),
        Path("src/omnibase_core/models/metadata"),
    ]

    total_fixed = 0
    total_files = 0

    for directory in directories:
        if not directory.exists():
            print(f"Directory not found: {directory}")
            continue

        print(f"\nProcessing {directory}...")

        for filepath in sorted(directory.rglob("*.py")):
            if filepath.name == "__init__.py":
                continue

            total_files += 1
            was_modified, changes = fix_file(filepath)

            if was_modified:
                total_fixed += 1
                print(f"  Fixed: {filepath.name}")
                for change in changes:
                    print(f"    - {change}")

    print(f"\n{'=' * 60}")
    print(f"Total files processed: {total_files}")
    print(f"Total files fixed: {total_fixed}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
