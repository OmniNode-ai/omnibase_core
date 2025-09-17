#!/usr/bin/env python3
"""
Fix import references from omnibase to omnibase_spi throughout the codebase.

This script systematically updates all import statements to use the correct
omnibase_spi package instead of the old omnibase references.
"""

import re
from pathlib import Path
from typing import List, Tuple


class ImportFixer:
    """Fixes import references in Python files."""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0

    def fix_file_imports(self, file_path: Path) -> bool:
        """Fix imports in a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix import patterns
            patterns = [
                # from omnibase.protocols.* -> from omnibase_spi.protocols.*
                (r"from omnibase\.protocols\.", r"from omnibase_spi.protocols."),
                # from omnibase.model.* -> from omnibase_spi.model.* (if needed)
                (r"from omnibase\.model\.", r"from omnibase_spi.model."),
                # import omnibase.protocols.* -> import omnibase_spi.protocols.*
                (r"import omnibase\.protocols\.", r"import omnibase_spi.protocols."),
            ]

            file_fixes = 0
            for pattern, replacement in patterns:
                content, count = re.subn(pattern, replacement, content)
                file_fixes += count

            # Write back if changes were made
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.fixes_applied += file_fixes
                print(
                    f"  📝 Fixed {file_fixes} imports in {file_path.relative_to(Path.cwd())}"
                )
                return True

            return False

        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
            return False

    def fix_all_imports(self) -> None:
        """Fix imports in all Python files."""
        print("🔧 Fixing import references...")

        # Find all Python files
        src_path = Path("src/omnibase_core")
        if not src_path.exists():
            print(f"❌ Source directory not found: {src_path}")
            return

        python_files = list(src_path.rglob("*.py"))

        print(f"📁 Found {len(python_files)} Python files to process")

        files_changed = 0
        for file_path in python_files:
            self.files_processed += 1
            if self.fix_file_imports(file_path):
                files_changed += 1

        print(f"\n📊 Summary:")
        print(f"   Files processed: {self.files_processed}")
        print(f"   Files changed: {files_changed}")
        print(f"   Total imports fixed: {self.fixes_applied}")


def main():
    """Main entry point."""
    print("🎯 omnibase_core Import Reference Fixer")
    print("=" * 40)

    fixer = ImportFixer()
    fixer.fix_all_imports()

    if fixer.fixes_applied > 0:
        print(f"\n✅ Successfully fixed {fixer.fixes_applied} import references")
        print("   Re-run import validation to verify fixes")
    else:
        print("\n✅ No import references needed fixing")


if __name__ == "__main__":
    main()
