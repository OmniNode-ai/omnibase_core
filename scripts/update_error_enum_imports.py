#!/usr/bin/env python3
"""
Update imports for error code enums moved from errors/error_codes.py to enums/.

This script updates all imports of EnumCLIExitCode, EnumOnexErrorCode,
EnumCoreErrorCode, and EnumRegistryErrorCode to use the new enum module locations.
"""

import re
import sys
from pathlib import Path

# Define the import mappings
IMPORT_MAPPINGS = {
    "EnumCLIExitCode": "omnibase_core.enums.enum_cli_exit_code",
    "EnumOnexErrorCode": "omnibase_core.enums.enum_onex_error_code",
    "EnumCoreErrorCode": "omnibase_core.enums.enum_core_error_code",
    "EnumRegistryErrorCode": "omnibase_core.enums.enum_registry_error_code",
    "get_core_error_description": "omnibase_core.enums.enum_core_error_code",
    "get_exit_code_for_core_error": "omnibase_core.enums.enum_core_error_code",
    "CORE_ERROR_CODE_TO_EXIT_CODE": "omnibase_core.enums.enum_core_error_code",
}


def update_imports_in_file(file_path: Path) -> bool:
    """
    Update imports in a single file.

    Returns True if file was modified, False otherwise.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Pattern to match: from omnibase_core.errors.error_codes import ...
        pattern = r"from omnibase_core\.errors\.error_codes import (.+)"

        matches = list(re.finditer(pattern, content))
        if not matches:
            return False

        modifications = []
        for match in matches:
            import_line = match.group(0)
            imports_str = match.group(1).strip()

            # Parse imports (handle both single and multi-line imports)
            if "(" in imports_str:
                # Multi-line import
                # Find the closing parenthesis
                start_pos = match.start()
                paren_count = imports_str.count("(") - imports_str.count(")")
                end_pos = match.end()

                # If unbalanced, search for closing paren
                if paren_count > 0:
                    remaining = content[end_pos:]
                    for i, char in enumerate(remaining):
                        if char == ")":
                            paren_count -= 1
                            if paren_count == 0:
                                end_pos += i + 1
                                break
                        elif char == "(":
                            paren_count += 1

                full_import = content[start_pos:end_pos]
                imports_str = full_import[full_import.index("import") + 6 :].strip()
                imports_str = imports_str.strip("()").strip()

            # Split imports and strip whitespace
            imports = [
                imp.strip() for imp in re.split(r",|\n", imports_str) if imp.strip()
            ]

            # Group imports by their new module
            new_imports_by_module = {}
            remaining_imports = []

            for imp in imports:
                found = False
                for enum_name, new_module in IMPORT_MAPPINGS.items():
                    if enum_name in imp:
                        if new_module not in new_imports_by_module:
                            new_imports_by_module[new_module] = []
                        new_imports_by_module[new_module].append(imp)
                        found = True
                        break

                if not found:
                    # Keep imports that aren't being moved
                    remaining_imports.append(imp)

            # Build new import statements
            new_imports = []
            for module, imports_list in sorted(new_imports_by_module.items()):
                if len(imports_list) == 1:
                    new_imports.append(f"from {module} import {imports_list[0]}")
                else:
                    imports_joined = ", ".join(imports_list)
                    new_imports.append(f"from {module} import {imports_joined}")

            # Add remaining imports back to error_codes if any
            if remaining_imports:
                if len(remaining_imports) == 1:
                    new_imports.append(
                        f"from omnibase_core.errors.error_codes import {remaining_imports[0]}"
                    )
                else:
                    imports_joined = ", ".join(remaining_imports)
                    new_imports.append(
                        f"from omnibase_core.errors.error_codes import {imports_joined}"
                    )

            replacement = "\n".join(new_imports)
            modifications.append((match.start(), match.end(), replacement))

        # Apply modifications in reverse order to preserve positions
        for start, end, replacement in reversed(modifications):
            content = content[:start] + replacement + content[end:]

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    # Find the repository root
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent

    # Process all Python files
    python_files = list(repo_root.glob("**/*.py"))

    modified_count = 0
    skipped_files = [
        "scripts/update_error_enum_imports.py",  # This script
        "src/omnibase_core/errors/error_codes.py",  # Will be cleaned separately
        "src/omnibase_core/errors/__init__.py",  # Already updated manually
        "src/omnibase_core/enums/__init__.py",  # Already updated manually
        "src/omnibase_core/enums/enum_cli_exit_code.py",  # New file
        "src/omnibase_core/enums/enum_onex_error_code.py",  # New file
        "src/omnibase_core/enums/enum_core_error_code.py",  # New file
        "src/omnibase_core/enums/enum_registry_error_code.py",  # New file
    ]

    for file_path in python_files:
        # Skip files in the skip list
        rel_path = str(file_path.relative_to(repo_root))
        if any(skip in rel_path for skip in skipped_files):
            continue

        if update_imports_in_file(file_path):
            print(f"Updated: {rel_path}")
            modified_count += 1

    print(f"\nTotal files modified: {modified_count}")


if __name__ == "__main__":
    main()
