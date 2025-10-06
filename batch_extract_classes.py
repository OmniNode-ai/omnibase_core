#!/usr/bin/env python3
"""Batch extract classes from violation files."""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


def read_file_content(filepath: Path) -> str:
    """Read file content."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def write_file_content(filepath: Path, content: str) -> bool:
    """Write file content."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False


def extract_classes_from_content(
    content: str, target_classes: List[str]
) -> Dict[str, str]:
    """Extract specific classes from file content."""
    try:
        tree = ast.parse(content)
        class_contents = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in target_classes:
                # Get the lines for this class
                start_line = node.lineno - 1  # 0-based
                end_line = node.end_lineno

                lines = content.split("\n")
                class_lines = lines[start_line:end_line]
                class_content = "\n".join(class_lines)
                class_contents[node.name] = class_content

        return class_contents
    except Exception as e:
        print(f"Error parsing content: {e}")
        return {}


def remove_class_from_content(content: str, class_name: str) -> str:
    """Remove a class from content."""
    try:
        tree = ast.parse(content)
        lines = content.split("\n")
        filtered_lines = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                start_line = node.lineno - 1
                end_line = node.end_lineno

                # Keep lines before this class
                for i in range(start_line):
                    if i < len(lines):
                        filtered_lines.append(lines[i])

                # Skip this class
                # Keep lines after this class
                for i in range(end_line, len(lines)):
                    filtered_lines.append(lines[i])

                return "\n".join(filtered_lines)

        return content
    except Exception as e:
        print(f"Error removing class {class_name}: {e}")
        return content


def process_violation(violation_info: Dict) -> bool:
    """Process a single violation."""
    filepath = Path(violation_info["file"])
    classes = violation_info["classes"]

    print(f"Processing {filepath}")

    content = read_file_content(filepath)
    if not content:
        return False

    # Extract classes
    class_contents = extract_classes_from_content(content, classes)
    if not class_contents:
        print(f"  No classes found to extract")
        return False

    # Determine which classes to extract (keep main class in original file)
    main_class = None
    extracted_classes = []

    # Heuristic: keep the class that matches the filename
    filename = filepath.stem
    for class_name in classes:
        if class_name.lower().replace("model", "") == filename.lower().replace(
            "model", ""
        ):
            main_class = class_name
        else:
            extracted_classes.append(class_name)

    # If no clear match, keep the first one
    if not main_class:
        main_class = classes[0]
        extracted_classes = classes[1:]
    elif main_class in extracted_classes:
        extracted_classes.remove(main_class)

    print(f"  Main class: {main_class}")
    print(f"  Extracted classes: {extracted_classes}")

    # Create new files for extracted classes
    for class_name in extracted_classes:
        # Generate new filename
        new_filename = f"model_{class_name.lower().replace('model', '')}.py"
        new_filepath = filepath.parent / new_filename

        # Create new file
        if class_name in class_contents:
            # Add necessary imports
            new_content = class_contents[class_name]

            # Add imports if needed
            if "BaseModel" in new_content and "from pydantic import" not in new_content:
                new_content = "from pydantic import BaseModel, Field\n\n" + new_content

            if "Enum" in new_content and "from enum import Enum" not in new_content:
                new_content = "from enum import Enum\n\n" + new_content

            write_file_content(new_filepath, new_content)
            print(f"  ✓ Created {new_filepath}")

    # Update original file
    if main_class and main_class in class_contents:
        # Remove extracted classes from original
        updated_content = content
        for class_name in extracted_classes:
            if class_name in class_contents:
                updated_content = remove_class_from_content(updated_content, class_name)

        # Add imports for extracted classes if needed
        if extracted_classes:
            imports_section = []
            for class_name in extracted_classes:
                new_filename = f"model_{class_name.lower().replace('model', '')}.py"
                imports_section.append(f"from .{new_filename[:-3]} import {class_name}")

            if imports_section:
                # Find where to insert imports (after existing imports)
                lines = updated_content.split("\n")
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith("from ") or line.startswith("import "):
                        insert_pos = i + 1
                    elif line.strip() == "" and insert_pos > 0:
                        insert_pos = i + 1
                    elif (
                        line.strip()
                        and not line.startswith("from ")
                        and not line.startswith("import ")
                        and insert_pos > 0
                    ):
                        break

                # Insert imports
                for imp in reversed(imports_section):
                    lines.insert(insert_pos, imp)

                updated_content = "\n".join(lines)

        write_file_content(filepath, updated_content)
        print(f"  ✓ Updated {filepath}")

    return True


