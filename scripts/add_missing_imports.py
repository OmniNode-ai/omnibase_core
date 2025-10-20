#!/usr/bin/env python3
"""
Script to add missing OnexError and EnumCoreErrorCode imports to files.
"""

import re
from pathlib import Path


def add_imports_to_file(filepath: Path) -> bool:
    """Add missing imports to a file if OnexError or EnumCoreErrorCode are used."""
    content = filepath.read_text(encoding="utf-8")

    # Check if OnexError or EnumCoreErrorCode are used
    uses_onex_error = "OnexError" in content
    uses_error_code = "EnumCoreErrorCode" in content

    # Check if already imported
    has_onex_error_import = (
        "from omnibase_core.exceptions.onex_error import OnexError" in content
    )
    has_error_code_import = (
        "from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode"
        in content
    )

    needs_onex_error = uses_onex_error and not has_onex_error_import
    needs_error_code = uses_error_code and not has_error_code_import

    if not needs_onex_error and not needs_error_code:
        return False

    # Find where to insert imports (after from __future__ import annotations)
    # Look for the line after "from __future__ import annotations"
    lines = content.split("\n")
    insert_index = -1

    for i, line in enumerate(lines):
        if "from __future__ import annotations" in line:
            insert_index = i + 1
            break

    if insert_index == -1:
        # Look for first import line
        for i, line in enumerate(lines):
            if line.startswith(("from ", "import ")):
                insert_index = i
                break

    if insert_index == -1:
        print(f"⚠️  Could not find insert point for {filepath}")
        return False

    # Add blank line if needed
    if insert_index < len(lines) and lines[insert_index].strip():
        lines.insert(insert_index, "")
        insert_index += 1

    # Add imports in reverse order so indices don't shift
    imports_added = []
    if needs_error_code:
        lines.insert(
            insert_index,
            "from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode",
        )
        imports_added.append("EnumCoreErrorCode")
    if needs_onex_error:
        lines.insert(
            insert_index, "from omnibase_core.exceptions.onex_error import OnexError"
        )
        imports_added.append("OnexError")

    # Write back
    new_content = "\n".join(lines)
    filepath.write_text(new_content, encoding="utf-8")

    print(f"✅ Added imports to {filepath}: {', '.join(imports_added)}")
    return True


def main():
    """Main entry point."""
    files_to_fix = [
        "src/omnibase_core/models/nodes/model_function_node.py",
        "src/omnibase_core/models/nodes/model_node_execution_settings.py",
        "src/omnibase_core/models/nodes/model_function_node_metadata.py",
        "src/omnibase_core/models/nodes/model_node_capability.py",
        "src/omnibase_core/models/nodes/model_function_node_core.py",
        "src/omnibase_core/models/nodes/model_node_core_metadata.py",
        "src/omnibase_core/models/nodes/model_node_configuration.py",
        "src/omnibase_core/models/nodes/model_node_capabilities_info.py",
        "src/omnibase_core/models/nodes/model_node_information_summary.py",
        "src/omnibase_core/models/nodes/model_node_feature_flags.py",
        "src/omnibase_core/models/nodes/model_function_node_summary.py",
        "src/omnibase_core/models/nodes/model_node_connection_settings.py",
        "src/omnibase_core/models/nodes/model_node_capabilities_summary.py",
        "src/omnibase_core/models/nodes/model_function_node_performance.py",
        "src/omnibase_core/models/nodes/model_node_resource_limits.py",
        "src/omnibase_core/models/nodes/model_node_core_info_summary.py",
        "src/omnibase_core/models/nodes/model_node_metadata_info.py",
        "src/omnibase_core/models/nodes/model_node_information.py",
        "src/omnibase_core/models/nodes/model_node_core_info.py",
        "src/omnibase_core/models/nodes/model_node_configuration_summary.py",
        "src/omnibase_core/models/nodes/model_node_type.py",
        "src/omnibase_core/models/nodes/model_function_documentation.py",
        "src/omnibase_core/models/nodes/model_function_relationships.py",
        "src/omnibase_core/models/nodes/model_function_deprecation_info.py",
        "src/omnibase_core/models/nodes/model_node_organization_metadata.py",
        "src/omnibase_core/models/operations/model_system_metadata.py",
        "src/omnibase_core/models/operations/model_message_payload.py",
        "src/omnibase_core/models/operations/model_event_metadata.py",
        "src/omnibase_core/models/operations/model_computation_output_data.py",
        "src/omnibase_core/models/operations/model_workflow_parameters.py",
        "src/omnibase_core/models/operations/model_computation_input_data.py",
        "src/omnibase_core/models/operations/model_operation_parameters_base.py",
        "src/omnibase_core/models/operations/model_effect_parameters.py",
        "src/omnibase_core/models/operations/model_workflow_instance_metadata.py",
        "src/omnibase_core/models/operations/model_event_payload.py",
        "src/omnibase_core/models/operations/model_workflow_payload.py",
        "src/omnibase_core/models/operations/model_operation_payload.py",
    ]

    fixed_count = 0
    for filepath_str in files_to_fix:
        filepath = Path(filepath_str)
        if filepath.exists():
            if add_imports_to_file(filepath):
                fixed_count += 1
        else:
            print(f"❌ Not found: {filepath}")

    print(f"\n✅ Added imports to {fixed_count} files")


if __name__ == "__main__":
    main()
