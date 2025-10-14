#!/usr/bin/env python3
"""
Migration script to consolidate OnexError implementations.

This script:
1. Updates all imports from duplicate OnexError files to canonical version
2. Updates enum imports from EnumCoreErrorCode to CoreErrorCode
3. Handles edge cases and special imports
"""

import re
from pathlib import Path
from typing import Any

# Base directories for the project
SRC_DIR = Path(__file__).parent.parent / "src"
TESTS_DIR = Path(__file__).parent.parent / "tests"


def update_file_imports(file_path: Path) -> tuple[bool, list[str]]:
    """
    Update imports in a single file.

    Returns:
        Tuple of (changed, list of changes made)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        changes = []

        # Pattern 1: Update exceptions.onex_error imports
        if "from omnibase_core.exceptions.onex_error import" in content:
            content = re.sub(
                r"from omnibase_core\.exceptions\.onex_error import OnexError",
                "from omnibase_core.errors.error_codes import OnexError",
                content,
            )
            changes.append("Updated exceptions.onex_error import to errors.error_codes")

        # Pattern 2: Update errors.error_onex imports
        if "from omnibase_core.errors.error_onex import" in content:
            # Handle both OnexError and CoreErrorCode imports
            content = re.sub(
                r"from omnibase_core\.errors\.error_onex import ([^;\n]+)",
                r"from omnibase_core.errors.error_codes import \1",
                content,
            )
            changes.append("Updated errors.error_onex import to errors.error_codes")

        # Pattern 3: Update EnumCoreErrorCode to CoreErrorCode
        if (
            "from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode"
            in content
        ):
            content = re.sub(
                r"from omnibase_core\.enums\.enum_core_error_code import EnumCoreErrorCode",
                "from omnibase_core.errors.error_codes import CoreErrorCode",
                content,
            )
            changes.append("Updated EnumCoreErrorCode import to CoreErrorCode")

        # Pattern 4: Update usage of EnumCoreErrorCode in code
        if "EnumCoreErrorCode." in content:
            content = re.sub(r"\bEnumCoreErrorCode\.", "CoreErrorCode.", content)
            changes.append("Updated EnumCoreErrorCode usage to CoreErrorCode")

        # Pattern 5: Update type hints
        if ": EnumCoreErrorCode" in content or "(EnumCoreErrorCode" in content:
            content = re.sub(r"\bEnumCoreErrorCode\b", "CoreErrorCode", content)
            if "Updated EnumCoreErrorCode usage to CoreErrorCode" not in changes:
                changes.append("Updated EnumCoreErrorCode type hints to CoreErrorCode")

        # Write back if changed
        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return True, changes

        return False, []

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, []


def find_files_to_migrate() -> list[Path]:
    """Find all Python files that need migration."""
    patterns = [
        "from omnibase_core.exceptions.onex_error import",
        "from omnibase_core.errors.error_onex import",
        "from omnibase_core.enums.enum_core_error_code import",
        "EnumCoreErrorCode",
    ]

    files_to_migrate = set()

    # Search in both src and tests directories
    for base_dir in [SRC_DIR, TESTS_DIR]:
        if not base_dir.exists():
            continue
        for pattern in patterns:
            for file_path in base_dir.rglob("*.py"):
                try:
                    if pattern in file_path.read_text(encoding="utf-8"):
                        files_to_migrate.add(file_path)
                except Exception:
                    continue

    return sorted(files_to_migrate)


def main() -> None:
    """Run the migration."""
    print("=" * 80)
    print("OnexError Consolidation Migration")
    print("=" * 80)
    print()

    # Find files to migrate
    print("Finding files to migrate...")
    files = find_files_to_migrate()
    print(f"Found {len(files)} files to migrate")
    print()

    # Process files
    total_changed = 0
    base_path = Path(__file__).parent.parent
    for i, file_path in enumerate(files, 1):
        rel_path = file_path.relative_to(base_path)
        changed, changes = update_file_imports(file_path)

        if changed:
            total_changed += 1
            print(f"[{i}/{len(files)}] ✓ {rel_path}")
            for change in changes:
                print(f"           - {change}")
        else:
            print(f"[{i}/{len(files)}] - {rel_path} (no changes)")

    print()
    print("=" * 80)
    print("Migration complete!")
    print(f"  Files changed: {total_changed}/{len(files)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
