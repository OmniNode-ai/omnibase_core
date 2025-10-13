#!/usr/bin/env python3
"""
Systematic fix for import issues after class extraction.

This script fixes common import issues that occur after extracting classes
into individual files following ONEX naming conventions.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def find_all_python_files(root_dir: Path) -> list[Path]:
    """Find all Python files in the directory."""
    return list(root_dir.rglob("*.py"))


def parse_imports_from_file(filepath: Path) -> dict[str, str]:
    """Parse all imports from a Python file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        imports = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imports[alias.name] = full_name

        return imports
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return {}


def get_import_mapping() -> dict[str, str]:
    """Create a mapping of old class names to new file paths."""
    mapping = {}

    # Common mappings for ModelConfig
    mapping["ModelConfig"] = "model_config"

    # Mappings for classes that were moved to individual files
    # Based on the naming convention: Class Name -> model_class_name.py
    class_mappings = {
        "ModelCustomFields": "model_custom_fields",
        "ModelValidationRules": "model_validation_rules",
        "ModelValidationRulesConverter": "model_validation_rules_converter",
        "ModelOperationParameters": "model_operation_parameters",
        "ModelWorkflowParameters": "model_workflow_parameters",
        "ModelTypedValue": "model_typed_value",
        "ModelErrorContext": "model_error_context",
        "ModelSchemaValue": "model_schema_value",
        "ModelNodeSignature": "model_node_signature",
        "ModelSignatureMetadata": "model_signature_metadata",
        "ModelOperationDetails": "model_operation_details",
        "ModelSignatureEvaluation": "model_signature_evaluation",
        "ModelComplianceEvaluation": "model_compliance_evaluation",
        "ModelAuthorizationEvaluation": "model_authorization_evaluation",
        "ModelEvaluationContext": "model_evaluation_context",
        "ModelEvaluationModels": "model_evaluation_models",
        "ModelSecurityPolicyData": "model_security_policy_data",
        "ModelPolicyEvaluationDetails": "model_policy_evaluation_details",
        "ModelCertificateInfo": "model_certificate_info",
        "ModelTypedMapping": "model_typed_mapping",
        "ModelValueContainer": "model_value_container",
        "ModelOperationParameterValue": "model_operation_parameter_value",
        "ModelOperationParametersBase": "model_operation_parameters_base",
        "ModelValidationRulesInputValue": "model_validation_rules_input_value",
        "ModelWorkflowInputState": "model_workflow_input_state",
        "ModelWorkflowListResult": "model_workflow_list_result",
        "ModelKubernetesTemplateGenerator": "model_kubernetes_template_generator",
        "ModelBaseResult": "model_base_result",
        "ModelWorkflow": "model_workflow",
        "ModelNodeServiceConfig": "model_node_service_config",
        "ModelHubConsulRegistrationInput": "model_hub_consul_registration_input",
        "ModelHubConsulRegistrationOutput": "model_hub_consul_registration_output",
        "ModelHubRegistrationEvent": "model_hub_registration_event",
        "EnumSignatureAlgorithm": "enum_signature_algorithm",
        "EnumNodeOperation": "enum_node_operation",
        "EnumValidationRulesInputType": "enum_validation_rules_input_type",
        "ModelCoreErrorCode": "model_core_error_code",
        "ModelOnexError": "model_onex_error",
    }

    # Add ONEX naming convention mappings
    for class_name, file_base in class_mappings.items():
        # Remove "Model" prefix for ONEX convention if it exists
        if class_name.startswith("Model"):
            simple_name = class_name[5:]  # Remove "Model"
            mapping[class_name] = f"model_{simple_name.lower()}"
        else:
            mapping[class_name] = file_base

    return mapping


def fix_imports_in_file(filepath: Path, import_mapping: dict[str, str]) -> bool:
    """Fix imports in a single file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix relative imports for ModelConfig
        content = re.sub(
            r"from \.model_config import ModelConfig",
            "from .model_config import ModelConfig",
            content,
        )

        # Fix imports that reference classes that were moved
        for class_name, file_base in import_mapping.items():
            # Fix omnibase_core imports
            content = re.sub(
                rf"from omnibase_core\.models\.([^\.]+)\.model_{file_base} import {class_name}",
                rf"from omnibase_core.models.\1.model_{file_base} import {class_name}",
                content,
            )

            # Fix relative imports
            content = re.sub(
                rf"from \.model_{file_base} import {class_name}",
                rf"from .model_{file_base} import {class_name}",
                content,
            )

        # Fix ModelConfig imports specifically
        content = re.sub(
            r"from \.model_config import ModelConfig",
            "from .model_config import ModelConfig",
            content,
        )

        # Fix missing imports for common types
        if (
            "Any" in content
            and "from typing import Any" not in content
            and "from typing import" in content
        ):
            content = re.sub(
                r"from typing import ([^A\n]+)", r"from typing import \1, Any", content
            )

        if (
            "Dict" in content
            and "from typing import Dict" not in content
            and "from typing import" in content
        ):
            content = re.sub(
                r"from typing import ([^D\n]+)", r"from typing import \1, Dict", content
            )

        # Write back if changed
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"Error fixing imports in {filepath}: {e}")
        return False


def add_missing_imports(filepath: Path) -> bool:
    """Add missing imports to a file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Add pydantic imports if missing
        if "BaseModel" in content and "from pydantic import" not in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("class ") and "BaseModel" in line:
                    lines.insert(i, "from pydantic import BaseModel")
                    break
            content = "\n".join(lines)

        # Add typing imports if missing
        typing_imports = []
        if "Any" in content and "from typing import Any" not in content:
            typing_imports.append("Any")
        if "Dict" in content and "from typing import Dict" not in content:
            typing_imports.append("Dict")
        if "Optional" in content and "from typing import Optional" not in content:
            typing_imports.append("Optional")

        if typing_imports and "from typing import" in content:
            content = re.sub(
                r"from typing import ([^\n]+)",
                rf'from typing import \1, {", ".join(typing_imports)}',
                content,
            )
        elif typing_imports:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from ") and "import" in line and i > 0:
                    lines.insert(i, f'from typing import {", ".join(typing_imports)}')
                    break
            content = "\n".join(lines)

        # Write back if changed
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"Error adding missing imports to {filepath}: {e}")
        return False


def main():
    """Main function to fix all import issues."""
    root_dir = Path("src/omnibase_core")
    import_mapping = get_import_mapping()

    print("Starting import fix process...")
    print(f"Import mapping: {import_mapping}")

    # Find all Python files
    python_files = find_all_python_files(root_dir)
    print(f"Found {len(python_files)} Python files")

    # Fix imports in each file
    fixed_files = []
    for filepath in python_files:
        if fix_imports_in_file(filepath, import_mapping):
            fixed_files.append(filepath)
            print(f"Fixed imports in {filepath}")

        if add_missing_imports(filepath):
            if filepath not in fixed_files:
                fixed_files.append(filepath)
            print(f"Added missing imports to {filepath}")

    print(f"Fixed {len(fixed_files)} files")


if __name__ == "__main__":
    main()
