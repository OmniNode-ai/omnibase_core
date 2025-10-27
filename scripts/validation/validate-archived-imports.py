#!/usr/bin/env python3
"""
ONEX Archived Path Import Validator

This validation script prevents accidental imports from archived paths during
migration transition periods, helping maintain code quality and preventing
regressions to old import patterns.

Detected Anti-Patterns:
- `from archived.` - Direct imports from archived directory
- `from archive.` - Direct imports from archive directory
- `from omnibase_core.core.contracts.*` - Old contract paths (migrated)
- `from omnibase_core.core.mixins.*` - Old mixin paths (migrated)
- `import archived.*` - Direct module imports from archived paths

Ignored Paths:
- archived/ directory itself (expected to have old patterns)
- archive/ directory itself (expected to have old patterns)
- tests/fixtures/ (may contain test data with old patterns)

Usage:
    python validate-archived-imports.py [path] [--max-violations MAX]

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


class ArchiveViolation(TypedDict):
    file: str
    line: int
    import_statement: str
    violation_type: str
    suggested_fix: str
    severity: str


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


def should_skip_path(file_path: Path) -> bool:
    """
    Determine if a path should be skipped during validation.

    Args:
        file_path: Path to check

    Returns:
        True if path should be skipped, False otherwise
    """
    path_str = str(file_path)
    path_parts = file_path.parts

    # Skip archived directories themselves (they're expected to have old imports)
    if "archived" in path_parts or "archive" in path_parts:
        return True

    # Skip test fixtures that might contain old patterns as test data
    if "tests/fixtures" in path_str or "test/fixtures" in path_str:
        return True

    # Skip hidden directories and common non-source directories
    skip_dirs = {
        "__pycache__",
        ".git",
        ".pytest_cache",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".tox",
    }

    if any(part.startswith(".") or part in skip_dirs for part in path_parts):
        return True

    return False


def discover_python_files_safe(base_path: Path) -> Iterator[Path]:
    """
    Safely discover Python files with proper error handling and path filtering.

    Args:
        base_path: Base directory to search

    Yields:
        Path objects for Python files that should be validated
    """
    try:
        for root, dirs, files in os.walk(base_path):
            root_path = Path(root)

            # Skip if this path should be ignored
            if should_skip_path(root_path):
                dirs.clear()  # Don't recurse into this directory
                continue

            # Filter out directories to skip early
            dirs_to_skip = []
            for dir_name in dirs:
                child_path = root_path / dir_name
                if should_skip_path(child_path):
                    dirs_to_skip.append(dir_name)

            # Remove from dirs to prevent os.walk from recursing
            for skip_dir in dirs_to_skip:
                if skip_dir in dirs:
                    dirs.remove(skip_dir)

            # Process Python files
            for file_name in sorted(files):
                if (
                    file_name.endswith(".py")
                    and not file_name.startswith(".")
                    and file_name
                    not in {"__init__.py"}  # Skip __init__.py to reduce noise
                ):
                    file_path = root_path / file_name
                    if not should_skip_path(file_path):
                        yield file_path

    except (OSError, PermissionError) as e:
        logging.exception(f"Error during file discovery: {e}")
        raise


class ArchivedImportValidator:
    """Validates against imports from archived/migrated paths."""

    def __init__(self, max_violations: int = 0):
        self.max_violations = max_violations
        self.violations: list[ArchiveViolation] = []

        # Define archived import patterns to detect
        self.archived_patterns = [
            {
                "pattern": r"^\s*from\s+archived\.",
                "type": "direct_archived_import",
                "severity": "critical",
                "message": "Direct import from archived directory",
                "fix_hint": "Use the migrated path or current implementation",
            },
            {
                "pattern": r"^\s*from\s+archive\.",
                "type": "direct_archive_import",
                "severity": "critical",
                "message": "Direct import from archive directory",
                "fix_hint": "Use the migrated path or current implementation",
            },
            {
                "pattern": r"^\s*import\s+archived",
                "type": "module_archived_import",
                "severity": "critical",
                "message": "Module import from archived directory",
                "fix_hint": "Use the migrated module or current implementation",
            },
            {
                "pattern": r"^\s*import\s+archive",
                "type": "module_archive_import",
                "severity": "critical",
                "message": "Module import from archive directory",
                "fix_hint": "Use the migrated module or current implementation",
            },
            {
                "pattern": r"^\s*from\s+omnibase_core\.core\.contracts\.",
                "type": "old_contract_path",
                "severity": "high",
                "message": "Import from old contracts path (migrated)",
                "fix_hint": "Use new contract paths: from omnibase_core.models.* or omnibase_core.types.*",
            },
            {
                "pattern": r"^\s*from\s+omnibase_core\.core\.mixins\.",
                "type": "old_mixin_path",
                "severity": "high",
                "message": "Import from old mixins path (migrated)",
                "fix_hint": "Use new mixin paths or updated patterns",
            },
        ]

    def validate_file(self, file_path: Path) -> None:
        """
        Validate a single Python file for archived import patterns.

        Args:
            file_path: Path to Python file to validate
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

        except (OSError, UnicodeDecodeError) as e:
            logging.warning(f"Could not read {file_path}: {e}")
            return

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith("#"):
                continue

            # Check each archived pattern
            for pattern_info in self.archived_patterns:
                if re.search(pattern_info["pattern"], line_stripped):
                    violation = ArchiveViolation(
                        file=str(file_path),
                        line=line_num,
                        import_statement=line_stripped,
                        violation_type=pattern_info["type"],
                        suggested_fix=pattern_info["fix_hint"],
                        severity=pattern_info["severity"],
                    )
                    self.violations.append(violation)

    def validate_directory(self, directory: Path) -> None:
        """
        Validate all Python files in a directory.

        Args:
            directory: Directory path to validate
        """
        if not directory.exists():
            logging.error(f"Directory does not exist: {directory}")
            print(f"❌ ERROR: Directory does not exist: {directory}")
            sys.exit(1)

        # Discover Python files with timeout
        python_files = []
        try:
            with TimeoutContext(FILE_DISCOVERY_TIMEOUT, FILE_DISCOVERY_TIMEOUT_ERROR):
                python_files = list(discover_python_files_safe(directory))

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
            print(f"No Python files found to validate in {directory}")
            return

        # Validate files with timeout
        processed_files = 0
        try:
            with TimeoutContext(VALIDATION_TIMEOUT, VALIDATION_TIMEOUT_ERROR):
                for file_path in python_files:
                    try:
                        logging.debug(f"Validating: {file_path}")
                        self.validate_file(file_path)
                        processed_files += 1
                    except Exception as e:
                        logging.warning(f"Error validating {file_path}: {e}")

        except TimeoutError:
            logging.exception(
                f"Validation timed out after {VALIDATION_TIMEOUT} seconds"
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
        """Generate and print validation report."""
        print("🔍 ONEX Archived Import Validation Report")
        print("=" * 50)

        if not self.violations:
            print("✅ SUCCESS: No archived path imports found")
            print("All imports follow current migration patterns")
            return

        # Group violations by severity
        violations_by_severity = {"critical": [], "high": [], "medium": [], "low": []}

        for violation in self.violations:
            severity = violation["severity"]
            violations_by_severity[severity].append(violation)

        # Report violations by severity
        total_violations = len(self.violations)
        print(f"Found {total_violations} archived import violations:\n")

        for severity in ["critical", "high", "medium", "low"]:
            severity_violations = violations_by_severity[severity]
            if not severity_violations:
                continue

            severity_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "⚡",
                "low": "💡",
            }[severity]

            print(
                f"{severity_emoji} {severity.upper()} ({len(severity_violations)} violations)"
            )

            # Group by violation type for better organization
            violations_by_type = {}
            for violation in severity_violations:
                violation_type = violation["violation_type"]
                if violation_type not in violations_by_type:
                    violations_by_type[violation_type] = []
                violations_by_type[violation_type].append(violation)

            for violation_type, type_violations in violations_by_type.items():
                print(
                    f"  📋 {violation_type.replace('_', ' ').title()} ({len(type_violations)} files)"
                )

                # Show up to 3 examples
                for violation in type_violations[:3]:
                    try:
                        relative_file = str(
                            Path(violation["file"]).relative_to(Path.cwd())
                        )
                    except ValueError:
                        relative_file = violation["file"]

                    print(f"    📄 {Path(relative_file).name}:{violation['line']}")
                    print(f"       Import: {violation['import_statement']}")
                    print(f"       Fix: {violation['suggested_fix']}")

                if len(type_violations) > 3:
                    print(f"       ... and {len(type_violations) - 3} more violations")
                print()

        # Summary and recommendations
        print("\n📊 SUMMARY:")
        critical_count = len(violations_by_severity["critical"])
        high_count = len(violations_by_severity["high"])

        if self.max_violations == 0:
            print(
                f"❌ FAILURE: {total_violations} violations found (zero tolerance policy)"
            )
        elif total_violations > self.max_violations:
            print(
                f"❌ FAILURE: {total_violations} violations exceed maximum of {self.max_violations}"
            )
        else:
            print(
                f"⚠️  WARNING: {total_violations} violations found (within limit of {self.max_violations})"
            )

        print(f"   🚨 Critical: {critical_count} (archived/archive imports)")
        print(f"   ⚠️  High: {high_count} (old migrated paths)")

        print("\n🎯 MIGRATION GUIDELINES:")
        print("✅ Use current paths: from omnibase_core.models.* import ...")
        print("✅ Use current paths: from omnibase_core.types.* import ...")
        print("❌ Avoid: from archived.* import ...")
        print("❌ Avoid: from omnibase_core.core.contracts.* import ...")
        print("❌ Avoid: from omnibase_core.core.mixins.* import ...")

        print("\n🔧 NEXT STEPS:")
        if critical_count > 0:
            print(
                "1. 🚨 IMMEDIATE: Fix critical archived imports (prevent build failures)"
            )
        if high_count > 0:
            print("2. ⚠️  URGENT: Update old contract/mixin paths to new locations")
        print("3. 📚 REFERENCE: Check migration documentation for correct patterns")
        print("4. 🧪 TEST: Verify imports work with current codebase structure")


def main():
    parser = argparse.ArgumentParser(
        description="Validate against archived path imports in ONEX framework",
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
        validator = ArchivedImportValidator(max_violations=args.max_violations)

        # Validate the specified directory
        path = Path(args.path).resolve()
        logging.debug(f"Validating archived imports in: {path}")

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

        # Exit with appropriate code
        violation_count = len(validator.violations)

        if violation_count == 0:
            logging.info(
                "Archived import validation completed successfully: no violations found"
            )
            sys.exit(0)
        elif violation_count > validator.max_violations:
            logging.info(
                f"Archived import validation failed: {violation_count} violations exceed limit of {validator.max_violations}"
            )
            sys.exit(1)
        else:
            # Violations within acceptable limit
            logging.info(
                f"Archived import validation completed with acceptable violations: {violation_count} violations within limit of {validator.max_violations}"
            )
            sys.exit(0)

    except KeyboardInterrupt:
        logging.info("Archived import validation interrupted by user")
        print("\n❌ Validation interrupted by user")
        sys.exit(1)
    except Exception:
        logging.exception("Unexpected error during archived import validation")
        print("❌ Unexpected error during archived import validation")
        sys.exit(1)


if __name__ == "__main__":
    main()
