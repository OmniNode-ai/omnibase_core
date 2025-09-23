#!/usr/bin/env python3
"""
ONEX Import Pattern Validator

This validation script detects improper relative import patterns and suggests
absolute imports for better maintainability and IDE support.

Enforced Patterns:
- Absolute imports for non-siblings: `from omnibase_core.enums.enum_type import EnumType`
- Relative imports only for siblings: `from .model_sibling import ModelSibling`
- Avoid: `from ..parent import Something`, `from ...grandparent import Something`

Usage:
    python validate-import-patterns.py [path] [--max-violations MAX] [--generate-fixes]

Exit Codes:
    0: No violations found or within acceptable limits
    1: Violations found that exceed the maximum threshold
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ImportPatternValidator:
    """Validates proper import patterns in ONEX codebase."""

    def __init__(self, max_violations: int = 0, generate_fixes: bool = False):
        self.max_violations = max_violations
        self.generate_fixes = generate_fixes
        self.violations: List[Dict[str, str]] = []
        self.fixes_by_directory: Dict[str, List[str]] = {}

    def detect_multi_level_relative_imports(self, file_path: Path) -> None:
        """Detect relative imports with multiple levels (.., ..., etc.)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            # Look for relative import patterns
            multi_level_patterns = [
                (r"from\s+\.\.([.\w]+)\s+import", 2),  # from ..something import
                (r"from\s+\.\.\.([.\w]+)\s+import", 3),  # from ...something import
                (r"from\s+\.\.\.\.([.\w]+)\s+import", 4),  # from ....something import
                (
                    r"from\s+\.\.\.\.\.([.\w]+)\s+import",
                    5,
                ),  # from .....something import
            ]

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                for pattern, level in multi_level_patterns:
                    match = re.search(pattern, line)
                    if match:
                        relative_path = match.group(1)
                        absolute_import = self._generate_absolute_import(
                            file_path, relative_path, level
                        )

                        violation = {
                            "file": str(file_path),
                            "line": line_num,
                            "current_import": line,
                            "relative_path": relative_path,
                            "level": level,
                            "suggested_absolute": absolute_import,
                            "directory": str(file_path.parent),
                        }

                        self.violations.append(violation)

                        # Generate sed fix command
                        if self.generate_fixes:
                            self._generate_sed_fix(violation)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _generate_absolute_import(
        self, file_path: Path, relative_path: str, level: int
    ) -> str:
        """Generate absolute import path."""
        # Get the current file's path relative to src/
        try:
            src_index = file_path.parts.index("src")
            current_parts = file_path.parts[src_index + 1 :]  # omnibase_core/models/...
        except ValueError:
            return f"omnibase_core.{relative_path.replace('.', '/')}"

        # Calculate the target path by going up 'level' directories
        target_parts = current_parts[:-level]  # Remove file and go up levels

        # Add the relative path parts
        relative_parts = relative_path.split(".")
        target_parts = target_parts + tuple(relative_parts)

        # Join with dots for Python import
        absolute_path = ".".join(target_parts)

        return absolute_path

    def _generate_sed_fix(self, violation: Dict[str, str]) -> None:
        """Generate sed command to fix the import."""
        directory = violation["directory"]
        current = violation["current_import"].strip()
        suggested = violation["suggested_absolute"]

        # Extract the import components
        match = re.search(r"from\s+(\.+[\w.]*)\s+import\s+(.*)", current)
        if match:
            import_items = match.group(2)
            fixed_line = f"from {suggested} import {import_items}"

            # Create sed command (escape special characters)
            current_escaped = current.replace("/", "\\/")
            fixed_escaped = fixed_line.replace("/", "\\/")

            sed_command = f"sed -i 's/{current_escaped}/{fixed_escaped}/g'"

            if directory not in self.fixes_by_directory:
                self.fixes_by_directory[directory] = []

            self.fixes_by_directory[directory].append(
                {
                    "file": violation["file"],
                    "sed_command": sed_command,
                    "original": current,
                    "fixed": fixed_line,
                }
            )

    def validate_directory(self, directory: Path) -> None:
        """Validate all Python files in a directory."""
        if not directory.exists():
            print(f"❌ ERROR: Directory does not exist: {directory}")
            sys.exit(1)

        python_files = list(directory.glob("**/*.py"))

        if not python_files:
            print(f"No Python files found in {directory}")
            return

        for file_path in python_files:
            # Skip certain directories
            if any(
                skip in str(file_path)
                for skip in ["__pycache__", ".pyc", "test_", "_test.py"]
            ):
                continue
            self.detect_multi_level_relative_imports(file_path)

    def generate_report(self) -> None:
        """Generate and print violation report."""
        print("🔍 ONEX Import Pattern Validation Report")
        print("=" * 50)

        if not self.violations:
            print("✅ SUCCESS: No multi-level relative import violations found")
            print("All imports follow proper ONEX patterns")
            return

        # Group violations by directory
        violations_by_dir = {}
        for violation in self.violations:
            directory = violation["directory"]
            if directory not in violations_by_dir:
                violations_by_dir[directory] = []
            violations_by_dir[directory].append(violation)

        print(
            f"Found {len(self.violations)} multi-level relative import violations:\\n"
        )

        for directory, dir_violations in violations_by_dir.items():
            relative_dir = directory.replace(str(Path.cwd()), ".")
            print(f"📁 {relative_dir} ({len(dir_violations)} violations)")

            # Show sample violations
            for violation in dir_violations[:3]:  # Show first 3
                relative_file = violation["file"].replace(str(Path.cwd()), ".")
                print(f"  🚨 {Path(relative_file).name}:{violation['line']}")
                print(f"     Current:  {violation['current_import']}")
                print(
                    f"     Absolute: from {violation['suggested_absolute']} import ..."
                )

            if len(dir_violations) > 3:
                print(f"     ... and {len(dir_violations) - 3} more violations")
            print()

        # Summary
        violation_count = len(self.violations)
        if self.max_violations == 0:
            print(
                f"❌ FAILURE: {violation_count} violations found (zero tolerance policy)"
            )
            print("🔧 Convert multi-level relative imports to absolute imports")
        elif violation_count > self.max_violations:
            print(
                f"❌ FAILURE: {violation_count} violations exceed maximum of {self.max_violations}"
            )
            print(f"🔧 Reduce violations by {violation_count - self.max_violations}")
        else:
            print(
                f"⚠️  WARNING: {violation_count} violations found (within limit of {self.max_violations})"
            )

        print("\\n🎯 RECOMMENDED PATTERNS:")
        print("✅ Absolute imports: from omnibase_core.enums.enum_type import EnumType")
        print("✅ Sibling imports:  from .model_sibling import ModelSibling")
        print("❌ Avoid: from ..parent import Something")
        print("❌ Avoid: from ...grandparent import Something")

        # Generate fix commands if requested
        if self.generate_fixes and self.fixes_by_directory:
            print("\\n🔧 AUTOMATED FIX COMMANDS:")
            print("=" * 30)

            for directory, fixes in self.fixes_by_directory.items():
                relative_dir = directory.replace(str(Path.cwd()), ".")
                print(f"\\n📁 {relative_dir}:")

                # Group by file for efficiency
                files = set(fix["file"] for fix in fixes)
                for file_path in sorted(files):
                    file_fixes = [f for f in fixes if f["file"] == file_path]
                    relative_file = file_path.replace(str(Path.cwd()), ".")

                    print(
                        f"\\n# Fix {Path(relative_file).name} ({len(file_fixes)} imports)"
                    )
                    for fix in file_fixes:
                        print(f"# {fix['original']} -> {fix['fixed']}")

                    # Generate combined sed command for file
                    print(
                        f"{file_fixes[0]['sed_command'].replace(file_fixes[0]['original'], '')}..."
                    )

                print(f"\\n# Or fix all files in directory:")
                print(
                    f"find {relative_dir} -name '*.py' -exec sed -i 's/from \\.\\.\\./from omnibase_core./g' {{}} \\;"
                )

    def generate_directory_fixes(self) -> None:
        """Generate directory-specific fix commands."""
        if not self.fixes_by_directory:
            return

        print("\\n📋 DIRECTORY-SPECIFIC FIX COMMANDS:")
        print("=" * 40)

        for directory, fixes in self.fixes_by_directory.items():
            relative_dir = directory.replace(str(Path.cwd()), ".")
            violation_count = len(fixes)

            print(f"\\n📁 {relative_dir} - {violation_count} violations")
            print(f"cd {relative_dir}")

            # Common patterns in this directory
            patterns = {}
            for fix in fixes:
                original = fix["original"]
                # Extract the relative import pattern
                match = re.search(r"from\s+(\.+[\w.]*)", original)
                if match:
                    pattern = match.group(1)
                    if pattern not in patterns:
                        patterns[pattern] = 0
                    patterns[pattern] += 1

            # Generate sed commands for common patterns
            for pattern, count in sorted(
                patterns.items(), key=lambda x: x[1], reverse=True
            ):
                if pattern.startswith("..."):
                    replacement = pattern.replace("...", "omnibase_core.")
                elif pattern.startswith(".."):
                    replacement = pattern.replace("..", "omnibase_core.")
                else:
                    continue

                print(f"# Fix {count} imports from {pattern}")
                print(f"sed -i 's/from {re.escape(pattern)}/from {replacement}/g' *.py")

            print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate import patterns in ONEX framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "path", nargs="?", default="src", help="Path to analyze (default: src)"
    )

    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0 for zero tolerance)",
    )

    parser.add_argument(
        "--generate-fixes",
        action="store_true",
        help="Generate sed commands to fix violations",
    )

    parser.add_argument(
        "--quiet", action="store_true", help="Suppress output except for errors"
    )

    args = parser.parse_args()

    validator = ImportPatternValidator(
        max_violations=args.max_violations, generate_fixes=args.generate_fixes
    )

    # Validate the specified directory
    path = Path(args.path)
    validator.validate_directory(path)

    # Generate report
    if not args.quiet:
        validator.generate_report()
        if args.generate_fixes:
            validator.generate_directory_fixes()

    # Exit with appropriate code
    violation_count = len(validator.violations)

    if violation_count == 0:
        sys.exit(0)
    elif violation_count > validator.max_violations:
        sys.exit(1)
    else:
        # Violations within acceptable limit
        sys.exit(0)


if __name__ == "__main__":
    main()