def main():
    """Main function."""
    # Define final batch of violations (41-59)
    violations = [
        {
            "file": "src/omnibase_core/models/logging/model_log_node_identifier.py",
            "classes": ["ModelLogNodeIdentifierUUID", "ModelLogNodeIdentifierString"],
        },
        {
            "file": "src/omnibase_core/models/contracts/subcontracts/model_event_routing.py",
            "classes": ["ModelRetryPolicy", "ModelEventRouting"],
        },
        {
            "file": "src/omnibase_core/models/contracts/subcontracts/model_fsm_transition_action.py",
            "classes": ["ModelActionConfigValue", "ModelFSMTransitionAction"],
        },
        {
            "file": "src/omnibase_core/models/core/model_generic_value.py",
            "classes": ["ModelGenericValue", "EnumValueType"],
        },
        {
            "file": "src/omnibase_core/models/core/model_metadata_tool_info.py",
            "classes": [
                "ModelMetadataToolInfo",
                "EnumMetadataToolType",
                "EnumMetadataToolStatus",
                "EnumMetadataToolComplexity",
            ],
        },
        {
            "file": "src/omnibase_core/models/core/model_business_impact.py",
            "classes": ["ModelBusinessImpact", "EnumImpactSeverity"],
        },
        {
            "file": "src/omnibase_core/models/core/model_tool_metadata.py",
            "classes": [
                "ModelToolMetadata",
                "EnumToolRegistrationStatus",
                "EnumToolCapabilityLevel",
                "EnumToolCategory",
                "EnumToolCompatibilityMode",
            ],
        },
        {
            "file": "src/omnibase_core/models/core/model_missing_tool.py",
            "classes": [
                "ModelMissingTool",
                "EnumToolMissingReason",
                "EnumToolCriticality",
                "EnumToolCategory",
            ],
        },
        {
            "file": "src/omnibase_core/models/core/model_audit_entry.py",
            "classes": ["ModelAuditEntry", "EnumAuditAction"],
        },
        {
            "file": "src/omnibase_core/models/core/model_tree_sync_result.py",
            "classes": ["ModelTreeSyncResult", "EnumTreeSyncStatus"],
        },
        {
            "file": "src/omnibase_core/models/core/model_function_tool.py",
            "classes": ["ModelFunctionTool", "EnumToolType", "EnumFunctionLanguage"],
        },
        {
            "file": "src/omnibase_core/models/core/model_registry_configuration.py",
            "classes": ["ModelRegistryConfiguration", "EnumRegistryType"],
        },
        {
            "file": "src/omnibase_core/models/security/model_signature_chain.py",
            "classes": [
                "ModelSignatureChain",
                "EnumChainValidationStatus",
                "EnumTrustLevel",
                "EnumComplianceFramework",
            ],
        },
        {
            "file": "src/omnibase_core/models/health/model_tool_health.py",
            "classes": ["ModelToolHealth", "EnumToolHealthStatus", "EnumToolType"],
        },
        {
            "file": "src/omnibase_core/models/health/model_health_check.py",
            "classes": ["ModelHealthCheck", "EnumHealthCheckType"],
        },
        {
            "file": "src/omnibase_core/models/discovery/model_event_descriptor.py",
            "classes": [
                "ModelEventDescriptor",
                "EnumEventType",
                "EnumServiceStatus",
                "EnumDiscoveryPhase",
            ],
        },
        {
            "file": "src/omnibase_core/models/registry/model_registry_health_report.py",
            "classes": ["ModelRegistryHealthReport", "EnumRegistryHealthStatus"],
        },
        {
            "file": "src/omnibase_core/models/service/model_service_health.py",
            "classes": [
                "ModelServiceHealth",
                "EnumServiceHealthStatus",
                "EnumServiceType",
            ],
        },
        {
            "file": "src/omnibase_core/models/service/model_service_type.py",
            "classes": ["ModelServiceType", "EnumServiceTypeCategory"],
        },
    ]

    print(f"Processing {len(violations)} violations...")

    for i, violation in enumerate(violations):
        print(f"\n{i+1}. Processing: {violation['file']}")
        result = process_violation(violation)
        if result:
            print(f"   ✓ Success")
        else:
            print(f"   ✗ Failed")

    print("\nBatch processing complete!")


if __name__ == "__main__":
    main()
