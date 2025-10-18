#!/usr/bin/env python3
"""
ONEX Single Class Per File Validation

Enforces the "one class per file" rule to maintain clear module boundaries
and improve code organization. Exceptions:
- Multiple enums in the same file are allowed (enum collections)
- Test files are excluded
- __init__.py files are excluded

This promotes better code organization and maintains the ONEX framework
architecture principles.
"""

import argparse
import ast
import sys
from enum import Enum
from pathlib import Path
from typing import Any


class ClassDefinitionDetector(ast.NodeVisitor):
    """AST visitor to detect class definitions in Python code."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.classes: list[tuple[int, str, bool]] = []  # (line_num, name, is_enum)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check if class definition is an Enum."""
        is_enum = self._is_enum_class(node)
        self.classes.append((node.lineno, node.name, is_enum))
        self.generic_visit(node)

    def _is_enum_class(self, node: ast.ClassDef) -> bool:
        """Check if a class inherits from Enum."""
        for base in node.bases:
            # Direct Enum base
            if isinstance(base, ast.Name) and base.id == "Enum":
                return True
            # Qualified Enum base (e.g., enum.Enum)
            if isinstance(base, ast.Attribute) and base.attr == "Enum":
                return True
            # IntEnum, StrEnum, etc.
            if isinstance(base, ast.Name) and "Enum" in base.id:
                return True
            if isinstance(base, ast.Attribute) and "Enum" in base.attr:
                return True
        return False


def check_file(filepath: Path) -> dict[str, Any]:
    """
    Check a Python file for single-class-per-file violations.

    Args:
        filepath: Path to the Python file to check

    Returns:
        Dictionary with validation results:
        - 'valid': bool - whether file passes validation
        - 'classes': list - classes found in file
        - 'violation_type': str - type of violation if any
        - 'message': str - violation message if any
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        detector = ClassDefinitionDetector(str(filepath))
        detector.visit(tree)

        # No classes = valid (utility modules, etc.)
        if not detector.classes:
            return {"valid": True, "classes": []}

        # Single class = valid
        if len(detector.classes) == 1:
            return {"valid": True, "classes": detector.classes}

        # Multiple classes - check if all are enums
        all_enums = all(is_enum for _, _, is_enum in detector.classes)
        if all_enums:
            return {
                "valid": True,
                "classes": detector.classes,
                "note": "Multiple enums allowed in same file",
            }

        # Multiple non-enum classes = violation
        non_enum_classes = [
            (line, name) for line, name, is_enum in detector.classes if not is_enum
        ]
        enum_classes = [
            (line, name) for line, name, is_enum in detector.classes if is_enum
        ]

        return {
            "valid": False,
            "classes": detector.classes,
            "non_enum_classes": non_enum_classes,
            "enum_classes": enum_classes,
            "violation_type": "multiple_classes",
            "message": f"Found {len(non_enum_classes)} non-enum class(es) and {len(enum_classes)} enum(s) in same file",
        }

    except SyntaxError:
        # Skip files with syntax errors (they'll be caught by other tools)
        return {"valid": True, "skipped": True, "reason": "syntax_error"}
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return {"valid": True, "skipped": True, "reason": f"error: {e}"}


def should_exclude_file(filepath: Path) -> bool:
    """
    Check if file should be excluded from validation.

    Args:
        filepath: Path to check

    Returns:
        True if file should be excluded
    """
    path_str = str(filepath)

    # Exclude test files
    if "/tests/" in path_str or "/test_" in path_str:
        return True

    # Exclude __init__.py
    if filepath.name == "__init__.py":
        return True

    # Exclude archived directories
    if "/archived/" in path_str or "/archive/" in path_str:
        return True

    # Exclude validation scripts themselves
    if "/scripts/validation/" in path_str:
        return True

    return False


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate single class per file rule in Python code"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to check (defaults to src/)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Default to src/ if no paths provided
    paths = args.paths if args.paths else [Path("src/")]

    # Collect all Python files to check
    files_to_check: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            if not should_exclude_file(path):
                files_to_check.append(path)
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                if not should_exclude_file(py_file):
                    files_to_check.append(py_file)

    if not files_to_check:
        print("No Python files found to check")
        return 0

    total_violations = 0
    files_with_violations = []

    for filepath in sorted(files_to_check):
        result = check_file(filepath)

        if result.get("skipped"):
            if args.verbose:
                print(f"Skipped {filepath}: {result.get('reason', 'unknown')}")
            continue

        if not result["valid"]:
            total_violations += 1
            files_with_violations.append((filepath, result))

            print(f"\n{filepath}:")
            print(f"  {result['message']}")

            if result.get("non_enum_classes"):
                print("  Non-enum classes:")
                for line, name in result["non_enum_classes"]:
                    print(f"    Line {line}: {name}")

            if result.get("enum_classes"):
                print("  Enums:")
                for line, name in result["enum_classes"]:
                    print(f"    Line {line}: {name}")

        elif args.verbose and result["classes"]:
            class_count = len(result["classes"])
            note = result.get("note", "")
            if note:
                print(f"✓ {filepath}: {class_count} class(es) - {note}")
            else:
                print(f"✓ {filepath}: {class_count} class(es)")

    if total_violations > 0:
        print(
            f"\n❌ Found {total_violations} file(s) violating single-class-per-file rule"
        )
        print("\nGuidance:")
        print("  - Split files with multiple non-enum classes into separate files")
        print("  - Each class should have its own file with matching name")
        print("  - Multiple enums in one file are acceptable (enum collections)")
        print("\nExamples:")
        print("  ❌ node_orchestrator.py with 11 classes")
        print("  ✓ node_orchestrator.py (main class only)")
        print("  ✓ model_orchestrator_input.py (separate file)")
        print("  ✓ enum_workflow_states.py (multiple enums OK)")
        return 1

    if args.verbose:
        print(f"\n✓ Checked {len(files_to_check)} files - no violations found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
