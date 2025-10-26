#!/usr/bin/env python3
"""
ONEX TypedDict Pattern Validation Hook.

Validates that TypedDict definitions follow ONEX architectural standards:
- Naming: TypedDict<Name> (not Model<Name>)
- Inheritance: Must inherit from TypedDict (not BaseModel)
- Location: Must be in types/ directory
- File naming: typed_dict_<name>.py

Architectural Principles:
- TypedDict = structural type definitions (types/)
- BaseModel = behavioral classes with validation (models/)
- Clear separation prevents architectural confusion
"""

import ast
import re
import sys
from pathlib import Path


def check_typeddict_naming(file_path: Path) -> list[tuple[int, str, str]]:
    """
    Check if TypedDict classes follow naming conventions.

    Args:
        file_path: Path to the Python file

    Returns:
        List of (line_number, class_name, violation_type) tuples
    """
    violations = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name

                # Check if class inherits from TypedDict
                inherits_typeddict = any(
                    (isinstance(base, ast.Name) and base.id == "TypedDict")
                    or (isinstance(base, ast.Attribute) and base.attr == "TypedDict")
                    for base in node.bases
                )

                # Check if class inherits from BaseModel
                inherits_basemodel = any(
                    (isinstance(base, ast.Name) and base.id == "BaseModel")
                    or (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
                    for base in node.bases
                )

                # Violation 1: TypedDict class with Model prefix
                if inherits_typeddict and class_name.startswith("Model"):
                    violations.append(
                        (
                            node.lineno,
                            class_name,
                            "typeddict_with_model_prefix",
                        )
                    )

                # Violation 2: BaseModel class with TypedDict prefix
                if inherits_basemodel and class_name.startswith("TypedDict"):
                    violations.append(
                        (
                            node.lineno,
                            class_name,
                            "basemodel_with_typeddict_prefix",
                        )
                    )

                # Violation 3: TypedDict without TypedDict prefix
                if inherits_typeddict and not class_name.startswith("TypedDict"):
                    violations.append(
                        (
                            node.lineno,
                            class_name,
                            "typeddict_without_prefix",
                        )
                    )

                # Violation 4: TypedDict in wrong location (not in types/)
                if inherits_typeddict and "/types/" not in str(file_path):
                    violations.append(
                        (
                            node.lineno,
                            class_name,
                            "typeddict_wrong_location",
                        )
                    )

    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        return []

    return violations


def main() -> int:
    """
    Main entry point for the hook.

    Returns:
        0 if no violations found, 1 otherwise
    """
    if len(sys.argv) < 2:
        print("Usage: validate-typeddict-patterns.py <file> [<file> ...]")
        return 1

    files_to_check = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]

    if not files_to_check:
        return 0

    violations_found = False

    for file_path in files_to_check:
        violations = check_typeddict_naming(file_path)

        if violations:
            violations_found = True
            print(f"\n{file_path}:")

            for line_num, class_name, violation_type in violations:
                if violation_type == "typeddict_with_model_prefix":
                    print(
                        f"  Line {line_num}: ❌ TypedDict class '{class_name}' uses Model prefix"
                    )
                    print(
                        f"    Should be: {class_name.replace('Model', 'TypedDict', 1)}"
                    )

                elif violation_type == "basemodel_with_typeddict_prefix":
                    print(
                        f"  Line {line_num}: ❌ BaseModel class '{class_name}' uses TypedDict prefix"
                    )
                    print(
                        f"    Should be: {class_name.replace('TypedDict', 'Model', 1)}"
                    )

                elif violation_type == "typeddict_without_prefix":
                    print(
                        f"  Line {line_num}: ❌ TypedDict class '{class_name}' missing TypedDict prefix"
                    )
                    print(f"    Should be: TypedDict{class_name}")

                elif violation_type == "typeddict_wrong_location":
                    print(
                        f"  Line {line_num}: ❌ TypedDict class '{class_name}' not in types/ directory"
                    )
                    expected_file = f"typed_dict_{re.sub(r'(?<!^)(?=[A-Z])', '_', class_name.replace('TypedDict', '', 1)).lower()}.py"
                    print(f"    Should be in: src/omnibase_core/types/{expected_file}")

    if violations_found:
        print(
            "\n❌ TypedDict Pattern Violations Found"
            "\n"
            "\nONEX Architectural Standards:"
            "\n  1. TypedDict classes MUST start with 'TypedDict' prefix"
            "\n  2. TypedDict classes MUST be in src/omnibase_core/types/"
            "\n  3. TypedDict classes MUST inherit from TypedDict (not BaseModel)"
            "\n  4. BaseModel classes MUST start with 'Model' prefix"
            "\n  5. File naming: typed_dict_<name>.py (snake_case)"
            "\n"
            "\nExamples:"
            "\n  ❌ class ModelCoreSummary(TypedDict)  # Wrong prefix"
            "\n  ✅ class TypedDictCoreSummary(TypedDict)  # Correct"
            "\n"
            "\n  ❌ models/nodes/model_node_core_info.py  # Wrong location"
            "\n  ✅ types/typed_dict_core_summary.py  # Correct"
            "\n"
            "\n  ❌ class TypedDictUser(BaseModel)  # Wrong inheritance"
            "\n  ✅ class ModelUser(BaseModel)  # Correct"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
