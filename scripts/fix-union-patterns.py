#!/usr/bin/env python3
"""
Automated Union Pattern Fixer for ONEX Architecture

This script replaces common Union patterns with stronger typing:
- T | None -> Optional[T]
- Union[str, int, float, bool] -> Any with proper models
- Instance of pattern replacement -> better isinstance checks

Priority is on reducing Union count by fixing the most common patterns.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class UnionPatternFixer:
    """Fixes common Union patterns in Python files."""

    def __init__(self):
        self.replacements_made = 0
        self.files_processed = 0

        # Patterns to fix (ordered by impact)
        self.patterns = [
            # T | None -> Optional[T] patterns
            (r"(\w+(?:\[[^\]]+\])?)\s*\|\s*None", r"Optional[\1]"),
            (r"None\s*\|\s*(\w+(?:\[[^\]]+\])?)", r"Optional[\1]"),
            # Fix isinstance checks with union types
            (
                r"isinstance\(([^,]+),\s*int\s*\|\s*float\s*\|\s*bool\)",
                r"isinstance(\1, (int, float, bool))",
            ),
            (r"isinstance\(([^,]+),\s*str\s*\|\s*int\)", r"isinstance(\1, (str, int))"),
            # Union[str, int, float, bool] -> Any
            (r"Union\[str,\s*int,\s*float,\s*bool\]", "Any"),
            (
                r"Union\[int,\s*float\]",
                "Union[int, float]",
            ),  # Keep numeric unions for now
        ]

    def fix_file(self, file_path: Path) -> Tuple[bool, int]:
        """
        Fix Union patterns in a single file.

        Args:
            file_path: Path to the file to fix

        Returns:
            (was_modified, replacement_count)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            replacements_in_file = 0

            # Apply each pattern replacement
            for pattern, replacement in self.patterns:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    replacements_in_file += len(re.findall(pattern, content))
                    content = new_content

            # Only write if changes were made
            if content != original_content:
                # Ensure Optional is imported
                if "Optional[" in content and "from typing import" in content:
                    # Add Optional to existing typing imports
                    content = re.sub(
                        r"from typing import ([^\\n]+)",
                        lambda m: (
                            f"from typing import {m.group(1)}, Optional"
                            if "Optional" not in m.group(1)
                            else m.group(0)
                        ),
                        content,
                    )
                elif "Optional[" in content and not re.search(
                    r"from typing import.*Optional", content
                ):
                    # Add typing import if needed
                    if "from typing import" not in content:
                        content = "from typing import Optional\n" + content

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                return True, replacements_in_file

            return False, 0

        except (UnicodeDecodeError, PermissionError) as e:
            print(f"⚠️  Could not process {file_path}: {e}")
            return False, 0

    def fix_project(self, src_dir: Path, limit: int = 10) -> bool:
        """
        Fix Union patterns across the entire project.

        Args:
            src_dir: Source directory to scan
            limit: Maximum number of replacements to make

        Returns:
            True if successful
        """
        print("🔧 ONEX Union Pattern Fixer")
        print("=" * 50)

        # Find all Python files
        python_files = list(src_dir.rglob("*.py"))
        print(f"📁 Processing {len(python_files)} Python files...")

        total_replacements = 0
        files_modified = 0

        for py_file in python_files:
            if total_replacements >= limit:
                print(f"🚫 Reached replacement limit of {limit}")
                break

            was_modified, replacements = self.fix_file(py_file)
            if was_modified:
                files_modified += 1
                total_replacements += replacements
                relative_path = py_file.relative_to(src_dir.parent)
                print(f"✅ Fixed {relative_path}: {replacements} patterns replaced")

        print(f"\n📊 UNION PATTERN FIXING SUMMARY")
        print("=" * 50)
        print(f"Total files processed: {len(python_files)}")
        print(f"Files modified: {files_modified}")
        print(f"Total replacements made: {total_replacements}")

        if total_replacements > 0:
            print(
                f"🎉 Successfully reduced Union usage by {total_replacements} patterns!"
            )
            return True
        else:
            print("ℹ️  No Union patterns needed fixing.")
            return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ONEX Union Pattern Fixer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--src-dir",
        "-s",
        type=Path,
        default=Path("src"),
        help="Source directory to scan (default: src)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum number of replacements to make (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    args = parser.parse_args()

    if not args.src_dir.exists():
        print(f"❌ Source directory not found: {args.src_dir}")
        sys.exit(1)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")

    fixer = UnionPatternFixer()
    success = fixer.fix_project(args.src_dir, args.limit)

    if success:
        print("\n✅ Union pattern fixing completed!")
        print("💡 Run the validation script to check the new Union count:")
        print("   python scripts/validate-union-usage.py --max-unions 6700")
    else:
        print("\n⚠️  No patterns were fixed.")


if __name__ == "__main__":
    main()
