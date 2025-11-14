#!/usr/bin/env python3
"""
Script to automatically replace standard Python exceptions with ModelOnexError.

This script:
1. Finds all files with standard exception raises
2. Replaces them with appropriate ModelOnexError calls
3. Adds necessary imports
"""

import re
from pathlib import Path
from typing import Any

# Mapping of standard exceptions to error codes
EXCEPTION_MAPPINGS = {
    "ValueError": "ModelCoreErrorCode.VALIDATION_ERROR",
    "TypeError": "ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH",
    "KeyError": "ModelCoreErrorCode.ITEM_NOT_REGISTERED",
    "FileNotFoundError": "ModelCoreErrorCode.FILE_NOT_FOUND",
    "Exception": "ModelCoreErrorCode.INTERNAL_ERROR",
    "AttributeError": "ModelCoreErrorCode.ITEM_NOT_REGISTERED",
}


def needs_imports(content: str) -> tuple[bool, bool]:
    """Check if file needs ModelOnexError or ModelCoreErrorCode imports."""
    needs_error = "ModelOnexError" not in content
    needs_code = "ModelCoreErrorCode" not in content
    return needs_error, needs_code


def add_imports_if_needed(content: str) -> str:
    """Add necessary imports at the top of the file if not present."""
    needs_error, needs_code = needs_imports(content)

    if not needs_error and not needs_code:
        return content

    # Find where to insert imports (after module docstring and __future__ imports)
    lines = content.split("\n")
    insert_index = 0

    # Skip docstring
    in_docstring = False
    for i, line in enumerate(lines):
        if '"""' in line or "'''" in line:
            if not in_docstring:
                in_docstring = True
            else:
                insert_index = i + 1
                in_docstring = False
                break

    # Skip __future__ imports
    for i in range(insert_index, len(lines)):
        if lines[i].startswith("from __future__"):
            insert_index = i + 1
        elif lines[i].strip() and not lines[i].startswith("#"):
            break

    # Add blank line if needed
    if insert_index < len(lines) and lines[insert_index].strip():
        lines.insert(insert_index, "")
        insert_index += 1

    # Add imports
    if needs_code:
        lines.insert(
            insert_index,
            "from omnibase_core.errors.error_codes import ModelCoreErrorCode",
        )
        insert_index += 1
    if needs_error:
        lines.insert(
            insert_index,
            "from omnibase_core.errors.model_onex_error import ModelOnexError",
        )
        insert_index += 1

    return "\n".join(lines)


def replace_exception_raising(content: str, exc_type: str, error_code: str) -> str:
    """Replace standard exception raises with ModelOnexError."""

    # Pattern 1: Simple raise with string message
    # raise ValueError("message")
    pattern1 = rf'raise {exc_type}\(\s*"([^"]+)"\s*\)'
    replacement1 = (
        r"raise ModelOnexError(\n"
        r"            error_code=" + error_code + r",\n"
        r'            message="\1",\n'
        r"        )"
    )
    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: raise with f-string
    # raise ValueError(f"message {var}")
    pattern2 = rf'raise {exc_type}\(\s*f"([^"]+)"\s*\)'
    replacement2 = (
        r"raise ModelOnexError(\n"
        r"            error_code=" + error_code + r",\n"
        r'            message=f"\1",\n'
        r"        )"
    )
    content = re.sub(pattern2, replacement2, content)

    # Pattern 3: raise with variable message
    # raise ValueError(msg)
    pattern3 = rf"raise {exc_type}\(\s*(\w+)\s*\)"
    replacement3 = (
        r"raise ModelOnexError(\n"
        r"            error_code=" + error_code + r",\n"
        r"            message=\1,\n"
        r"        )"
    )
    content = re.sub(pattern3, replacement3, content)

    # Pattern 4: raise with "from e"
    # raise ValueError(msg) from e
    pattern4 = rf"raise {exc_type}\(\s*([^)]+)\s*\)\s+from\s+(\w+)"
    replacement4 = (
        r"raise ModelOnexError(\n"
        r"            error_code=" + error_code + r",\n"
        r"            message=\1,\n"
        r"        ) from \2"
    )
    content = re.sub(pattern4, replacement4, content)

    # Pattern 5: Multi-line raise statements
    # raise ValueError(
    #     "message"
    # )
    pattern5 = rf"raise {exc_type}\(\s*\n\s*([^)]+)\s*\n\s*\)"
    replacement5 = (
        r"raise ModelOnexError(\n"
        r"            error_code=" + error_code + r",\n"
        r"            message=\1,\n"
        r"        )"
    )
    content = re.sub(pattern5, replacement5, content, flags=re.MULTILINE | re.DOTALL)

    return content


def fix_file(filepath: Path) -> tuple[bool, list[str]]:
    """
    Fix exception raises in a file.

    Returns:
        (modified, exceptions_fixed) where exceptions_fixed is list of exception types
    """
    content = filepath.read_text(encoding="utf-8")
    original_content = content
    exceptions_fixed = []

    # Skip if file contains error-ok comments
    if "# error-ok:" in content:
        return False, []

    # Replace each exception type
    for exc_type, error_code in EXCEPTION_MAPPINGS.items():
        if f"raise {exc_type}" in content:
            content = replace_exception_raising(content, exc_type, error_code)
            if content != original_content:
                exceptions_fixed.append(exc_type)
                original_content = content

    # Add imports if any exceptions were replaced
    if exceptions_fixed:
        content = add_imports_if_needed(content)

    # Write back if modified
    if content != filepath.read_text(encoding="utf-8"):
        filepath.write_text(content, encoding="utf-8")
        return True, exceptions_fixed

    return False, []


def main():
    """Main entry point."""
    src_dir = Path(__file__).parent.parent / "src"

    # Find all Python files with standard exceptions
    files_to_fix = []
    for exc_type in EXCEPTION_MAPPINGS:
        for py_file in src_dir.rglob("*.py"):
            # Skip test files and validation scripts
            if "test" in str(py_file) or "validation" in str(py_file):
                continue

            content = py_file.read_text(encoding="utf-8")
            if f"raise {exc_type}" in content and "# error-ok:" not in content:
                files_to_fix.append(py_file)

    files_to_fix = sorted(set(files_to_fix))

    print(f"Found {len(files_to_fix)} files to fix")
    print()

    fixed_count = 0
    exception_counts = {exc: 0 for exc in EXCEPTION_MAPPINGS}

    for filepath in files_to_fix:
        modified, exceptions = fix_file(filepath)
        if modified:
            print(f"✅ Fixed: {filepath.relative_to(src_dir.parent.parent)}")
            print(f"   Exceptions: {', '.join(exceptions)}")
            fixed_count += 1
            for exc in exceptions:
                exception_counts[exc] += 1
        else:
            print(f"⏭️  Skipped: {filepath.relative_to(src_dir.parent.parent)}")

    print()
    print(f"✅ Fixed {fixed_count} files")
    for exc_type, count in exception_counts.items():
        if count > 0:
            print(f"   {exc_type}: {count} files")


if __name__ == "__main__":
    main()
