#!/usr/bin/env python3
"""
Systematic migration script for legacy Pydantic v1 dict() calls to v2 model_dump().

This script updates the codebase to use modern Pydantic v2 patterns while preserving
all existing functionality and avoiding breaking changes.
"""

import re
from pathlib import Path
from typing import List, Tuple


class PydanticDictMigrator:
    """Migrates legacy Pydantic dict() calls to model_dump()."""

    def __init__(self, root_dir: str = "src"):
        self.root_dir = Path(root_dir)
        self.migration_stats = {
            "files_processed": 0,
            "files_modified": 0,
            "patterns_replaced": 0,
        }

    def get_migration_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """Get regex patterns for migration."""
        return [
            # Most common pattern: self.dict(exclude_none=True)
            (
                re.compile(r"(\w+)\.dict\(exclude_none=True\)"),
                r"\1.model_dump(exclude_none=True)",
            ),
            # Simple dict() calls
            (re.compile(r"(\w+)\.dict\(\)"), r"\1.model_dump()"),
            # Dict with other parameters (by_alias=True, etc.)
            (re.compile(r"(\w+)\.dict\(([^)]+)\)"), r"\1.model_dump(\2)"),
        ]

    def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single Python file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            original_content = content

            patterns = self.get_migration_patterns()
            file_modified = False

            for pattern, replacement in patterns:
                new_content, count = pattern.subn(replacement, content)
                if count > 0:
                    content = new_content
                    file_modified = True
                    self.migration_stats["patterns_replaced"] += count
                    print(
                        f"  ✓ Replaced {count} pattern(s) in {file_path.relative_to(self.root_dir.parent)}"
                    )

            if file_modified:
                file_path.write_text(content, encoding="utf-8")
                self.migration_stats["files_modified"] += 1
                return True

            return False

        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
            return False

    def migrate_all(self) -> None:
        """Migrate all Python files in the source directory."""
        print("🔧 Starting Pydantic dict() → model_dump() migration...")
        print(f"📁 Scanning directory: {self.root_dir}")

        python_files = list(self.root_dir.rglob("*.py"))
        print(f"📄 Found {len(python_files)} Python files")

        for file_path in python_files:
            self.migration_stats["files_processed"] += 1

            # Skip __pycache__ and other build artifacts
            if "__pycache__" in str(file_path) or ".pyc" in str(file_path):
                continue

            print(f"🔍 Processing: {file_path.relative_to(self.root_dir.parent)}")
            self.migrate_file(file_path)

    def print_summary(self) -> None:
        """Print migration summary."""
        stats = self.migration_stats
        print("\n📊 Migration Summary:")
        print("=" * 50)
        print(f"Files processed: {stats['files_processed']}")
        print(f"Files modified:  {stats['files_modified']}")
        print(f"Patterns replaced: {stats['patterns_replaced']}")

        if stats["files_modified"] > 0:
            print("\n✅ Migration completed successfully!")
            print("🔍 Recommended next steps:")
            print("  1. Run tests to verify functionality: poetry run pytest")
            print("  2. Run type checking: poetry run mypy src")
            print("  3. Check for any remaining legacy patterns")
        else:
            print("\n💡 No legacy dict() patterns found - codebase is up to date!")


def main():
    """Main migration entry point."""
    migrator = PydanticDictMigrator()

    try:
        migrator.migrate_all()
        migrator.print_summary()
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
