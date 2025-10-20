from __future__ import annotations

from typing import Generic

"""
Pattern validation tools for ONEX compliance.

This module provides validation functions for various code patterns:
- Pydantic pattern validation
- Generic pattern validation
- Anti-pattern detection
- Naming convention validation
"""


import argparse
import ast
import sys
from pathlib import Path
from typing import Protocol

from .checker_generic_pattern import GenericPatternChecker
from .checker_naming_convention import NamingConventionChecker
from .checker_pydantic_pattern import PydanticPatternChecker
from .validation_utils import ValidationResult


class PatternChecker(Protocol):
    """Protocol for pattern checkers with issues tracking."""

    issues: list[str]

    def visit(self, node: ast.AST) -> None:
        """Visit an AST node."""
        ...


def validate_patterns_file(file_path: Path) -> list[str]:
    """Validate patterns in a Python file."""
    all_issues = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        # Run all pattern checkers
        checkers: list[PatternChecker] = [
            PydanticPatternChecker(str(file_path)),
            NamingConventionChecker(str(file_path)),
            GenericPatternChecker(str(file_path)),
        ]

        for checker in checkers:
            checker.visit(tree)
            all_issues.extend(checker.issues)

    except Exception as e:
        all_issues.append(f"Error parsing {file_path}: {e}")

    return all_issues


def validate_patterns_directory(
    directory: Path,
    strict: bool = False,
) -> ValidationResult:
    """Validate patterns in a directory."""
    python_files = []

    for py_file in directory.rglob("*.py"):
        # Skip excluded files
        if any(
            part in str(py_file)
            for part in [
                "__pycache__",
                ".git",
                "archived",
                "examples",
                "tests/fixtures",
            ]
        ):
            continue
        python_files.append(py_file)

    all_errors = []
    files_with_errors = []

    for py_file in python_files:
        issues = validate_patterns_file(py_file)
        if issues:
            files_with_errors.append(str(py_file))
            all_errors.extend([f"{py_file}: {issue}" for issue in issues])

    success = len(all_errors) == 0 or not strict

    return ValidationResult(
        success=success,
        errors=all_errors,
        files_checked=len(python_files),
        violations_found=len(all_errors),
        files_with_violations=len(files_with_errors),
        metadata={
            "validation_type": "patterns",
            "strict_mode": strict,
        },
    )


def validate_patterns_cli() -> int:
    """CLI interface for pattern validation."""
    parser = argparse.ArgumentParser(
        description="Validate code patterns for ONEX compliance",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["src/"],
        help="Directories to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )

    args = parser.parse_args()

    print("🔍 ONEX Pattern Validation")
    print("=" * 40)

    overall_result = ValidationResult(success=True, errors=[], files_checked=0)

    for directory in args.directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ Directory not found: {directory}")
            continue

        print(f"📁 Scanning {directory}...")
        result = validate_patterns_directory(dir_path, args.strict)

        # Merge results
        overall_result.success = overall_result.success and result.success
        overall_result.errors.extend(result.errors)
        overall_result.files_checked += result.files_checked

        if result.errors:
            print(f"\n❌ Pattern issues found in {directory}:")
            for error in result.errors:
                print(f"   {error}")

    print("\n📊 Pattern Validation Summary:")
    print(f"   • Files checked: {overall_result.files_checked}")
    print(f"   • Issues found: {len(overall_result.errors)}")

    if overall_result.success:
        print("✅ Pattern validation PASSED")
        return 0
    print("❌ Pattern validation FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(validate_patterns_cli())
