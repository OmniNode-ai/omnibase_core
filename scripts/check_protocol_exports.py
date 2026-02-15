#!/usr/bin/env python3
"""
ONEX Protocol __all__ Exports Validation.

Validates that protocol files have correct __all__ exports that match
the Protocol class definitions in each file.

This ensures:
1. Every Protocol class is exported in __all__
2. __all__ doesn't contain non-existent names
3. Consistent exports across all protocol files

Usage:
    uv run python scripts/check_protocol_exports.py
    uv run python scripts/check_protocol_exports.py --verbose
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import NamedTuple


class ProtocolExportResult(NamedTuple):
    """Result of validating a single protocol file's exports."""

    file_path: Path
    defined_protocols: set[str]
    exported_names: set[str]
    missing_exports: set[str]
    extra_exports: set[str]
    has_all: bool
    is_valid: bool
    error: str | None


class DefinedNamesFinder(ast.NodeVisitor):
    """AST visitor to find Protocol classes and type aliases defined in file."""

    def __init__(self) -> None:
        self.protocol_classes: set[str] = set()
        self.type_aliases: set[str] = set()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check if class inherits from Protocol."""
        if self._is_protocol_class(node):
            self.protocol_classes.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for type alias assignments (e.g., ContextValue = ProtocolContextValue)."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Skip __all__ and dunder names
                if target.id.startswith("__"):
                    continue
                # Capture type aliases that reference Protocol classes
                # These are typically PascalCase names assigned to other names
                if target.id[0].isupper():
                    self.type_aliases.add(target.id)
        self.generic_visit(node)

    def _is_protocol_class(self, node: ast.ClassDef) -> bool:
        """Check if a class inherits from Protocol."""
        for base in node.bases:
            # Direct Protocol base
            if isinstance(base, ast.Name) and base.id == "Protocol":
                return True
            # Qualified Protocol base (e.g., typing.Protocol)
            if isinstance(base, ast.Attribute) and base.attr == "Protocol":
                return True
            # Generic Protocol (e.g., Protocol[T_co])
            if isinstance(base, ast.Subscript):
                if isinstance(base.value, ast.Name) and base.value.id == "Protocol":
                    return True
                if (
                    isinstance(base.value, ast.Attribute)
                    and base.value.attr == "Protocol"
                ):
                    return True
        return False

    @property
    def all_defined_names(self) -> set[str]:
        """Get all defined names (protocols + type aliases)."""
        return self.protocol_classes | self.type_aliases


class AllExtractor(ast.NodeVisitor):
    """AST visitor to extract __all__ list contents."""

    def __init__(self) -> None:
        self.all_names: set[str] = set()
        self.has_all: bool = False

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for __all__ assignment."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                self.has_all = True
                self._extract_names(node.value)
        self.generic_visit(node)

    def _extract_names(self, value: ast.expr) -> None:
        """Extract string names from __all__ list/tuple."""
        if isinstance(value, ast.List | ast.Tuple):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.all_names.add(elt.value)


def validate_protocol_file(file_path: Path) -> ProtocolExportResult:
    """
    Validate a protocol file's __all__ exports.

    Args:
        file_path: Path to the protocol file

    Returns:
        ProtocolExportResult with validation details
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

        # Find Protocol classes and type aliases
        names_finder = DefinedNamesFinder()
        names_finder.visit(tree)

        # Extract __all__ contents
        all_extractor = AllExtractor()
        all_extractor.visit(tree)

        defined_names = names_finder.all_defined_names
        exported_names = all_extractor.all_names
        has_all = all_extractor.has_all

        # Calculate mismatches
        # Only check Protocol classes for missing exports (type aliases are optional)
        missing_exports = names_finder.protocol_classes - exported_names
        # Extra exports must be defined names (Protocol classes or type aliases)
        extra_exports = exported_names - defined_names

        # A file is valid if:
        # 1. It has __all__ defined
        # 2. All Protocol classes are exported
        # 3. No non-existent names in __all__
        is_valid = has_all and not missing_exports and not extra_exports

        return ProtocolExportResult(
            file_path=file_path,
            defined_protocols=names_finder.protocol_classes,
            exported_names=exported_names,
            missing_exports=missing_exports,
            extra_exports=extra_exports,
            has_all=has_all,
            is_valid=is_valid,
            error=None,
        )

    except SyntaxError as e:
        return ProtocolExportResult(
            file_path=file_path,
            defined_protocols=set(),
            exported_names=set(),
            missing_exports=set(),
            extra_exports=set(),
            has_all=False,
            is_valid=False,
            error=f"Syntax error: {e}",
        )
    except Exception as e:
        return ProtocolExportResult(
            file_path=file_path,
            defined_protocols=set(),
            exported_names=set(),
            missing_exports=set(),
            extra_exports=set(),
            has_all=False,
            is_valid=False,
            error=f"Error: {e}",
        )


