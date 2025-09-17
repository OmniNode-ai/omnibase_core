#!/usr/bin/env python3
"""
Pydantic Pattern Auto-Fixer for ONEX Architecture

Automatically fixes common legacy Pydantic v1 patterns found by the validator.
Handles the remaining 13 critical errors detected by validate-pydantic-patterns.py

Usage:
    python tools/fix-pydantic-patterns.py              # Show what would be fixed
    python tools/fix-pydantic-patterns.py --fix        # Actually apply fixes
    python tools/fix-pydantic-patterns.py --file path  # Fix specific file only
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class PydanticPatternFixer:
    """Automatically fixes legacy Pydantic patterns."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.files_modified = 0

        # Pattern replacements for critical errors
        self.pattern_fixes = [
            # .copy() patterns
            (r"\.copy\(\s*update\s*=", ".model_copy(update="),
            (r"\.copy\(\s*deep\s*=\s*True\s*\)", ".model_copy(deep=True)"),
            (r"\.copy\(\s*deep\s*=\s*False\s*\)", ".model_copy(deep=False)"),
            # .dict() patterns (should be rare after previous migration)
            (r"\.dict\(\s*\)", ".model_dump()"),
            (
                r"\.dict\(\s*exclude_none\s*=\s*True\s*\)",
                ".model_dump(exclude_none=True)",
            ),
            (
                r"\.dict\(\s*exclude_unset\s*=\s*True\s*\)",
                ".model_dump(exclude_unset=True)",
            ),
            (r"\.dict\(\s*by_alias\s*=\s*True\s*\)", ".model_dump(by_alias=True)"),
            (r"\.dict\(\s*exclude\s*=", ".model_dump(exclude="),
            (r"\.dict\(\s*include\s*=", ".model_dump(include="),
            # .json() patterns
            (
                r"\.json\(\s*exclude_none\s*=\s*True\s*\)",
                ".model_dump_json(exclude_none=True)",
            ),
            (r"\.json\(\s*by_alias\s*=\s*True\s*\)", ".model_dump_json(by_alias=True)"),
        ]

    def fix_file(self, file_path: Path) -> Tuple[int, List[str]]:
        """
        Fix Pydantic patterns in a single file.

        Args:
            file_path: Path to the Python file

        Returns:
            Tuple of (fixes_count, list_of_changes)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            modified_content = original_content
            changes = []
            fixes_in_file = 0

            for line_num, line in enumerate(original_content.splitlines(), 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith('"""')
                    or stripped.startswith("'''")
                ):
                    continue

                # Apply pattern fixes
                original_line = line
                for pattern, replacement in self.pattern_fixes:
                    if re.search(pattern, line):
                        new_line = re.sub(pattern, replacement, line)
                        if new_line != line:
                            if self._is_likely_pydantic_line(line, file_path):
                                changes.append(
                                    f"Line {line_num}: {pattern} -> {replacement}"
                                )
                                modified_content = modified_content.replace(
                                    original_line, new_line, 1
                                )
                                fixes_in_file += 1
                                line = (
                                    new_line  # In case multiple patterns on same line
                                )
                                break

            # Write file if changes were made and not dry run
            if fixes_in_file > 0 and not self.dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)

            return fixes_in_file, changes

        except (UnicodeDecodeError, PermissionError) as e:
            print(f"⚠️  Could not process {file_path}: {e}")
            return 0, []

    def _is_likely_pydantic_line(self, line: str, file_path: Path) -> bool:
        """
        Determine if a line likely contains Pydantic model method calls.

        Args:
            line: The code line to analyze
            file_path: Path to the file being analyzed

        Returns:
            True if likely Pydantic usage, False otherwise
        """
        # Strong indicators this is Pydantic usage
        pydantic_indicators = [
            "BaseModel",
            "model_",
            "self.copy",
            "self.dict",
            "self.json",
            ".copy(",
            ".dict(",
            ".json(",
        ]

        # Check if line contains Pydantic indicators
        for indicator in pydantic_indicators:
            if indicator in line:
                return True

        # Check file-level context (read first 20 lines for imports)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                first_lines = "".join(f.readlines()[:20])
                if "pydantic" in first_lines.lower() or "BaseModel" in first_lines:
                    return True
        except:
            pass

        # Default to True to be conservative (better to fix non-Pydantic than miss Pydantic)
        return True

    def fix_project(self, src_dir: Path, specific_file: Path = None) -> Dict:
        """
        Fix Pydantic patterns across project or specific file.

        Args:
            src_dir: Source directory to scan
            specific_file: Optional specific file to fix

        Returns:
            Dictionary with fix statistics
        """
        mode_str = "DRY RUN" if self.dry_run else "APPLYING FIXES"
        print(f"🔧 ONEX Pydantic Pattern Auto-Fixer ({mode_str})")
        print("=" * 60)

        if specific_file:
            python_files = [specific_file] if specific_file.suffix == ".py" else []
            print(f"📁 Processing specific file: {specific_file}")
        else:
            python_files = list(src_dir.rglob("*.py"))
            print(f"📁 Scanning {len(python_files)} Python files...")

        total_fixes = 0
        files_with_fixes = {}

        for py_file in python_files:
            fixes_count, changes = self.fix_file(py_file)
            if fixes_count > 0:
                relative_path = (
                    py_file.relative_to(src_dir.parent)
                    if not specific_file
                    else py_file
                )
                files_with_fixes[str(relative_path)] = changes
                total_fixes += fixes_count

        # Report results
        if files_with_fixes:
            mode_icon = "🔍" if self.dry_run else "✅"
            print(f"\n{mode_icon} FILES WITH PYDANTIC PATTERN FIXES:")
            for file_path, changes in files_with_fixes.items():
                print(f"\n   📄 {file_path} ({len(changes)} fixes):")
                for change in changes:
                    print(f"      🔧 {change}")
        else:
            print(f"\n✨ No Pydantic pattern fixes needed!")

        # Summary
        print(f"\n📊 PATTERN FIX SUMMARY")
        print("=" * 60)
        print(
            f"Mode: {'DRY RUN (no changes made)' if self.dry_run else 'FIXES APPLIED'}"
        )
        print(f"Total fixes: {total_fixes}")
        print(f"Files modified: {len(files_with_fixes)}")

        if self.dry_run and total_fixes > 0:
            print(
                f"\n💡 Run with --fix to apply {total_fixes} changes to {len(files_with_fixes)} files"
            )
        elif not self.dry_run and total_fixes > 0:
            print(f"\n🎉 Successfully applied {total_fixes} fixes!")
            print("🧪 Recommended next steps:")
            print("   1. Run tests to ensure functionality is preserved")
            print("   2. Run validator: python scripts/validate-pydantic-patterns.py")
            print("   3. Update pre-commit config if all errors are fixed")

        return {
            "total_fixes": total_fixes,
            "files_modified": len(files_with_fixes),
            "dry_run": self.dry_run,
            "files_with_fixes": files_with_fixes,
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ONEX Pydantic Pattern Auto-Fixer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tools/fix-pydantic-patterns.py                    # Dry run (show what would be fixed)
    python tools/fix-pydantic-patterns.py --fix              # Apply fixes
    python tools/fix-pydantic-patterns.py --file model.py    # Fix specific file only
    python tools/fix-pydantic-patterns.py --fix --src-dir src # Apply fixes to src directory
        """,
    )
    parser.add_argument(
        "--fix", action="store_true", help="Apply fixes (default is dry run)"
    )
    parser.add_argument("--file", type=Path, help="Fix specific file only")
    parser.add_argument(
        "--src-dir",
        "-s",
        type=Path,
        default=Path("src"),
        help="Source directory to scan (default: src)",
    )

    args = parser.parse_args()

    if args.file and not args.file.exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    if not args.file and not args.src_dir.exists():
        print(f"❌ Source directory not found: {args.src_dir}")
        sys.exit(1)

    fixer = PydanticPatternFixer(dry_run=not args.fix)
    results = fixer.fix_project(args.src_dir, args.file)

    if not args.fix and results["total_fixes"] > 0:
        print(f"\n🚀 To apply these fixes, run:")
        if args.file:
            print(f"   python tools/fix-pydantic-patterns.py --fix --file {args.file}")
        else:
            print(f"   python tools/fix-pydantic-patterns.py --fix")


if __name__ == "__main__":
    main()
