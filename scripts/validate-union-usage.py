#!/usr/bin/env python3
"""
Union Usage Validator for ONEX Architecture

Validates that Union types are used sparingly and issues warnings/errors
based on usage count. Promotes strong typing over loose union types.

Usage:
    python scripts/validate-union-usage.py
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class UnionValidator:
    """Validates Union usage in Python files."""

    def __init__(self, max_unions: int = 5):
        self.max_unions = max_unions
        self.union_patterns = [
            r"Union\[",  # Union[type1, type2]
            r"\|\s*\w+",  # type1 | type2 (Python 3.10+ syntax)
        ]

    def find_unions_in_file(self, file_path: Path) -> List[Tuple[int, str]]:
        """
        Find all Union usages in a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            List of (line_number, line_content) tuples containing unions
        """
        unions = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    for pattern in self.union_patterns:
                        if re.search(pattern, line):
                            # Skip comments and docstrings
                            stripped = line.strip()
                            if (
                                stripped.startswith("#")
                                or stripped.startswith('"""')
                                or stripped.startswith("'''")
                            ):
                                continue
                            unions.append((line_num, line.strip()))
                            break
        except (UnicodeDecodeError, PermissionError) as e:
            print(f"⚠️  Could not read {file_path}: {e}")

        return unions

    def validate_project(self, src_dir: Path) -> bool:
        """
        Validate Union usage across the entire project.

        Args:
            src_dir: Source directory to scan

        Returns:
            True if validation passes, False otherwise
        """
        print("🔍 ONEX Union Usage Validation")
        print("=" * 50)

        # Find all Python files
        python_files = list(src_dir.rglob("*.py"))
        print(f"📁 Scanning {len(python_files)} Python files...")

        total_unions = 0
        files_with_unions = {}

        for py_file in python_files:
            unions = self.find_unions_in_file(py_file)
            if unions:
                relative_path = py_file.relative_to(src_dir.parent)
                files_with_unions[str(relative_path)] = unions
                total_unions += len(unions)

        print(
            f"📊 Found {total_unions} Union usages across {len(files_with_unions)} files"
        )

        # Report findings
        if files_with_unions:
            print(f"\n⚠️  FILES WITH UNION USAGE:")
            for file_path, unions in files_with_unions.items():
                print(f"\n   📄 {file_path} ({len(unions)} unions):")
                for line_num, line in unions[:3]:  # Show first 3 unions per file
                    print(f"      Line {line_num}: {line}")
                if len(unions) > 3:
                    print(f"      ... and {len(unions) - 3} more")

        # Apply validation rules
        success = True

        if total_unions > self.max_unions:
            print(
                f"\n❌ ERROR: Too many Union usages ({total_unions} > {self.max_unions})"
            )
            print("   ONEX Architecture promotes strong typing over loose unions.")
            print("   Consider using:")
            print("   • Specific Pydantic models instead of Union[str, int, dict]")
            print("   • Enums instead of Union[Literal[...], ...]")
            print("   • Protocol types instead of Union[Type1, Type2]")
            print("   • Optional[T] instead of Union[T, None]")
            success = False
        elif total_unions > 0:
            print(f"\n⚠️  WARNING: {total_unions} Union usages found")
            print("   Consider reducing union types for stronger typing:")
            print("   • Use Optional[T] instead of Union[T, None]")
            print("   • Use specific types instead of Union[str, int, float, bool]")
            print("   • Use Pydantic models for complex data structures")
        else:
            print(f"\n✅ EXCELLENT: No Union types found!")

        print(f"\n📊 UNION VALIDATION SUMMARY")
        print("=" * 50)
        print(f"Total Union usages: {total_unions}")
        print(f"Files with unions: {len(files_with_unions)}")
        print(f"Maximum allowed: {self.max_unions}")
        print(f"Status: {'PASSED' if success else 'FAILED'}")

        if success and total_unions == 0:
            print("🎉 Perfect strong typing compliance!")

        return success


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ONEX Union Usage Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--max-unions",
        "-m",
        type=int,
        default=5,
        help="Maximum allowed Union usages before failing (default: 5)",
    )
    parser.add_argument(
        "--src-dir",
        "-s",
        type=Path,
        default=Path("src"),
        help="Source directory to scan (default: src)",
    )

    args = parser.parse_args()

    if not args.src_dir.exists():
        print(f"❌ Source directory not found: {args.src_dir}")
        sys.exit(1)

    validator = UnionValidator(max_unions=args.max_unions)
    success = validator.validate_project(args.src_dir)

    if not success:
        print("\n🚫 Union validation failed!")
        sys.exit(1)
    else:
        print("\n✅ Union validation passed!")


if __name__ == "__main__":
    main()