def find_protocol_files(protocols_dir: Path) -> list[Path]:
    """
    Find all protocol files to validate.

    Only validates protocol_*.py files (not __init__.py or other files).
    Protocol definitions should be in individual protocol_*.py files.

    Args:
        protocols_dir: Root protocols directory

    Returns:
        List of protocol file paths
    """
    protocol_files: list[Path] = []

    for py_file in protocols_dir.rglob("protocol_*.py"):
        # Skip __init__.py files
        if py_file.name == "__init__.py":
            continue
        protocol_files.append(py_file)

    return sorted(protocol_files)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate protocol __all__ exports match Protocol class definitions"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--protocols-dir",
        type=Path,
        default=None,
        help="Protocols directory (default: src/omnibase_core/protocols)",
    )

    args = parser.parse_args()

    # Determine protocols directory
    if args.protocols_dir:
        protocols_dir = args.protocols_dir
    else:
        # Try to find from current working directory
        cwd = Path.cwd()
        protocols_dir = cwd / "src" / "omnibase_core" / "protocols"

        if not protocols_dir.exists():
            # Try from script location
            script_dir = Path(__file__).parent
            protocols_dir = script_dir.parent / "src" / "omnibase_core" / "protocols"

    if not protocols_dir.exists():
        print(f"Error: Protocols directory not found: {protocols_dir}", file=sys.stderr)
        return 1

    # Find protocol files
    protocol_files = find_protocol_files(protocols_dir)

    if not protocol_files:
        print("No protocol files found to validate")
        return 0

    if args.verbose:
        print(f"Validating {len(protocol_files)} protocol files in {protocols_dir}")
        print()

    # Validate each file
    results: list[ProtocolExportResult] = []
    for file_path in protocol_files:
        result = validate_protocol_file(file_path)
        results.append(result)

    # Report results
    invalid_results = [r for r in results if not r.is_valid]
    valid_count = len(results) - len(invalid_results)

    if invalid_results:
        print("Protocol __all__ Export Validation FAILED")
        print("=" * 60)
        print()

        for result in invalid_results:
            relative_path = result.file_path.relative_to(
                protocols_dir.parent.parent.parent
            )
            print(f"File: {relative_path}")

            if result.error:
                print(f"  Error: {result.error}")
            else:
                if not result.has_all:
                    print("  Missing __all__ definition")

                if result.missing_exports:
                    print(f"  Missing from __all__: {sorted(result.missing_exports)}")

                if result.extra_exports:
                    print(
                        f"  Extra in __all__ (not defined): {sorted(result.extra_exports)}"
                    )

                if args.verbose:
                    print(f"  Defined Protocols: {sorted(result.defined_protocols)}")
                    print(f"  Exported Names: {sorted(result.exported_names)}")

            print()

        print(
            f"Summary: {len(invalid_results)} file(s) with issues, {valid_count} valid"
        )
        return 1

    if args.verbose:
        print(f"All {len(results)} protocol files have valid __all__ exports")
        print()
        for result in results:
            relative_path = result.file_path.relative_to(
                protocols_dir.parent.parent.parent
            )
            protocols = sorted(result.defined_protocols)
            print(f"  {relative_path}: {protocols}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
