#!/usr/bin/env python3
"""
Script to automatically fix id(self) fallback patterns in get_id() methods.

Replaces fallback with explicit error raising.
"""

import re
from pathlib import Path

# The pattern to find and replace
OLD_PATTERN = re.compile(
    r'return f"\{self\.__class__\.__name__\}_\{id\(self\)\}"', re.MULTILINE
)

NEW_CODE = """raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
                    f"(type_id, id, uuid, identifier, etc.). "
                    f"Cannot generate stable ID without UUID field."
        )"""


def fix_file(filepath: Path) -> bool:
    """Fix id(self) fallback in a file. Returns True if file was modified."""
    content = filepath.read_text(encoding="utf-8")

    # Check if pattern exists
    if not OLD_PATTERN.search(content):
        return False

    # Replace pattern
    new_content = OLD_PATTERN.sub(NEW_CODE, content)

    # Write back
    filepath.write_text(new_content, encoding="utf-8")
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
            if fix_file(filepath):
                print(f"✅ Fixed: {filepath}")
                fixed_count += 1
            else:
                print(f"⏭️  Skipped (no pattern): {filepath}")
        else:
            print(f"❌ Not found: {filepath}")

    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
