#!/usr/bin/env python3
"""
Fix MyPy name-defined and attr-defined errors systematically.

This script applies targeted fixes based on the error analysis.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Set, Tuple

# Root directory
ROOT_DIR = Path("/Volumes/PRO-G40/Code/omnibase_core")
SRC_DIR = ROOT_DIR / "src" / "omnibase_core"


# Mapping of undefined names to their import statements
IMPORT_MAP = {
    # Standard library
    "hashlib": "import hashlib",
    "math": "import math",
    "fnmatch": "import fnmatch",
    "shlex": "import shlex",
    "re": "import re",
    "traceback": "import traceback",
    # pathlib
    "Path": "from pathlib import Path",
    # typing
    "cast": "from typing import cast",
    "UUID": "from uuid import UUID",
    "TYPE_CHECKING": "from typing import TYPE_CHECKING",
    "Any": "from typing import Any",
    # Common models that need to be discovered dynamically
    "ModelOnexError": "from omnibase_core.errors.model_onex_error import ModelOnexError",
    "EnumCoreErrorCode": "from omnibase_core.errors.error_codes import EnumCoreErrorCode",
    "ModelErrorContext": "from omnibase_core.models.common.model_error_context import ModelErrorContext",
    "ModelSchemaValue": "from omnibase_core.models.common.model_schema_value import ModelSchemaValue",
    "EnumAuditAction": "from omnibase_core.enums.enum_audit_action import EnumAuditAction",
    "EnumSecurityLevel": "from omnibase_core.enums.enum_security_level import EnumSecurityLevel",
}


def run_mypy() -> str:
    """Run MyPy and return output."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/", "--no-error-summary"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
    )
    return result.stdout + result.stderr


def find_files_with_missing_self() -> Dict[str, list]:
    """Find all files with missing 'self' parameter errors."""
    output = run_mypy()
    files_errors = {}

    pattern = r'^(.+?):(\d+): error: Name "self" is not defined'

    for line in output.split("\n"):
        match = re.match(pattern, line)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            if file_path not in files_errors:
                files_errors[file_path] = []
            files_errors[file_path].append(line_num)

    return files_errors


def fix_missing_self_in_file(file_path: str, error_lines: list) -> int:
    """Fix missing 'self' parameters in a file."""
    path = Path(file_path)
    if not path.exists():
        return 0

    content = path.read_text()
    lines = content.split("\n")

    fixed_count = 0

    # Find method definitions that are missing self
    # Look backwards from error lines to find the def statement
    for error_line_num in sorted(set(error_lines), reverse=True):
        # error_line_num is 1-based, convert to 0-based
        error_idx = error_line_num - 1

        # Search backwards for the method definition
        for i in range(error_idx, max(0, error_idx - 50), -1):
            line = lines[i].strip()

            # Look for method definition
            if line.startswith("def ") and "(" in line:
                # Check if it's missing self
                method_match = re.match(r"def\s+(\w+)\s*\((.*?)\)", line)
                if method_match:
                    method_name = method_match.group(1)
                    params = method_match.group(2).strip()

                    # Skip static methods, class methods, and already-fixed methods
                    if params.startswith("self") or params.startswith("cls"):
                        break

                    # Check if previous line has @staticmethod or @classmethod
                    if i > 0:
                        prev_line = lines[i - 1].strip()
                        if "@staticmethod" in prev_line or "@classmethod" in prev_line:
                            break

                    # This method needs 'self' added
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    indent_str = " " * indent

                    # Fix the method signature
                    if params:
                        # Add self before existing params
                        new_line = lines[i].replace(f"({params}", f"(self, {params}", 1)
                    else:
                        # Add self to empty params
                        new_line = lines[i].replace("()", "(self)", 1)

                    lines[i] = new_line
                    fixed_count += 1
                    print(f"    Fixed method '{method_name}' at line {i + 1}")
                    break
                break

    if fixed_count > 0:
        path.write_text("\n".join(lines))

    return fixed_count


