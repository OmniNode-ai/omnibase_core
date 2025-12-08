#!/usr/bin/env python3
"""
ONEX __all__ Exports Validation.

Validates that Python modules have correct __all__ exports that match
the actual module-level definitions (classes, functions, constants).

This ensures:
1. Items in __all__ are actually defined or imported in the module
2. Explicit exports prevent accidental public API changes
3. Consistent exports across all Python files

Usage:
    poetry run python scripts/validation/validate-all-exports.py
    poetry run python scripts/validation/validate-all-exports.py --verbose
    poetry run python scripts/validation/validate-all-exports.py --warn-missing
    poetry run python scripts/validation/validate-all-exports.py --fail-on-star
    poetry run python scripts/validation/validate-all-exports.py src/omnibase_core/models/

Exit Codes:
    0: All validations passed
    1: Validation errors found (items in __all__ but not defined, or
       star imports when --fail-on-star is used)

Note:
    - __init__.py files are excluded (they re-export from submodules)
    - Test files are excluded
    - Files without __all__ are skipped (separate concern)
    - Star imports (from x import *) are warned by default, use --fail-on-star
      to treat them as errors since they make __all__ validation unreliable
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import NamedTuple


class StarImportInfo(NamedTuple):
    """Information about a star import in a file."""

    module: str  # The module being imported from
    line_no: int  # Line number of the import


class ExportValidationResult(NamedTuple):
    """Result of validating a single file's __all__ exports."""

    file_path: Path
    defined_names: set[str]
    all_exports: set[str]
    extra_exports: set[str]  # In __all__ but not defined - ERROR
    missing_exports: set[str]  # Defined but not in __all__ - WARNING (optional)
    star_imports: list[StarImportInfo]  # Star imports found - WARNING
    has_all: bool
    is_valid: bool
    error: str | None


class ModuleLevelDefinitionsFinder(ast.NodeVisitor):
    """AST visitor to find all module-level definitions and imports.

    Note:
        This visitor only processes module-level nodes. By not calling
        generic_visit() in class/function visitors, we avoid recursing
        into nested scopes where definitions would not be module-level.
        This approach is simpler than tracking depth since we only care
        about top-level definitions.
    """

    def __init__(self) -> None:
        self.class_names: set[str] = set()
        self.function_names: set[str] = set()
        self.constant_names: set[str] = set()
        self.import_names: set[str] = set()
        self.import_aliases: set[str] = set()
        self.star_imports: list[StarImportInfo] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Record class definitions at module level.

        Note: We don't call generic_visit() here because nested classes
        within class bodies are not module-level definitions.
        """
        self.class_names.add(node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Record function definitions at module level.

        Note: We don't call generic_visit() here because nested functions
        within function bodies are not module-level definitions.
        """
        self.function_names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Record async function definitions at module level.

        Note: We don't call generic_visit() here because nested functions
        within function bodies are not module-level definitions.
        """
        self.function_names.add(node.name)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Record module-level assignments (constants, aliases)."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                # Skip __all__ and other dunder attributes
                if not name.startswith("__"):
                    self.constant_names.add(name)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Record annotated assignments at module level."""
        if isinstance(node.target, ast.Name):
            name = node.target.id
            if not name.startswith("__"):
                self.constant_names.add(name)
        self.generic_visit(node)

    def visit_TypeAlias(self, node: ast.TypeAlias) -> None:
        """Record PEP 695 type alias statements (Python 3.12+)."""
        # TypeAlias.name is an ast.Name node containing the alias name
        if isinstance(node.name, ast.Name):
            self.constant_names.add(node.name.id)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Record regular imports."""
        for alias in node.names:
            # Use alias name if present, otherwise use module name
            name = alias.asname if alias.asname else alias.name
            # For dotted imports like 'import os.path', only the first part
            # is available without the alias
            if "." in name and not alias.asname:
                name = name.split(".")[0]
            self.import_names.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Record from imports."""
        for alias in node.names:
            if alias.name == "*":
                # Track star imports - they make __all__ validation unreliable
                module_name = node.module if node.module else "<relative>"
                self.star_imports.append(
                    StarImportInfo(module=module_name, line_no=node.lineno)
                )
                continue
            # Use alias name if present, otherwise use imported name
            name = alias.asname if alias.asname else alias.name
            self.import_names.add(name)
            if alias.asname:
                self.import_aliases.add(alias.asname)
        self.generic_visit(node)

    @property
    def all_defined_names(self) -> set[str]:
        """Get all names defined or imported at module level."""
        return (
            self.class_names
            | self.function_names
            | self.constant_names
            | self.import_names
        )

    @property
    def public_defined_names(self) -> set[str]:
        """Get public names (not starting with _) defined at module level."""
        all_names = self.all_defined_names
        return {name for name in all_names if not name.startswith("_")}


