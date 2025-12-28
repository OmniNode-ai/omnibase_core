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
import logging
import os
import re
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict


class Violation(TypedDict):
    file: str
    line: int
    current_import: str
    relative_path: str
    level: int
    suggested_absolute: str
    directory: str


class Fix(TypedDict):
    file: str
    bsd_sed_command: str
    gnu_sed_command: str
    original: str
    fixed: str
    current_escaped: str
    fixed_escaped: str


# Constants
FILE_DISCOVERY_TIMEOUT = 30  # seconds
VALIDATION_TIMEOUT = 300  # 5 minutes
FILE_DISCOVERY_TIMEOUT_ERROR = "File discovery operation timed out"
VALIDATION_TIMEOUT_ERROR = "Validation operation timed out"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class TimeoutContext:
    """Cross-platform timeout context manager using threading."""

    def __init__(self, seconds: int, error_message: str):
        self.seconds = seconds
        self.error_message = error_message
        self.timer: threading.Timer | None = None
        self.timed_out = False

    def _timeout_handler(self):
        """Called when timeout occurs."""
        self.timed_out = True
        logging.error(self.error_message)

    def __enter__(self):
        self.timer = threading.Timer(self.seconds, self._timeout_handler)
        self.timer.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer:
            self.timer.cancel()
        if self.timed_out:
            raise TimeoutError(self.error_message)


def discover_python_files_optimized(base_path: Path) -> Iterator[Path]:
    """
    Optimized Python file discovery using single walk with filtering.

    Args:
        base_path: Base directory to search

    Yields:
        Path objects for Python files
    """
    try:
        # Single walk through directory tree with immediate filtering
        for root, dirs, files in os.walk(base_path):
            root_path = Path(root)

            # Skip directories early to prevent recursion
            dirs_to_skip = []
            for dir_name in dirs:
                if dir_name in (
                    "__pycache__",
                    "archived",
                    ".git",
                    ".pytest_cache",
                    "node_modules",
                    ".venv",
                    "venv",
                ) or dir_name.startswith("."):
                    dirs_to_skip.append(dir_name)

            # Remove from dirs to prevent os.walk from recursing
            for skip_dir in dirs_to_skip:
                if skip_dir in dirs:
                    dirs.remove(skip_dir)

            # Skip if we're in an archived path or test files
            root_str = str(root_path)
            if "/archived/" in root_str or "archived" in root_path.parts:
                continue

            # Process files with immediate Python filtering
            # Sort files for deterministic order across different systems
            for file_name in sorted(files):
                if (
                    file_name.endswith(".py")
                    and not file_name.startswith(".")
                    and not any(
                        skip in file_name
                        for skip in ["__pycache__", ".pyc", "test_", "_test.py"]
                    )
                ):
                    yield root_path / file_name

    except (OSError, PermissionError):
        logging.exception("Error during file discovery")
        raise


