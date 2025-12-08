#!/usr/bin/env python3
"""
ONEX Cross-Repository Import Validator (omnibase_infra)

This validation script prevents architectural violations by detecting imports
from omnibase_infra in the omnibase_core codebase. The ONEX architecture requires
that omnibase_core NEVER imports from omnibase_infra (infra depends on core,
not vice versa).

Architectural Principle:
- omnibase_core is the foundational library
- omnibase_infra depends on omnibase_core (one-way dependency)
- omnibase_core importing omnibase_infra creates circular dependencies

Detected Anti-Patterns (using AST parsing for accuracy):
- `from omnibase_infra import ...`
- `from omnibase_infra.module import ...`
- `import omnibase_infra`
- `import omnibase_infra.module`

Usage:
    # Directory mode (recursive scan)
    python validate-no-infra-imports.py [path]
    python validate-no-infra-imports.py src/omnibase_core

    # Pre-commit mode (pass_filenames)
    python validate-no-infra-imports.py file1.py file2.py ...

Exit Codes:
    0: No violations found
    1: Violations found or error occurred
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


# Constants
TARGET_MODULE = "omnibase_infra"
DEFAULT_SCAN_PATH = "src/omnibase_core"


@dataclass
class InfraImportViolation:
    """Represents a detected omnibase_infra import violation."""

    file_path: str
    line_no: int
    import_statement: str
    import_type: str  # 'import' or 'from'
    module_path: str  # Full module path being imported


class InfraImportVisitor(ast.NodeVisitor):
    """AST visitor to detect omnibase_infra imports."""

    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[InfraImportViolation] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements (e.g., import omnibase_infra)."""
        for alias in node.names:
            if alias.name == TARGET_MODULE or alias.name.startswith(
                f"{TARGET_MODULE}."
            ):
                # Get the actual source line for accurate reporting
                import_stmt = self._get_source_line(node.lineno)
                self.violations.append(
                    InfraImportViolation(
                        file_path=self.filename,
                        line_no=node.lineno,
                        import_statement=import_stmt,
                        import_type="import",
                        module_path=alias.name,
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from ... import statements (e.g., from omnibase_infra import ...)."""
        if node.module is not None:
            if node.module == TARGET_MODULE or node.module.startswith(
                f"{TARGET_MODULE}."
            ):
                # Get the actual source line for accurate reporting
                import_stmt = self._get_source_line(node.lineno)
                self.violations.append(
                    InfraImportViolation(
                        file_path=self.filename,
                        line_no=node.lineno,
                        import_statement=import_stmt,
                        import_type="from",
                        module_path=node.module,
                    )
                )
        self.generic_visit(node)

    def _get_source_line(self, line_no: int) -> str:
        """Get the source line for a given line number."""
        if 0 < line_no <= len(self.source_lines):
            return self.source_lines[line_no - 1].strip()
        return "<source unavailable>"


class InfraImportValidator:
    """Validates that omnibase_core does not import from omnibase_infra."""

    def __init__(self) -> None:
        self.violations: list[InfraImportViolation] = []
        self.checked_files = 0
        self.errors: list[str] = []

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate a single Python file for omnibase_infra imports.

        Args:
            file_path: Path to Python file to validate

        Returns:
            True if no violations found, False otherwise
        """
        # Skip .pyi type stub files
        if file_path.suffix == ".pyi":
            return True

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                source_lines = content.splitlines()

            # Parse the AST
            tree = ast.parse(content, filename=str(file_path))
            self.checked_files += 1

            # Visit the AST to find violations
            visitor = InfraImportVisitor(str(file_path), source_lines)
            visitor.visit(tree)

            if visitor.violations:
                self.violations.extend(visitor.violations)
                return False

            return True

        except SyntaxError as e:
            # Report syntax errors but don't fail the validation
            # (let other tools like mypy handle syntax errors)
            line_info = f":{e.lineno}" if e.lineno else ""
            self.errors.append(f"{file_path}{line_info}: Syntax error: {e.msg}")
            return True

        except UnicodeDecodeError as e:
            self.errors.append(f"{file_path}: Encoding error: {e}")
            return True

        except OSError as e:
            self.errors.append(f"{file_path}: Error reading file: {e}")
            return True

    def _discover_python_files(self, base_path: Path) -> Iterator[Path]:
        """
        Discover Python files in a directory, skipping common non-source directories.

        Args:
            base_path: Base directory to search

        Yields:
            Path objects for Python files
        """
        skip_dirs = {
            "__pycache__",
            ".git",
            ".pytest_cache",
            ".mypy_cache",
            ".venv",
            "venv",
            ".tox",
            "node_modules",
            "build",
            "dist",
            "archived",
            "archive",
        }

        if base_path.is_file():
            if base_path.suffix == ".py":
                yield base_path
            return

        for item in base_path.rglob("*.py"):
            # Skip if any parent directory is in skip_dirs
            if any(part in skip_dirs for part in item.parts):
                continue
            yield item

    def validate_path(self, path: Path) -> bool:
        """
        Validate a file or directory for omnibase_infra imports.

        Args:
            path: Path to file or directory to validate

        Returns:
            True if no violations found, False otherwise
        """
        if not path.exists():
            self.errors.append(f"Path does not exist: {path}")
            return False

        success = True
        for file_path in self._discover_python_files(path):
            if not self.validate_file(file_path):
                success = False

        return success

    def validate_files(self, file_paths: list[Path]) -> bool:
        """
        Validate multiple files (for pass_filenames pre-commit mode).

        Args:
            file_paths: List of file paths to validate

        Returns:
            True if no violations found, False otherwise
        """
        success = True
        for file_path in file_paths:
            if file_path.suffix != ".py":
                continue
            if not self.validate_file(file_path):
                success = False
        return success

    def generate_report(self) -> None:
        """Generate and print validation report."""
        print("ONEX Cross-Repository Import Validation Report")
        print("=" * 60)
        print(f"Target: Detect imports from '{TARGET_MODULE}'")
        print(f"Files checked: {self.checked_files}")
        print()

        # Report any errors encountered
        if self.errors:
            print("Warnings/Errors during validation:")
            for error in self.errors:
                print(f"  [!] {error}")
            print()

        if not self.violations:
            print("[OK] SUCCESS: No omnibase_infra imports found")
            print("All imports follow ONEX architectural boundaries")
            return

        # Group violations by file for better readability
        violations_by_file: dict[str, list[InfraImportViolation]] = {}
        for violation in self.violations:
            if violation.file_path not in violations_by_file:
                violations_by_file[violation.file_path] = []
            violations_by_file[violation.file_path].append(violation)

        print(f"[FAIL] Found {len(self.violations)} violation(s):")
        print()

        for file_path, file_violations in sorted(violations_by_file.items()):
            # Show relative path if possible
            try:
                relative_path = Path(file_path).relative_to(Path.cwd())
            except ValueError:
                relative_path = Path(file_path)

            print(f"  {relative_path}")
            for violation in sorted(file_violations, key=lambda v: v.line_no):
                print(f"    Line {violation.line_no}: {violation.import_statement}")
            print()

        # Print architectural guidance
        print("=" * 60)
        print("ONEX Architectural Violation Detected")
        print()
        print("Architectural Principle:")
        print("  - omnibase_core is the foundational library")
        print("  - omnibase_infra depends on omnibase_core (one-way dependency)")
        print("  - omnibase_core must NEVER import from omnibase_infra")
        print()
        print("How to Fix:")
        print("  1. Remove the omnibase_infra import")
        print("  2. Move the functionality to omnibase_core if needed")
        print("  3. Or create an interface/protocol in omnibase_core that")
        print("     omnibase_infra can implement")
        print()
        print("Examples:")
        print("  [BAD]  from omnibase_infra.kafka import KafkaProducer")
        print("  [BAD]  import omnibase_infra.database")
        print("  [GOOD] from omnibase_core.protocols import ProtocolMessageBus")
        print("  [GOOD] # Define protocol in core, implement in infra")


def main() -> int:
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate that omnibase_core does not import from omnibase_infra",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "paths",
        nargs="*",
        help=f"Files or directories to validate (default: {DEFAULT_SCAN_PATH})",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output except for errors",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    validator = InfraImportValidator()

    # Determine paths to validate
    if args.paths:
        # Pre-commit mode: validate specific files
        file_paths = [Path(p) for p in args.paths]

        # Check if these are files (pass_filenames mode) or directories
        if all(p.is_file() or not p.exists() for p in file_paths):
            # Filter to only existing Python files
            existing_files = [p for p in file_paths if p.exists() and p.suffix == ".py"]
            if not existing_files:
                if not args.quiet:
                    print("[OK] No Python files to validate")
                return 0
            success = validator.validate_files(existing_files)
        else:
            # Directory mode
            success = True
            for path in file_paths:
                if not validator.validate_path(path):
                    success = False
    else:
        # Default: scan src/omnibase_core
        default_path = Path(DEFAULT_SCAN_PATH)
        if not default_path.exists():
            print(f"[ERROR] Default path does not exist: {default_path}")
            return 1
        success = validator.validate_path(default_path)

    # Generate report
    if not args.quiet:
        validator.generate_report()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
