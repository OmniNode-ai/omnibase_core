#!/usr/bin/env python3
"""
Automated migration script: ModelSchemaValue → SchemaValue type alias

This script performs automated transformations to replace ModelSchemaValue
usage with PEP 695 SchemaValue type alias.

Usage:
    poetry run python scripts/migrate_modelschemavalue.py --dry-run
    poetry run python scripts/migrate_modelschemavalue.py --file src/path/to/file.py
    poetry run python scripts/migrate_modelschemavalue.py --all --backup

Safety features:
- Dry-run mode for preview
- Automatic backups before modification
- Validation after each change
- Rollback on validation failure
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class ModelSchemaValueMigrator:
    """Automated migration tool for ModelSchemaValue → SchemaValue."""

    def __init__(self, dry_run: bool = True, backup: bool = True):
        """Initialize migrator with safety settings."""
        self.dry_run = dry_run
        self.backup = backup
        self.stats = {
            "files_processed": 0,
            "files_modified": 0,
            "conversions_removed": 0,
            "type_annotations_updated": 0,
            "imports_updated": 0,
            "validation_failures": 0,
        }

    def migrate_file(self, file_path: Path) -> bool:
        """
        Migrate a single file from ModelSchemaValue to SchemaValue.

        Returns:
            bool: True if migration successful, False otherwise
        """
        self.stats["files_processed"] += 1

        # Read original content
        try:
            content = file_path.read_text()
            original_content = content
        except Exception as e:
            print(f"❌ Failed to read {file_path}: {e}")
            return False

        # Create backup if enabled
        if self.backup and not self.dry_run:
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy2(file_path, backup_path)
            print(f"📦 Backup created: {backup_path}")

        # Apply transformations
        content, changes = self._apply_transformations(content)

        # Check if any changes were made
        if content == original_content:
            print(f"⏭️  No changes needed: {file_path}")
            return True

        # Preview or write changes
        if self.dry_run:
            print(f"\n📝 DRY RUN - Changes for {file_path}:")
            self._print_diff(original_content, content)
            print(f"   Changes: {changes}")
            return True

        # Write changes
        try:
            file_path.write_text(content)
            print(f"✅ Modified: {file_path}")
            print(f"   Changes: {changes}")
            self.stats["files_modified"] += 1

            # Update stats
            for key, value in changes.items():
                if key in self.stats:
                    self.stats[key] += value

            # Validate changes
            if not self._validate_file(file_path):
                print(f"❌ Validation failed for {file_path}, restoring backup...")
                self._restore_backup(file_path)
                self.stats["validation_failures"] += 1
                return False

            return True

        except Exception as e:
            print(f"❌ Failed to write {file_path}: {e}")
            if self.backup:
                self._restore_backup(file_path)
            return False

    def _apply_transformations(self, content: str) -> tuple[str, dict[str, int]]:
        """
        Apply all transformation rules to content.

        Returns:
            Tuple of (modified_content, change_counts)
        """
        changes: dict[str, int] = {
            "conversions_removed": 0,
            "type_annotations_updated": 0,
            "imports_updated": 0,
        }

        # 1. Update imports
        import_pattern = r"from omnibase_core\.models\.common\.model_schema_value import ModelSchemaValue"
        if re.search(import_pattern, content):
            content = re.sub(
                import_pattern,
                "from omnibase_core.models.types.model_onex_common_types import SchemaValue",
                content,
            )
            changes["imports_updated"] += 1

        # 2. Remove .from_value() wrapping
        # Pattern: ModelSchemaValue.from_value(expression)
        from_value_pattern = (
            r"ModelSchemaValue\.from_value\(([^)]+(?:\([^)]*\))*[^)]*)\)"
        )

        def count_from_value(match: re.Match[str]) -> str:
            changes["conversions_removed"] += 1
            return match.group(1)  # Return just the wrapped expression

        content = re.sub(from_value_pattern, count_from_value, content)

        # 3. Remove .to_value() unwrapping
        # Pattern: variable.to_value()
        to_value_pattern = r"(\w+)\.to_value\(\)"

        def count_to_value(match: re.Match[str]) -> str:
            changes["conversions_removed"] += 1
            return match.group(1)  # Return just the variable name

        content = re.sub(to_value_pattern, count_to_value, content)

        # 4. Update type annotations
        # Pattern: : ModelSchemaValue
        type_pattern = r": ModelSchemaValue(\s|$|\)|\,|\|)"

        def count_type_updates(match: re.Match[str]) -> str:
            changes["type_annotations_updated"] += 1
            return f": SchemaValue{match.group(1)}"

        content = re.sub(type_pattern, count_type_updates, content)

        # 5. Update generic types
        # Pattern: dict[str, ModelSchemaValue]
        generic_pattern = r"dict\[str, ModelSchemaValue\]"

        def count_generic_updates(match: re.Match[str]) -> str:
            changes["type_annotations_updated"] += 1
            return "dict[str, SchemaValue]"

        content = re.sub(generic_pattern, count_generic_updates, content)

        # 6. Update Field type annotations
        # Pattern: ModelSchemaValue | None = Field(...)
        field_pattern = r"ModelSchemaValue(\s*\|\s*None)?\s*=\s*Field"

        def count_field_updates(match: re.Match[str]) -> str:
            changes["type_annotations_updated"] += 1
            return f"SchemaValue{match.group(1) or ''} = Field"

        content = re.sub(field_pattern, count_field_updates, content)

        # 7. Update isinstance checks
        # Pattern: isinstance(value, ModelSchemaValue)
        # Note: After migration, these checks become type narrowing only
        isinstance_pattern = r"isinstance\((\w+), ModelSchemaValue\)"
        content = re.sub(
            isinstance_pattern,
            r"# Type narrowing: \1 is SchemaValue  # Migration note: isinstance removed",
            content,
        )

        return content, changes

    def _validate_file(self, file_path: Path) -> bool:
        """
        Validate that the migrated file is syntactically correct.

        Returns:
            bool: True if validation passes
        """
        # Check Python syntax
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                print(f"   ❌ Syntax error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("   ❌ Validation timeout")
            return False
        except Exception as e:
            print(f"   ❌ Validation error: {e}")
            return False

        print("   ✅ Syntax validation passed")
        return True

    def _restore_backup(self, file_path: Path) -> None:
        """Restore file from backup."""
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        if backup_path.exists():
            shutil.copy2(backup_path, file_path)
            print(f"   🔄 Restored from backup: {backup_path}")

    def _print_diff(self, original: str, modified: str) -> None:
        """Print a simple diff showing changes."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()

        # Simple line-by-line comparison
        max_lines = max(len(original_lines), len(modified_lines))
        changes_shown = 0

        for i in range(max_lines):
            if changes_shown >= 10:  # Limit output in dry-run
                print("   ... (more changes not shown)")
                break

            orig_line = original_lines[i] if i < len(original_lines) else ""
            mod_line = modified_lines[i] if i < len(modified_lines) else ""

            if orig_line != mod_line:
                if orig_line:
                    print(f"   - {orig_line}")
                if mod_line:
                    print(f"   + {mod_line}")
                changes_shown += 1

    def print_stats(self) -> None:
        """Print migration statistics."""
        print("\n" + "=" * 60)
        print("📊 Migration Statistics")
        print("=" * 60)
        for key, value in self.stats.items():
            label = key.replace("_", " ").title()
            print(f"{label:.<40} {value:>5}")
        print("=" * 60)


