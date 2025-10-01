#!/usr/bin/env python3
"""
Script to replace ValueError with OnexError throughout the codebase.

Replaces two patterns:
1. ValueError in get_id() methods (ID validation errors)
2. ValueError in enum conversion (invalid enum value errors)
"""

import re
from pathlib import Path

# Pattern 1: ID validation errors in get_id() methods
PATTERN_ID_ERROR = re.compile(
    r"raise ValueError\(\s*"
    r'f"\{self\.__class__\.__name__\} must have a valid ID field "\s*'
    r'f"\(type_id, id, uuid, identifier, etc\.\)\. "\s*'
    r'f"Cannot generate stable ID without UUID field\."\s*'
    r"\)",
    re.MULTILINE | re.DOTALL,
)

REPLACEMENT_ID_ERROR = """raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
                    f"(type_id, id, uuid, identifier, etc.). "
                    f"Cannot generate stable ID without UUID field."
        )"""

# Pattern 2: Enum conversion errors (EnumFunctionType)
PATTERN_ENUM_FUNCTION_TYPE = re.compile(
    r"raise ValueError\(\s*"
    r'f"Invalid function type \'\{function_type\}\' for EnumFunctionType\. "\s*'
    r'f"Must be one of \{.*?\}\."\s*'
    r"\) from e",
    re.MULTILINE | re.DOTALL,
)

REPLACEMENT_ENUM_FUNCTION_TYPE = """raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid function type '{function_type}' for EnumFunctionType. "
                        f"Must be one of {[t.value for t in EnumFunctionType]}.",
            ) from e"""

# Pattern 3: Enum conversion errors (EnumReturnType)
PATTERN_ENUM_RETURN_TYPE = re.compile(
    r"raise ValueError\(\s*"
    r'f"Invalid return type \'\{return_type\}\' for EnumReturnType\. "\s*'
    r'f"Must be one of \{.*?\}\."\s*'
    r"\) from e",
    re.MULTILINE | re.DOTALL,
)

REPLACEMENT_ENUM_RETURN_TYPE = """raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid return type '{return_type}' for EnumReturnType. "
                        f"Must be one of {[t.value for t in EnumReturnType]}.",
            ) from e"""


def add_imports(content: str) -> str:
    """Add necessary imports if not present."""
    needs_error_code = "EnumCoreErrorCode" not in content
    needs_onex_error = "OnexError" not in content

    if not needs_error_code and not needs_onex_error:
        return content

    # Find the import section (after module docstring, before class definitions)
    import_pattern = re.compile(
        r'(""".*?"""\s*\n\s*from __future__ import annotations\s*\n)',
        re.MULTILINE | re.DOTALL,
    )

    match = import_pattern.search(content)
    if not match:
        # Try without __future__ imports
        import_pattern = re.compile(r'(""".*?"""\s*\n)', re.MULTILINE | re.DOTALL)
        match = import_pattern.search(content)

    if match:
        insert_pos = match.end()
        imports_to_add = []

        if needs_error_code:
            imports_to_add.append(
                "from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode\n"
            )
        if needs_onex_error:
            imports_to_add.append(
                "from omnibase_core.exceptions.onex_error import OnexError\n"
            )

        if imports_to_add:
            # Add a blank line before new imports if needed
            new_imports = "\n" + "".join(imports_to_add)
            content = content[:insert_pos] + new_imports + content[insert_pos:]

    return content


def fix_file(filepath: Path) -> tuple[bool, list[str]]:
    """
    Fix ValueError raises in a file.

    Returns:
        (modified, patterns_fixed) where patterns_fixed is a list of pattern names
    """
    content = filepath.read_text(encoding="utf-8")
    original_content = content
    patterns_fixed = []

    # Fix ID validation errors
    if PATTERN_ID_ERROR.search(content):
        content = PATTERN_ID_ERROR.sub(REPLACEMENT_ID_ERROR, content)
        patterns_fixed.append("id_validation")

    # Fix EnumFunctionType errors
    if PATTERN_ENUM_FUNCTION_TYPE.search(content):
        content = PATTERN_ENUM_FUNCTION_TYPE.sub(
            REPLACEMENT_ENUM_FUNCTION_TYPE, content
        )
        patterns_fixed.append("enum_function_type")

    # Fix EnumReturnType errors
    if PATTERN_ENUM_RETURN_TYPE.search(content):
        content = PATTERN_ENUM_RETURN_TYPE.sub(REPLACEMENT_ENUM_RETURN_TYPE, content)
        patterns_fixed.append("enum_return_type")

    # If any patterns were fixed, add necessary imports
    if patterns_fixed:
        content = add_imports(content)

    # Write back if modified
    if content != original_content:
        filepath.write_text(content, encoding="utf-8")
        return True, patterns_fixed

    return False, []


def main():
    """Main entry point."""
    # Files with get_id() ValueError raises
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
    pattern_counts = {
        "id_validation": 0,
        "enum_function_type": 0,
        "enum_return_type": 0,
    }

    for filepath_str in files_to_fix:
        filepath = Path(filepath_str)
        if filepath.exists():
            modified, patterns = fix_file(filepath)
            if modified:
                print(f"✅ Fixed: {filepath}")
                print(f"   Patterns: {', '.join(patterns)}")
                fixed_count += 1
                for pattern in patterns:
                    pattern_counts[pattern] += 1
            else:
                print(f"⏭️  Skipped (no patterns): {filepath}")
        else:
            print(f"❌ Not found: {filepath}")

    print(f"\n✅ Fixed {fixed_count} files")
    print(f"   ID validation errors: {pattern_counts['id_validation']}")
    print(f"   EnumFunctionType errors: {pattern_counts['enum_function_type']}")
    print(f"   EnumReturnType errors: {pattern_counts['enum_return_type']}")


if __name__ == "__main__":
    main()
