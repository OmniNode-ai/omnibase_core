#!/usr/bin/env python3
"""
Script to replace datetime.utcnow() with datetime.now(UTC)
and ensure UTC is imported from datetime module.
"""
import re
from pathlib import Path
from typing import List, Tuple


def fix_file(file_path: Path) -> Tuple[bool, int]:
    """
    Fix datetime.utcnow() usage in a single file.

    Returns:
        Tuple of (was_modified, num_replacements)
    """
    content = file_path.read_text()
    original_content = content

    # Count occurrences
    num_replacements = len(re.findall(r"datetime\.utcnow\(\)", content))

    if num_replacements == 0:
        return False, 0

    # Replace datetime.utcnow() with datetime.now(UTC)
    content = re.sub(r"datetime\.utcnow\(\)", "datetime.now(UTC)", content)

    # Check if UTC is already imported
    has_utc_import = bool(re.search(r"from datetime import.*\bUTC\b", content))

    if not has_utc_import:
        # Find datetime import line and add UTC
        # Pattern 1: from datetime import datetime
        pattern1 = r"from datetime import datetime\b(?!\s*,)"
        if re.search(pattern1, content):
            content = re.sub(pattern1, "from datetime import UTC, datetime", content)
        # Pattern 2: from datetime import ..., datetime, ...
        elif re.search(r"from datetime import.*datetime", content):
            # Add UTC to the import list
            def add_utc_to_imports(match):
                import_line = match.group(0)
                # If UTC not already there
                if "UTC" not in import_line:
                    # Add UTC as first import
                    import_line = import_line.replace(
                        "from datetime import ", "from datetime import UTC, "
                    )
                return import_line

            content = re.sub(
                r"from datetime import [^;\n]+", add_utc_to_imports, content
            )
        # Pattern 3: import datetime (need to add separate import)
        elif re.search(r"^import datetime$", content, re.MULTILINE):
            content = re.sub(
                r"^(import datetime)$",
                r"\1\nfrom datetime import UTC",
                content,
                flags=re.MULTILINE,
            )

    if content != original_content:
        file_path.write_text(content)
        return True, num_replacements

    return False, 0


def main():
    """Find and fix all files with datetime.utcnow() usage."""
    base_path = Path("/Volumes/PRO-G40/Code/omnibase_core")

    # Find all Python files in src and tests (excluding archived)
    src_files = list((base_path / "src" / "omnibase_core").rglob("*.py"))
    test_files = list((base_path / "tests").rglob("*.py"))

    all_files = src_files + test_files

    # Filter out archived files
    active_files = [f for f in all_files if "archived" not in str(f)]

    total_modified = 0
    total_replacements = 0
    modified_files = []

    for file_path in active_files:
        was_modified, num_replacements = fix_file(file_path)
        if was_modified:
            total_modified += 1
            total_replacements += num_replacements
            relative_path = file_path.relative_to(base_path)
            modified_files.append((str(relative_path), num_replacements))
            print(f"✓ Fixed {relative_path} ({num_replacements} replacements)")

    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  Total files modified: {total_modified}")
    print(f"  Total replacements: {total_replacements}")
    print(f"{'='*70}")

    if modified_files:
        print("\nModified files:")
        for file_path, count in sorted(modified_files):
            print(f"  {file_path}: {count} replacements")


if __name__ == "__main__":
    main()