def find_files_with_missing_name(name: str) -> Set[str]:
    """Find all files with missing name using mypy output."""
    output = run_mypy()
    files = set()
    pattern = rf'^(.+?):\d+: error: Name "{re.escape(name)}" is not defined'

    for line in output.split("\n"):
        match = re.match(pattern, line)
        if match:
            files.add(match.group(1))

    return files


def has_import(file_content: str, import_statement: str) -> bool:
    """Check if file already has the import."""
    # Normalize whitespace
    normalized_statement = " ".join(import_statement.split())
    normalized_content = " ".join(file_content.split())

    if normalized_statement in normalized_content:
        return True

    # Check for the imported name in any import
    if " import " in import_statement:
        # Extract module and name
        if import_statement.startswith("from "):
            parts = import_statement.split(" import ")
            module = parts[0].replace("from ", "").strip()
            imported_names = [n.strip() for n in parts[1].split(",")]

            # Check if module is imported
            for name in imported_names:
                # Simple check: is this name imported from this module?
                pattern = (
                    rf"from\s+{re.escape(module)}\s+import\s+.*\b{re.escape(name)}\b"
                )
                if re.search(pattern, file_content):
                    return True
        else:
            # Simple import statement
            module = import_statement.replace("import ", "").strip()
            pattern = rf"\bimport\s+{re.escape(module)}\b"
            if re.search(pattern, file_content):
                return True

    return False


