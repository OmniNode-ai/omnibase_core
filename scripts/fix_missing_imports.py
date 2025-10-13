#!/usr/bin/env python3
"""Fix missing imports in files based on MyPy errors."""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set

# Mapping of undefined names to their import statements
IMPORT_MAP = {
    "ModelOnexError": "from omnibase_core.errors.model_onex_error import ModelOnexError",
    "ModelCoreErrorCode": "from omnibase_core.errors.error_codes import ModelCoreErrorCode",
    "UUID": "from uuid import UUID",
    "TYPE_CHECKING": "from typing import TYPE_CHECKING",
    "Any": "from typing import Any",
}


def find_files_with_missing_name(name: str) -> set[str]:
    """Find all files with missing name using mypy output."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/", "--no-error-summary"],
        capture_output=True,
        text=True,
        cwd="/Volumes/PRO-G40/Code/omnibase_core",
        check=False,
    )
    output = result.stdout + result.stderr

    files = set()
    pattern = rf'^(.+?):\d+: error: Name "{re.escape(name)}" is not defined'

    for line in output.split("\n"):
        match = re.match(pattern, line)
        if match:
            files.add(match.group(1))

    return files


def has_import(file_content: str, import_statement: str) -> bool:
    """Check if file already has the import."""
    # Extract the actual import part (after 'from ... import ')
    import_name = import_statement.split(" import ")[-1]

    # Check for exact import
    if import_statement in file_content:
        return True

    # Check if it's imported from the same module but in a different way
    if " import " in import_statement:
        module = import_statement.split(" import ")[0].replace("from ", "")
        # Check if module is imported
        if f"from {module} import" in file_content:
            # Check if the specific name is in any import from this module
            module_imports = re.findall(
                rf"from {re.escape(module)} import .*?(?:\n|$)",
                file_content,
                re.MULTILINE,
            )
            for imp in module_imports:
                if import_name in imp:
                    return True

    return False


def add_import_to_file(file_path: str, import_statement: str) -> bool:
    """Add import to file if not already present."""
    path = Path(file_path)
    if not path.exists():
        print(f"  ⚠ File not found: {file_path}")
        return False

    content = path.read_text()

    # Check if import already exists
    if has_import(content, import_statement):
        return False

    lines = content.split("\n")

    # Find where to insert the import
    insert_line = 0
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if not in_docstring:
            if stripped.startswith(('"""', "'''")):
                docstring_char = stripped[:3]
                if not (stripped.endswith(('"""', "'''"))):
                    in_docstring = True
                continue
        else:
            if docstring_char in stripped:
                in_docstring = False
            continue

        # Skip comments and empty lines at the start
        if stripped.startswith("#") or not stripped:
            continue

        # Found first non-comment, non-docstring line
        if stripped.startswith(("from ", "import ")):
            # Determine which group this import belongs to
            if import_statement.startswith("from typing"):
                # Insert after other typing imports
                if "from typing" in stripped:
                    insert_line = i + 1
                    continue
            elif import_statement.startswith("from uuid"):
                # Insert after typing imports but before pydantic
                if "from uuid" in stripped or "from typing" in stripped:
                    insert_line = i + 1
                    continue
            elif import_statement.startswith("from omnibase_core"):
                # Insert with other omnibase_core imports
                if (
                    "from omnibase_core" in stripped
                    or "from pydantic" in stripped
                    or "import pydantic" in stripped
                ):
                    insert_line = i + 1
                    continue

            # If we haven't found a specific spot, insert after the last import
            insert_line = i + 1
        elif insert_line > 0:
            # We've passed all imports, insert before this line
            break

    # Insert the import
    if insert_line == 0:
        # No imports found, add after docstring/comments
        insert_line = max(1, i)

    lines.insert(insert_line, import_statement)

    # Write back
    path.write_text("\n".join(lines))
    return True


def fix_missing_imports(name: str, import_statement: str) -> int:
    """Fix missing imports for a specific name across all files."""
    print(f"\nFixing missing import for: {name}")
    print(f"Import statement: {import_statement}")

    files = find_files_with_missing_name(name)
    if not files:
        print(f"  No files found with missing {name}")
        return 0

    print(f"  Found {len(files)} files needing this import")

    fixed_count = 0
    for file_path in sorted(files):
        if add_import_to_file(file_path, import_statement):
            print(f"  ✓ Added to: {file_path}")
            fixed_count += 1
        else:
            print(f"  - Already has import: {file_path}")

    print(f"  Fixed {fixed_count} files")
    return fixed_count


def main():
    """Main function."""
    print("=" * 80)
    print("FIXING MISSING IMPORTS")
    print("=" * 80)

    total_fixed = 0

    # Fix imports in order of frequency
    priority_order = [
        "ModelCoreErrorCode",
        "ModelOnexError",
        "UUID",
        "TYPE_CHECKING",
        "Any",
    ]

    for name in priority_order:
        if name in IMPORT_MAP:
            fixed = fix_missing_imports(name, IMPORT_MAP[name])
            total_fixed += fixed

    print("\n" + "=" * 80)
    print(f"TOTAL FILES FIXED: {total_fixed}")
    print("=" * 80)


if __name__ == "__main__":
    main()
