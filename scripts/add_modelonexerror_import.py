#!/usr/bin/env python3
"""Add ModelOnexError import to files that need it."""

import re
from pathlib import Path


def add_import(file_path):
    """Add ModelOnexError import if not present."""
    path = Path(file_path)
    if not path.exists():
        return False

    content = path.read_text()

    # Check if import already exists
    if "from omnibase_core.errors.model_onex_error import ModelOnexError" in content:
        return False

    # Check if it's imported from a different location
    if re.search(r"from\s+\S+\s+import\s+.*ModelOnexError", content):
        return False

    lines = content.split("\n")
    insert_line = None

    # Find where to insert (after ModelCoreErrorCode import if it exists)
    for i, line in enumerate(lines):
        if "from omnibase_core.errors.error_codes import ModelCoreErrorCode" in line:
            insert_line = i + 1
            break

    # If no ModelCoreErrorCode import, insert after other omnibase_core.errors imports
    if insert_line is None:
        for i, line in enumerate(lines):
            if line.startswith("from omnibase_core.errors"):
                insert_line = i + 1
                break

    # If still not found, insert after pydantic imports
    if insert_line is None:
        for i, line in enumerate(lines):
            if line.startswith(("from pydantic", "import pydantic")):
                insert_line = i + 1
                break

    # If still not found, insert after typing imports
    if insert_line is None:
        for i, line in enumerate(lines):
            if line.startswith(("from typing", "import typing")):
                insert_line = i + 1
                break

    if insert_line is None:
        print(f"  ⚠ Could not find insertion point for {file_path}")
        return False

    # Insert the import
    lines.insert(
        insert_line, "from omnibase_core.errors.model_onex_error import ModelOnexError"
    )
    path.write_text("\n".join(lines))
    return True


def main():
    """Main function."""
    files_path = Path("/tmp/files_need_modelonexerror.txt")
    if not files_path.exists():
        print("Files list not found!")
        return

    files = files_path.read_text().strip().split("\n")
    print(f"Adding ModelOnexError import to {len(files)} files...")

    fixed_count = 0
    for file_path in files:
        file_path = file_path.strip()
        if not file_path:
            continue

        if add_import(file_path):
            print(f"  ✓ Added to: {file_path}")
            fixed_count += 1
        else:
            print(f"  - Skipped: {file_path}")

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