def add_import_to_file(file_path: str, import_statement: str) -> bool:
    """Add import to file if not already present."""
    path = Path(file_path)
    if not path.exists():
        return False

    content = path.read_text()

    if has_import(content, import_statement):
        return False

    lines = content.split("\n")

    # Find where to insert the import
    insert_line = 0
    in_docstring = False
    docstring_char = None
    last_import_line = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip module docstring
        if i == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
            docstring_char = stripped[:3]
            if not (stripped.endswith('"""') or stripped.endswith("'''")):
                in_docstring = True
            continue

        if in_docstring:
            if docstring_char in stripped:
                in_docstring = False
            continue

        # Skip comments and empty lines
        if stripped.startswith("#") or not stripped:
            if last_import_line == 0:
                insert_line = i + 1
            continue

        # Track imports
        if stripped.startswith("from ") or stripped.startswith("import "):
            last_import_line = i
            insert_line = i + 1
        elif last_import_line > 0:
            # We've found the first non-import line after imports
            break

    # Determine import position based on type
    if import_statement.startswith("import "):
        # Standard library import - goes at the top
        # Find the last standard library import
        for i in range(len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("import ") and not stripped.startswith(
                "import omnibase_core"
            ):
                insert_line = i + 1
    elif import_statement.startswith("from typing") or import_statement.startswith(
        "from uuid"
    ):
        # Typing imports - after standard library, before third-party
        for i in range(len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("from typing") or stripped.startswith("from uuid"):
                insert_line = i + 1
    elif import_statement.startswith("from omnibase_core"):
        # Local imports - at the end
        insert_line = last_import_line + 1 if last_import_line > 0 else insert_line

    # Insert the import
    lines.insert(insert_line, import_statement)
    path.write_text("\n".join(lines))
    return True


def fix_missing_imports(name: str, import_statement: str) -> int:
    """Fix missing imports for a specific name across all files."""
    print(f"\n  Fixing missing import for: {name}")
    print(f"  Import: {import_statement}")

    files = find_files_with_missing_name(name)
    if not files:
        print(f"    No files found with missing {name}")
        return 0

    print(f"    Found {len(files)} files")

    fixed_count = 0
    for file_path in sorted(files):
        if add_import_to_file(file_path, import_statement):
            print(f"    ✓ {file_path}")
            fixed_count += 1

    return fixed_count


def fix_onex_base_state_imports() -> int:
    """Special fix for model_onex_base_state.py - move imports from validators to top."""
    file_path = SRC_DIR / "models" / "core" / "model_onex_base_state.py"

    if not file_path.exists():
        return 0

    content = file_path.read_text()
    lines = content.split("\n")

    # Check if imports are inside validators (indented)
    has_nested_imports = False
    for line in lines:
        if "from omnibase_core.errors" in line and (
            line.startswith("        ") or line.startswith("\t")
        ):
            has_nested_imports = True
            break

    if not has_nested_imports:
        return 0

    print("\n  Fixing model_onex_base_state.py nested imports...")

    # Ensure imports are at the top
    required_imports = [
        "from omnibase_core.errors.error_codes import EnumCoreErrorCode",
        "from omnibase_core.errors.model_onex_error import ModelOnexError",
    ]

    # Add top-level imports if missing
    for imp in required_imports:
        if imp not in content:
            # Find insertion point (after existing imports)
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("from ") or line.strip().startswith(
                    "import "
                ):
                    insert_idx = i + 1

            lines.insert(insert_idx, imp)
            print(f"    Added: {imp}")

    # Remove nested imports from validators
    new_lines = []
    for line in lines:
        # Skip indented imports
        if "from omnibase_core.errors" in line and (
            line.startswith("        ") or line.startswith("\t")
        ):
            continue
        new_lines.append(line)

    file_path.write_text("\n".join(new_lines))
    print(f"    ✓ Fixed nested imports in model_onex_base_state.py")

    return 1


def fix_wrong_attribute_names() -> int:
    """Fix wrong attribute names in imports based on MyPy suggestions."""
    # Mapping of wrong names to correct names
    attr_fixes = {
        "ModelTypedDictGenericMetadataDict": "TypedDictMetadataDict",
        "ModelEnumTransitionType": "EnumTransitionType",
        "ModelExamples": "ModelExample",
        "ModelNodeOperationEnum": "EnumNodeOperation",
        "ModelToolCapabilityLevel": "EnumToolCapabilityLevel",
        "ModelToolCategory": "EnumToolCategory",
        "ModelToolCompatibilityMode": "EnumToolCompatibilityMode",
        "ModelToolRegistrationStatus": "EnumToolRegistrationStatus",
        "ModelMetadataToolComplexity": "EnumMetadataToolComplexity",
        "ModelMetadataToolStatus": "EnumMetadataToolStatus",
        "ModelMetadataToolType": "EnumMetadataToolType",
        "ModelRuleConditionValue": "RuleConditionValue",
        "ValidationInfo": "ValidationInfo",  # pydantic_core
    }

    print("\n  Fixing wrong attribute names in imports...")
    total_fixed = 0

    for wrong_name, correct_name in attr_fixes.items():
        # Find files using the wrong name
        output = run_mypy()
        pattern = rf'Module.*has no attribute "{re.escape(wrong_name)}"'
        files_to_fix = set()

        for line in output.split("\n"):
            if re.search(pattern, line):
                match = re.match(r"^(.+?):\d+:", line)
                if match:
                    files_to_fix.add(match.group(1))

        if not files_to_fix:
            continue

        print(f"    Fixing: {wrong_name} → {correct_name} in {len(files_to_fix)} files")

        for file_path in files_to_fix:
            path = Path(file_path)
            if not path.exists():
                continue

            content = path.read_text()
            if wrong_name in content:
                # Replace in import statements
                new_content = content.replace(wrong_name, correct_name)
                if new_content != content:
                    path.write_text(new_content)
                    print(f"      ✓ {path.name}")
                    total_fixed += 1

    return total_fixed


def discover_model_imports() -> Dict[str, str]:
    """Discover model imports by analyzing the codebase structure."""
    additional_imports = {}

    # Search for model definitions in the codebase
    model_patterns = [
        (
            "ModelSchemaValue",
            "from omnibase_core.models.common.model_schema_value import ModelSchemaValue",
        ),
        (
            "ModelToolParameter",
            "from omnibase_core.models.discovery.model_tool_parameter import ModelToolParameter",
        ),
        (
            "ModelOutputMetadataItem",
            "from omnibase_core.models.discovery.model_output_metadata_item import ModelOutputMetadataItem",
        ),
        (
            "ModelMetricValue",
            "from omnibase_core.models.discovery.model_metric_value import ModelMetricValue",
        ),
        (
            "ModelRetryPolicy",
            "from omnibase_core.models.core.model_retry_policy import ModelRetryPolicy",
        ),
        (
            "ModelActionConfigValue",
            "from omnibase_core.models.core.model_action_config_value import ModelActionConfigValue",
        ),
        (
            "TypedDictMetadataDict",
            "from omnibase_core.types.typed_dict_metadata_dict import TypedDictMetadataDict",
        ),
        (
            "ModelEnumTransitionType",
            "from omnibase_core.enums.enum_transition_type import ModelEnumTransitionType",
        ),
        (
            "ModelCoreSummary",
            "from omnibase_core.models.nodes.model_core_summary import ModelCoreSummary",
        ),
        (
            "ModelDeprecationSummary",
            "from omnibase_core.models.nodes.model_deprecation_summary import ModelDeprecationSummary",
        ),
        (
            "ModelHubRegistrationEvent",
            "from omnibase_core.models.discovery.model_hub_registration_event import ModelHubRegistrationEvent",
        ),
        (
            "ModelManagerAssessment",
            "from omnibase_core.models.security.model_manager_assessment import ModelManagerAssessment",
        ),
        (
            "ModelOperationParameterValue",
            "from omnibase_core.models.operations.model_operation_parameter_value import ModelOperationParameterValue",
        ),
    ]

    for name, import_stmt in model_patterns:
        additional_imports[name] = import_stmt

    return additional_imports


def main():
    """Main function."""
    print("=" * 80)
    print("FIXING NAME-DEFINED ERRORS")
    print("=" * 80)

    total_fixed = 0

    # Step 1: Fix missing 'self' parameters (highest frequency - 136 errors)
    print("\n[1/3] Fixing missing 'self' parameters in methods...")
    files_with_self_errors = find_files_with_missing_self()

    if files_with_self_errors:
        print(f"  Found {len(files_with_self_errors)} files with missing 'self'")
        for file_path, error_lines in sorted(files_with_self_errors.items()):
            print(f"\n  Processing: {file_path}")
            fixed = fix_missing_self_in_file(file_path, error_lines)
            total_fixed += fixed
            print(f"    Fixed {fixed} methods")
    else:
        print("  No missing 'self' errors found")

    # Step 2: Fix special case - model_onex_base_state.py
    print("\n[2/5] Fixing special cases...")
    fixed = fix_onex_base_state_imports()
    total_fixed += fixed

    # Step 3: Fix missing standard library and typing imports
    print("\n[3/5] Fixing missing standard library and typing imports...")

    for name, import_stmt in sorted(IMPORT_MAP.items()):
        fixed = fix_missing_imports(name, import_stmt)
        total_fixed += fixed

    # Step 4: Fix wrong attribute names
    print("\n[4/5] Fixing wrong attribute names...")
    fixed = fix_wrong_attribute_names()
    total_fixed += fixed

    # Step 5: Fix missing model imports
    print("\n[5/5] Fixing missing model imports...")

    model_imports = discover_model_imports()
    for name, import_stmt in sorted(model_imports.items()):
        fixed = fix_missing_imports(name, import_stmt)
        total_fixed += fixed

    # Final validation
    print("\n" + "=" * 80)
    print("RUNNING FINAL VALIDATION")
    print("=" * 80)

    output = run_mypy()
    remaining_errors = len(
        [line for line in output.split("\n") if "name-defined" in line]
    )

    print(f"\nTotal fixes applied: {total_fixed}")
    print(f"Remaining name-defined errors: {remaining_errors}")

    if remaining_errors > 0:
        print("\nRemaining errors (first 20):")
        count = 0
        for line in output.split("\n"):
            if "name-defined" in line:
                print(f"  {line}")
                count += 1
                if count >= 20:
                    break

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