def find_files_with_modelschemavalue(root: Path) -> list[Path]:
    """Find all Python files that import or use ModelSchemaValue."""
    result = subprocess.run(
        [
            "rg",
            "--type",
            "py",
            "--files-with-matches",
            "ModelSchemaValue",
            str(root),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    return [Path(line) for line in result.stdout.strip().split("\n") if line]


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate ModelSchemaValue to SchemaValue type alias",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes for all files
  %(prog)s --dry-run --all

  # Migrate a single file with backup
  %(prog)s --file src/omnibase_core/models/core/model_custom_properties.py

  # Migrate all files with backup (CAUTION!)
  %(prog)s --all --backup

  # Migrate contract models only
  %(prog)s --pattern "src/omnibase_core/models/contracts/**/*.py"
        """,
    )

    parser.add_argument("--file", type=Path, help="Migrate a specific file")
    parser.add_argument(
        "--all", action="store_true", help="Migrate all files with ModelSchemaValue"
    )
    parser.add_argument(
        "--pattern", type=str, help="Migrate files matching glob pattern"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without modifying files (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually modify files (disables dry-run)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create .bak files before modifying (default)",
    )
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    args = parser.parse_args()

    # Resolve dry-run vs execute
    dry_run = not args.execute
    backup = not args.no_backup

    # Initialize migrator
    migrator = ModelSchemaValueMigrator(dry_run=dry_run, backup=backup)

    # Determine files to migrate
    files_to_migrate: list[Path] = []

    if args.file:
        if not args.file.exists():
            print(f"❌ File not found: {args.file}")
            return 1
        files_to_migrate = [args.file]

    elif args.all:
        print("🔍 Finding files with ModelSchemaValue...")
        root = Path(__file__).parent.parent / "src"
        files_to_migrate = find_files_with_modelschemavalue(root)
        print(f"   Found {len(files_to_migrate)} files")

    elif args.pattern:
        root = Path(__file__).parent.parent
        files_to_migrate = list(root.glob(args.pattern))

    else:
        parser.print_help()
        return 1

    # Execute migration
    if dry_run:
        print(f"\n{'='*60}")
        print("🔬 DRY RUN MODE - No files will be modified")
        print(f"{'='*60}\n")

    success_count = 0
    for file_path in files_to_migrate:
        if migrator.migrate_file(file_path):
            success_count += 1

    # Print statistics
    migrator.print_stats()

    # Summary
    print(f"\n{'='*60}")
    if dry_run:
        print("✅ Dry run complete - review changes above")
        print("   Run with --execute to apply changes")
    else:
        print(f"✅ Migration complete: {success_count}/{len(files_to_migrate)} files")
        if migrator.stats["validation_failures"] > 0:
            print(f"⚠️  {migrator.stats['validation_failures']} files failed validation")
            print("   Review errors and restore from .bak files if needed")
    print(f"{'='*60}\n")

    return 0 if success_count == len(files_to_migrate) else 1


if __name__ == "__main__":
    sys.exit(main())