class AllExtractor(ast.NodeVisitor):
    """AST visitor to extract __all__ list contents."""

    def __init__(self) -> None:
        self.all_names: set[str] = set()
        self.has_all: bool = False
        self.all_line: int | None = None

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for __all__ assignment."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                self.has_all = True
                self.all_line = node.lineno
                self._extract_names(node.value)
        self.generic_visit(node)

    def _extract_names(self, value: ast.expr) -> None:
        """Extract string names from __all__ list/tuple."""
        if isinstance(value, ast.List | ast.Tuple):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.all_names.add(elt.value)


def validate_file(
    file_path: Path, warn_missing: bool = False
) -> ExportValidationResult:
    """
    Validate a Python file's __all__ exports.

    Args:
        file_path: Path to the Python file
        warn_missing: If True, also check for public names not in __all__

    Returns:
        ExportValidationResult with validation details
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

        # Find all module-level definitions and imports
        defs_finder = ModuleLevelDefinitionsFinder()
        defs_finder.visit(tree)

        # Extract __all__ contents
        all_extractor = AllExtractor()
        all_extractor.visit(tree)

        # If no __all__, skip this file (not an error)
        if not all_extractor.has_all:
            return ExportValidationResult(
                file_path=file_path,
                defined_names=defs_finder.all_defined_names,
                all_exports=set(),
                extra_exports=set(),
                missing_exports=set(),
                star_imports=defs_finder.star_imports,
                has_all=False,
                is_valid=True,  # Not having __all__ is not a validation error
                error=None,
            )

        defined_names = defs_finder.all_defined_names
        all_exports = all_extractor.all_names

        # Find items in __all__ that are not defined - this is an ERROR
        extra_exports = all_exports - defined_names

        # Find public items not in __all__ - this is a WARNING (optional)
        missing_exports: set[str] = set()
        if warn_missing:
            public_names = defs_finder.public_defined_names
            missing_exports = public_names - all_exports

        # File is valid if there are no extra exports (items in __all__ but not defined)
        is_valid = len(extra_exports) == 0

        return ExportValidationResult(
            file_path=file_path,
            defined_names=defined_names,
            all_exports=all_exports,
            extra_exports=extra_exports,
            missing_exports=missing_exports,
            star_imports=defs_finder.star_imports,
            has_all=True,
            is_valid=is_valid,
            error=None,
        )

    except SyntaxError as e:
        return ExportValidationResult(
            file_path=file_path,
            defined_names=set(),
            all_exports=set(),
            extra_exports=set(),
            missing_exports=set(),
            star_imports=[],
            has_all=False,
            is_valid=False,
            error=f"Syntax error: {e}",
        )
    except Exception as e:
        return ExportValidationResult(
            file_path=file_path,
            defined_names=set(),
            all_exports=set(),
            extra_exports=set(),
            missing_exports=set(),
            star_imports=[],
            has_all=False,
            is_valid=False,
            error=f"Error: {e}",
        )


def should_exclude_file(filepath: Path) -> bool:
    """
    Check if file should be excluded from validation.

    Args:
        filepath: Path to check

    Returns:
        True if file should be excluded

    Note:
        Uses pathlib.Path.parts for cross-platform path matching,
        ensuring compatibility with both Unix and Windows path separators.
    """
    # Get path parts for cross-platform directory matching
    parts = filepath.parts

    # Exclude __init__.py files (they re-export from submodules)
    if filepath.name == "__init__.py":
        return True

    # Exclude test files
    if (
        "tests" in parts
        or filepath.name.startswith("test_")
        or filepath.name.endswith("_test.py")
    ):
        return True

    # Exclude archived directories
    if "archived" in parts or "archive" in parts:
        return True

    # Exclude validation scripts themselves
    if "scripts" in parts and "validation" in parts:
        return True

    # Exclude __pycache__ directories
    if "__pycache__" in parts:
        return True

    # Exclude hidden directories (directories starting with '.')
    if any(part.startswith(".") and part != "." for part in parts):
        return True

    return False


def find_python_files(paths: list[Path]) -> list[Path]:
    """
    Find all Python files to validate.

    Args:
        paths: List of paths (files or directories)

    Returns:
        List of Python file paths to validate
    """
    python_files: list[Path] = []

    for path in paths:
        if path.is_file():
            if path.suffix == ".py" and not should_exclude_file(path):
                python_files.append(path)
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                if not should_exclude_file(py_file):
                    python_files.append(py_file)

    return sorted(python_files)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate __all__ exports match actual module definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to check (default: src/omnibase_core/)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--warn-missing",
        "-w",
        action="store_true",
        help="Warn about public names not in __all__",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=None,
        help="Source directory (default: src/omnibase_core/)",
    )
    parser.add_argument(
        "--fail-on-star",
        action="store_true",
        help="Treat star imports as errors (fail validation)",
    )

    args = parser.parse_args()

    # Determine paths to check
    if args.paths:
        paths = [p.resolve() for p in args.paths]
    elif args.src_dir:
        paths = [args.src_dir.resolve()]
    else:
        # Try to find from current working directory
        cwd = Path.cwd()
        src_dir = cwd / "src" / "omnibase_core"

        if not src_dir.exists():
            # Try from script location
            script_dir = Path(__file__).parent
            src_dir = script_dir.parent.parent / "src" / "omnibase_core"

        if not src_dir.exists():
            print(f"Error: Source directory not found: {src_dir}", file=sys.stderr)
            return 1

        paths = [src_dir]

    # Find Python files
    python_files = find_python_files(paths)

    if not python_files:
        print("No Python files found to validate")
        return 0

    if args.verbose:
        print(f"Validating {len(python_files)} Python files")
        print()

    # Validate each file
    results: list[ExportValidationResult] = []
    files_with_all = 0
    files_with_errors = 0
    files_with_warnings = 0
    files_with_star_imports = 0

    for file_path in python_files:
        result = validate_file(file_path, warn_missing=args.warn_missing)
        results.append(result)

        if result.has_all:
            files_with_all += 1

        if not result.is_valid:
            files_with_errors += 1

        if result.missing_exports:
            files_with_warnings += 1

        if result.star_imports:
            files_with_star_imports += 1

    # Report results
    invalid_results = [r for r in results if not r.is_valid and r.error is None]
    error_results = [r for r in results if r.error is not None]
    warning_results = [r for r in results if r.missing_exports]
    star_import_results = [r for r in results if r.star_imports]

    # Star imports are errors if --fail-on-star, otherwise warnings
    has_star_import_errors = args.fail_on_star and star_import_results
    has_failures = bool(invalid_results or error_results or has_star_import_errors)

    if has_failures:
        print("__all__ Export Validation FAILED")
        print("=" * 60)
        print()

        # Report errors first (items in __all__ but not defined)
        if invalid_results:
            print("ERRORS: Items in __all__ but not defined in module:")
            print("-" * 60)
            for result in invalid_results:
                try:
                    relative_path = result.file_path.relative_to(Path.cwd())
                except ValueError:
                    relative_path = result.file_path
                print(f"\nFile: {relative_path}")
                print(
                    f"  Extra in __all__ (not defined): {sorted(result.extra_exports)}"
                )
                if args.verbose:
                    print(f"  Defined names: {sorted(result.defined_names)}")
                    print(f"  __all__ exports: {sorted(result.all_exports)}")
            print()

        # Report parse/processing errors
        if error_results:
            print("ERRORS: Files that could not be parsed:")
            print("-" * 60)
            for result in error_results:
                try:
                    relative_path = result.file_path.relative_to(Path.cwd())
                except ValueError:
                    relative_path = result.file_path
                print(f"\nFile: {relative_path}")
                print(f"  {result.error}")
            print()

        # Report star import errors (when --fail-on-star)
        if has_star_import_errors:
            print("ERRORS: Star imports make __all__ validation unreliable:")
            print("-" * 60)
            for result in star_import_results:
                try:
                    relative_path = result.file_path.relative_to(Path.cwd())
                except ValueError:
                    relative_path = result.file_path
                print(f"\nFile: {relative_path}")
                for star_import in result.star_imports:
                    print(
                        f"  Line {star_import.line_no}: "
                        f"from {star_import.module} import *"
                    )
            print()

    # Report star import warnings (when not --fail-on-star)
    if star_import_results and not args.fail_on_star:
        print("WARNINGS: Star imports found (use --fail-on-star to treat as errors):")
        print("-" * 60)
        for result in star_import_results:
            try:
                relative_path = result.file_path.relative_to(Path.cwd())
            except ValueError:
                relative_path = result.file_path
            print(f"\nFile: {relative_path}")
            for star_import in result.star_imports:
                print(
                    f"  Line {star_import.line_no}: from {star_import.module} import *"
                )
        print()
        print("Note: Star imports make it impossible to reliably validate __all__.")
        print("      Consider replacing with explicit imports.")
        print()

    # Report warnings (optional - items defined but not in __all__)
    if args.warn_missing and warning_results:
        print("WARNINGS: Public names not in __all__:")
        print("-" * 60)
        for result in warning_results:
            try:
                relative_path = result.file_path.relative_to(Path.cwd())
            except ValueError:
                relative_path = result.file_path
            print(f"\nFile: {relative_path}")
            print(f"  Missing from __all__: {sorted(result.missing_exports)}")
        print()

    # Summary
    print("=" * 60)
    print("Summary:")
    print(f"  Total files scanned: {len(python_files)}")
    print(f"  Files with __all__: {files_with_all}")
    print(f"  Files with errors: {files_with_errors}")
    if files_with_star_imports:
        star_status = "errors" if args.fail_on_star else "warnings"
        print(f"  Files with star imports ({star_status}): {files_with_star_imports}")
    if args.warn_missing:
        print(f"  Files with warnings: {files_with_warnings}")

    if has_failures:
        print()
        print("FAILURE: Found validation errors")
        print(
            "Fix the issues above to ensure __all__ matches actual module definitions"
        )
        return 1

    # Always print success message for consistency with sibling scripts
    print()
    print("SUCCESS: All __all__ exports are valid")

    if args.verbose:
        print()
        # Show files with __all__
        files_with_valid_all = [r for r in results if r.has_all and r.is_valid]
        if files_with_valid_all:
            print("Files with valid __all__:")
            for result in files_with_valid_all:
                try:
                    relative_path = result.file_path.relative_to(Path.cwd())
                except ValueError:
                    relative_path = result.file_path
                exports = sorted(result.all_exports)
                if len(exports) <= 5:
                    print(f"  {relative_path}: {exports}")
                else:
                    print(f"  {relative_path}: [{len(exports)} exports]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
