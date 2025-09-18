#!/usr/bin/env python3
"""
Script to systematically fix dict[str, Any] patterns in model files.
Focuses on the most common field patterns while preserving method signatures.
"""

import os
import re
from pathlib import Path

# Common field patterns to replace with ModelGenericMetadata
FIELD_PATTERNS = [
    (
        r"metadata: dict\[str, Any\] = Field\(",
        "metadata: ModelGenericMetadata | None = Field(",
    ),
    (
        r"debug_info: dict\[str, Any\] = Field\(",
        "debug_info: ModelGenericMetadata | None = Field(",
    ),
    (
        r"context: dict\[str, Any\] \| None = Field\(",
        "context: ModelGenericMetadata | None = Field(",
    ),
    (
        r"additional_data: dict\[str, Any\] \| None = Field\(",
        "additional_data: ModelGenericMetadata | None = Field(",
    ),
    (
        r"custom_data: dict\[str, Any\] \| None = Field\(",
        "custom_data: ModelGenericMetadata | None = Field(",
    ),
    (
        r"data: dict\[str, Any\] \| None = Field\(",
        "data: ModelGenericMetadata | None = Field(",
    ),
    (
        r"raw_data: dict\[str, Any\] \| None = Field\(",
        "raw_data: ModelGenericMetadata | None = Field(",
    ),
    (
        r"config_details: dict\[str, Any\] \| None = Field\(",
        "config_details: ModelGenericMetadata | None = Field(",
    ),
    (
        r"output_json: dict\[str, Any\] \| None = Field\(",
        "output_json: ModelGenericMetadata | None = Field(",
    ),
    (
        r"custom_parameters: dict\[str, Any\] = Field\(",
        "custom_parameters: ModelGenericMetadata | None = Field(",
    ),
    (
        r"service_config: dict\[str, Any\] = Field\(",
        "service_config: ModelGenericMetadata | None = Field(",
    ),
    (
        r"discovery_filters: dict\[str, Any\] = Field\(",
        "discovery_filters: ModelGenericMetadata | None = Field(",
    ),
    (
        r"infrastructure: dict\[str, Any\] \| None = Field\(",
        "infrastructure: ModelGenericMetadata | None = Field(",
    ),
]

# Fields that should use specific model types
SPECIFIC_PATTERNS = [
    (r"payload_schema: dict\[str, Any\]", "payload_schema: ModelJsonSchema"),
    (r"schema_def: dict\[str, Any\]", "schema_def: ModelJsonSchema"),
]


def needs_generic_metadata_import(content):
    """Check if file needs ModelGenericMetadata import."""
    return (
        "ModelGenericMetadata" in content
        and "from .model_generic_metadata import ModelGenericMetadata" not in content
    )


def needs_json_schema_import(content):
    """Check if file needs ModelJsonSchema import."""
    return (
        "ModelJsonSchema" in content
        and "from .model_json_schema import ModelJsonSchema" not in content
    )


def add_imports(content):
    """Add necessary imports to the file."""
    lines = content.split("\n")

    # Find the last import line
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("from ") or line.strip().startswith("import "):
            last_import_idx = i

    imports_to_add = []

    if needs_generic_metadata_import(content):
        imports_to_add.append(
            "from .model_generic_metadata import ModelGenericMetadata"
        )

    if needs_json_schema_import(content):
        imports_to_add.append("from .model_json_schema import ModelJsonSchema")

    if imports_to_add and last_import_idx >= 0:
        # Insert after the last import
        for import_line in imports_to_add:
            lines.insert(last_import_idx + 1, import_line)
            last_import_idx += 1

    return "\n".join(lines)


def fix_file(file_path):
    """Fix dict[str, Any] patterns in a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        changes_made = []

        # Apply field patterns
        for pattern, replacement in FIELD_PATTERNS:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes_made.append(f"Replaced field pattern: {pattern}")

        # Apply specific patterns
        for pattern, replacement in SPECIFIC_PATTERNS:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes_made.append(f"Replaced specific pattern: {pattern}")

        # Add necessary imports if patterns were changed
        if changes_made:
            content = add_imports(content)
            changes_made.append("Added necessary imports")

        # Only write if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Fixed {file_path.name}: {len(changes_made)} changes")
            for change in changes_made:
                print(f"   - {change}")
        else:
            print(f"⚪ No changes needed for {file_path.name}")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")


def main():
    """Main function to process all model files."""
    models_dir = Path(
        "/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/core"
    )

    if not models_dir.exists():
        print(f"❌ Models directory not found: {models_dir}")
        return

    model_files = list(models_dir.glob("*.py"))
    print(f"📁 Processing {len(model_files)} model files...")

    total_fixed = 0
    for file_path in model_files:
        if file_path.name.startswith("model_"):
            print(f"\n🔧 Processing {file_path.name}...")
            fix_file(file_path)
            total_fixed += 1

    print(f"\n🎉 Completed processing {total_fixed} files")
    print("\n📊 Checking remaining dict[str, Any] patterns...")

    # Check remaining patterns
    remaining_files = []
    for file_path in model_files:
        if file_path.name.startswith("model_"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "dict[str, Any]" in content:
                    # Filter out method signatures and from_dict parameters
                    lines_with_dict = [
                        line.strip()
                        for line in content.split("\n")
                        if "dict[str, Any]" in line
                    ]
                    field_patterns = [
                        line
                        for line in lines_with_dict
                        if "= Field(" in line or "RootModel[" in line
                    ]
                    if field_patterns:
                        remaining_files.append((file_path.name, field_patterns))
            except Exception as e:
                print(f"Error checking {file_path}: {e}")

    if remaining_files:
        print(
            f"\n⚠️  {len(remaining_files)} files still have dict[str, Any] field patterns:"
        )
        for filename, patterns in remaining_files:
            print(f"   📄 {filename}:")
            for pattern in patterns:
                print(f"      - {pattern}")
    else:
        print("✅ All field patterns have been fixed!")


if __name__ == "__main__":
    main()