class ImportPatternValidator:
    """Validates proper import patterns in ONEX codebase."""

    def __init__(self, max_violations: int = 0, generate_fixes: bool = False):
        self.max_violations = max_violations
        self.generate_fixes = generate_fixes
        self.violations: list[Violation] = []
        self.fixes_by_directory: dict[str, list[Fix]] = {}

    def detect_multi_level_relative_imports(self, file_path: Path) -> None:
        """Detect relative imports with multiple levels (.., ..., etc.)."""
        try:
            with open(file_path, encoding="utf-8") as f:
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

        except (OSError, UnicodeDecodeError) as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    def _generate_absolute_import(
        self, file_path: Path, relative_path: str, level: int
    ) -> str:
        """Generate absolute import path."""
        # Get the current file's path relative to src/
        try:
            src_index = file_path.parts.index("src")
            current_parts = file_path.parts[src_index + 1 :]  # omnibase_core/models/...
        except ValueError:
            # Fall back to absolute import within omnibase_core; normalize any slashes
            return f"omnibase_core.{relative_path.replace('/', '.')}"

        # Drop filename and go up (level - 1) package levels
        dir_parts = current_parts[:-1]  # remove file
        ascend = max(level - 1, 0)
        if ascend:
            dir_parts = dir_parts[:-ascend]

        # Add the relative path parts
        relative_parts = tuple(relative_path.split("."))
        full_parts = (*dir_parts, *relative_parts)

        # Join with dots for Python import
        absolute_path = ".".join(p for p in full_parts if p)

        return absolute_path

    def _escape_sed_pattern(self, text: str) -> str:
        """Properly escape special characters for sed patterns."""
        # Escape sed special characters: / \ & [ ] * ^ $ . ( ) + ? { } |
        special_chars = r"\/&\[\]*^$.()+?{}|"
        escaped = text
        for char in special_chars:
            escaped = escaped.replace(char, f"\\{char}")
        return escaped

    def _generate_cross_platform_sed(
        self, file_path: str, current: str, fixed: str
    ) -> dict[str, str]:
        """Generate cross-platform sed commands with proper error handling."""
        current_escaped = self._escape_sed_pattern(current)
        fixed_escaped = self._escape_sed_pattern(fixed)

        # BSD sed (macOS) command with specific .bak file removal
        bsd_command = (
            f"if sed -i '.tmp_backup' 's/{current_escaped}/{fixed_escaped}/g' '{file_path}'; then "
            f"rm -f '{file_path}.tmp_backup'; else "
            f"[ -f '{file_path}.tmp_backup' ] && mv '{file_path}.tmp_backup' '{file_path}'; "
            f"echo 'Error: sed operation failed for {file_path}' >&2; exit 1; fi"
        )

        # GNU sed (Linux) command with error handling
        gnu_command = (
            f"if cp '{file_path}' '{file_path}.tmp_backup'; then "
            f"if sed -i 's/{current_escaped}/{fixed_escaped}/g' '{file_path}'; then "
            f"rm -f '{file_path}.tmp_backup'; else "
            f"mv '{file_path}.tmp_backup' '{file_path}'; "
            f"echo 'Error: sed operation failed for {file_path}' >&2; exit 1; fi; else "
            f"echo 'Error: backup creation failed for {file_path}' >&2; exit 1; fi"
        )

        return {
            "bsd_command": bsd_command,
            "gnu_command": gnu_command,
            "current_escaped": current_escaped,
            "fixed_escaped": fixed_escaped,
        }

    def _generate_sed_fix(self, violation: Violation) -> None:
        """Generate cross-platform sed commands to fix the import."""
        directory = violation["directory"]
        current = violation["current_import"].strip()
        suggested = violation["suggested_absolute"]

        # Extract the import components
        match = re.search(r"from\s+(\.+[\w.]*)\s+import\s+(.*)", current)
        if match:
            import_items = match.group(2)
            fixed_line = f"from {suggested} import {import_items}"

            # Generate cross-platform sed commands with proper escaping and error handling
            sed_commands = self._generate_cross_platform_sed(
                violation["file"], current, fixed_line
            )

            if directory not in self.fixes_by_directory:
                self.fixes_by_directory[directory] = []

            self.fixes_by_directory[directory].append(
                {
                    "file": violation["file"],
                    "bsd_sed_command": sed_commands["bsd_command"],
                    "gnu_sed_command": sed_commands["gnu_command"],
                    "original": current,
                    "fixed": fixed_line,
                    "current_escaped": sed_commands["current_escaped"],
                    "fixed_escaped": sed_commands["fixed_escaped"],
                }
            )

    def validate_directory(self, directory: Path) -> None:
        """Validate all Python files in a directory with optimized discovery and timeout."""
        if not directory.exists():
            logging.error(f"Directory does not exist: {directory}")
            print(f"❌ ERROR: Directory does not exist: {directory}")
            sys.exit(1)

        # Use optimized file discovery with timeout
        python_files = []
        try:
            with TimeoutContext(FILE_DISCOVERY_TIMEOUT, FILE_DISCOVERY_TIMEOUT_ERROR):
                python_files = list(discover_python_files_optimized(directory))

            logging.debug(f"Found {len(python_files)} Python files to analyze")

        except TimeoutError:
            logging.exception(
                f"File discovery timed out after {FILE_DISCOVERY_TIMEOUT} seconds"
            )
            print(f"❌ ERROR: File discovery timed out in {directory}")
            sys.exit(1)
        except (OSError, PermissionError):
            logging.exception("Error during file discovery")
            print(f"❌ ERROR: Cannot access directory {directory}")
            sys.exit(1)

        if not python_files:
            print(f"No Python files found in {directory}")
            return

        # Validate files with timeout
        processed_files = 0
        try:
            with TimeoutContext(VALIDATION_TIMEOUT, VALIDATION_TIMEOUT_ERROR):
                for file_path in python_files:
                    try:
                        logging.debug(f"Analyzing: {file_path}")
                        self.detect_multi_level_relative_imports(file_path)
                        processed_files += 1
                    except Exception:
                        logging.exception(f"Error analyzing {file_path}")
                        print(
                            f"Warning: Skipped {file_path} due to analysis error",
                            file=sys.stderr,
                        )

        except TimeoutError:
            logging.exception(
                "Validation timed out after %s seconds", VALIDATION_TIMEOUT
            )
            print(
                f"❌ ERROR: Validation timeout after processing {processed_files}/{len(python_files)} files"
            )
            sys.exit(1)
        except KeyboardInterrupt:
            logging.info("Validation interrupted by user")
            print(
                f"\n❌ Validation interrupted after processing {processed_files}/{len(python_files)} files"
            )
            sys.exit(1)

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

        # Sort violations by directory and line number for reproducible output
        for directory in list(violations_by_dir.keys()):
            violations_by_dir[directory].sort(key=lambda v: (v["file"], int(v["line"])))

        print(
            f"Found {len(self.violations)} multi-level relative import violations:\\n"
        )

        # Process directories in sorted order for deterministic output
        for directory in sorted(violations_by_dir.keys()):
            dir_violations = violations_by_dir[directory]
            # Use reliable relative path computation with Path APIs
            try:
                relative_dir = str(Path(directory).relative_to(Path.cwd()))
            except ValueError:
                relative_dir = directory
            if relative_dir == ".":
                relative_dir = "."

            print(f"📁 {relative_dir} ({len(dir_violations)} violations)")

            # Show sample violations
            for violation in dir_violations[:3]:  # Show first 3
                # Use reliable relative path computation with Path APIs
                try:
                    relative_file = str(Path(violation["file"]).relative_to(Path.cwd()))
                except ValueError:
                    relative_file = violation["file"]
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
                try:
                    relative_dir = str(Path(directory).relative_to(Path.cwd()))
                except ValueError:
                    relative_dir = directory
                print(f"\\n📁 {relative_dir}:")

                # Group by file for efficiency
                files = {fix["file"] for fix in fixes}
                for file_path in sorted(files):
                    file_fixes = [f for f in fixes if f["file"] == file_path]
                    # Use reliable relative path computation with Path APIs
                    try:
                        relative_file = str(Path(file_path).relative_to(Path.cwd()))
                    except ValueError:
                        relative_file = file_path

                    print(
                        f"\\n# Fix {Path(relative_file).name} ({len(file_fixes)} imports)"
                    )
                    for fix in file_fixes:
                        print(f"# {fix['original']} -> {fix['fixed']}")

                    # Generate cross-platform sed commands for file
                    print("\\n# BSD/macOS sed command (with error handling):")
                    print(f"# {file_fixes[0]['bsd_sed_command']}")
                    print("\\n# GNU/Linux sed command (with error handling):")
                    print(f"# {file_fixes[0]['gnu_sed_command']}")

                print(
                    "\\n# Or fix all files in directory (safer cross-platform approach):"
                )
                print(
                    f"# For macOS/BSD: find {relative_dir} -name '*.py' -type f -exec sh -c '"
                    f"for file do "
                    f'if sed -i ".tmp_bak" "s/from \\\\\\.\\.\\\\\\./from omnibase_core\\./g" "$file"; then '
                    f'rm -f "$file.tmp_bak"; else '
                    f'[ -f "$file.tmp_bak" ] && mv "$file.tmp_bak" "$file"; '
                    f'echo "Error processing $file" >&2; fi; '
                    f"done' sh {{}} +"
                )
                print(
                    f"# For Linux/GNU: find {relative_dir} -name '*.py' -type f -exec sh -c '"
                    f"for file do "
                    f'if cp "$file" "$file.tmp_bak" && sed -i "s/from \\\\\\.\\.\\\\\\./from omnibase_core\\./g" "$file"; then '
                    f'rm -f "$file.tmp_bak"; else '
                    f'[ -f "$file.tmp_bak" ] && mv "$file.tmp_bak" "$file"; '
                    f'echo "Error processing $file" >&2; fi; '
                    f"done' sh {{}} +"
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

            # Generate safer sed commands for common patterns with error handling
            for pattern, count in sorted(
                patterns.items(), key=lambda x: x[1], reverse=True
            ):
                if pattern.startswith("..."):
                    replacement = pattern.replace("...", "omnibase_core.")
                elif pattern.startswith(".."):
                    replacement = pattern.replace("..", "omnibase_core.")
                else:
                    continue

                # Properly escape pattern for sed
                pattern_escaped = self._escape_sed_pattern(f"from {pattern}")
                replacement_escaped = self._escape_sed_pattern(f"from {replacement}")

                print(f"# Fix {count} imports from {pattern} (safe cross-platform)")
                print(
                    f"# macOS/BSD: for file in *.py; do "
                    f'[ -f "$file" ] && '
                    f'if sed -i ".tmp_bak" \'s/{pattern_escaped}/{replacement_escaped}/g\' "$file"; then '
                    f'rm -f "$file.tmp_bak"; else '
                    f'[ -f "$file.tmp_bak" ] && mv "$file.tmp_bak" "$file"; '
                    f'echo "Error processing $file" >&2; fi; done'
                )
                print(
                    f"# Linux/GNU: for file in *.py; do "
                    f'[ -f "$file" ] && '
                    f'if cp "$file" "$file.tmp_bak" && sed -i \'s/{pattern_escaped}/{replacement_escaped}/g\' "$file"; then '
                    f'rm -f "$file.tmp_bak"; else '
                    f'[ -f "$file.tmp_bak" ] && mv "$file.tmp_bak" "$file"; '
                    f'echo "Error processing $file" >&2; fi; done'
                )

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

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    try:
        args = parser.parse_args()

        # Configure logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        elif args.quiet:
            logging.getLogger().setLevel(logging.ERROR)

    except Exception:
        logging.exception("Error parsing arguments")
        sys.exit(1)

    try:
        validator = ImportPatternValidator(
            max_violations=args.max_violations, generate_fixes=args.generate_fixes
        )

        # Validate the specified directory
        path = Path(args.path).resolve()
        logging.debug(f"Validating import patterns in: {path}")

        if not path.exists():
            logging.error(f"Path does not exist: {path}")
            print(f"❌ ERROR: Path does not exist: {path}")
            sys.exit(1)

        if not os.access(path, os.R_OK):
            logging.error(f"Cannot read path: {path}")
            print(f"❌ ERROR: Cannot read path: {path}")
            sys.exit(1)

        validator.validate_directory(path)

        # Generate report
        if not args.quiet:
            validator.generate_report()
            if args.generate_fixes:
                validator.generate_directory_fixes()

        # Exit with appropriate code
        violation_count = len(validator.violations)

        if violation_count == 0:
            logging.info(
                f"Import pattern validation completed successfully: {violation_count} violations found"
            )
            sys.exit(0)
        elif violation_count > validator.max_violations:
            logging.info(
                f"Import pattern validation failed: {violation_count} violations exceed limit of {validator.max_violations}"
            )
            sys.exit(1)
        else:
            # Violations within acceptable limit
            logging.info(
                f"Import pattern validation completed with acceptable violations: {violation_count} violations within limit of {validator.max_violations}"
            )
            sys.exit(0)

    except KeyboardInterrupt:
        logging.info("Import pattern validation interrupted by user")
        print("\n❌ Validation interrupted by user")
        sys.exit(1)
    except Exception:
        logging.exception("Unexpected error during import pattern validation")
        print("❌ Unexpected error during import pattern validation")
        sys.exit(1)


if __name__ == "__main__":
    main()
