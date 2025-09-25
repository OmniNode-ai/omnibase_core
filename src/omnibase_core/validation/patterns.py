"""
Pattern validation tools for ONEX compliance.

This module provides validation functions for various code patterns:
- Pydantic pattern validation
- Generic pattern validation
- Anti-pattern detection
- Naming convention validation
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Protocol

from .validation_utils import ValidationResult


class PatternChecker(Protocol):
    """Protocol for pattern checker classes."""

    issues: list[str]

    def visit(self, node: ast.AST) -> None: ...


class PydanticPatternChecker(ast.NodeVisitor):
    """Check for proper Pydantic patterns and anti-patterns."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[str] = []
        self.classes_checked = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to check Pydantic patterns."""
        # Check if this is a Pydantic model
        is_pydantic = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                is_pydantic = True
                break
            if isinstance(base, ast.Attribute):
                if (
                    isinstance(base.value, ast.Name)
                    and base.value.id == "pydantic"
                    and base.attr == "BaseModel"
                ):
                    is_pydantic = True
                    break

        if is_pydantic:
            self.classes_checked += 1
            self._check_pydantic_class(node)

        self.generic_visit(node)

    def _check_pydantic_class(self, node: ast.ClassDef) -> None:
        """Check a Pydantic class for pattern violations."""
        class_name = node.name

        # Check naming convention
        if not class_name.startswith("Model"):
            self.issues.append(
                f"Line {node.lineno}: Pydantic model '{class_name}' should start with 'Model'",
            )

        # Check field patterns
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                annotation = item.annotation

                # Check for string ID fields that should be UUID
                if field_name.endswith("_id") and self._is_str_annotation(annotation):
                    self.issues.append(
                        f"Line {item.lineno}: Field '{field_name}' should use UUID type instead of str",
                    )

                # Check for category/type/status fields that should be enums
                if field_name in [
                    "category",
                    "type",
                    "status",
                ] and self._is_str_annotation(annotation):
                    self.issues.append(
                        f"Line {item.lineno}: Field '{field_name}' should use Enum instead of str",
                    )

                # Check for name fields that reference entities
                if field_name.endswith("_name") and self._is_str_annotation(annotation):
                    self.issues.append(
                        f"Line {item.lineno}: Field '{field_name}' might reference an entity - consider using ID + display_name pattern",
                    )

    def _is_str_annotation(self, annotation: ast.AST) -> bool:
        """Check if annotation is str type."""
        if isinstance(annotation, ast.Name):
            return bool(annotation.id == "str")
        if isinstance(annotation, ast.Constant):
            return bool(annotation.value == "str")
        return False


class NamingConventionChecker(ast.NodeVisitor):
    """Check naming conventions."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class naming conventions."""
        class_name = node.name

        # Check for anti-pattern names
        anti_patterns = [
            "Manager",
            "Handler",
            "Helper",
            "Utility",
            "Util",
            "Service",
            "Controller",
            "Processor",
            "Worker",
        ]

        for pattern in anti_patterns:
            if pattern.lower() in class_name.lower():
                self.issues.append(
                    f"Line {node.lineno}: Class name '{class_name}' contains anti-pattern '{pattern}' - use specific domain terminology",
                )

        # Check naming style
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", class_name):
            self.issues.append(
                f"Line {node.lineno}: Class name '{class_name}' should use PascalCase",
            )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function naming conventions."""
        func_name = node.name

        # Skip special methods
        if func_name.startswith("__") and func_name.endswith("__"):
            return

        # Check naming style
        if not re.match(r"^[a-z_][a-z0-9_]*$", func_name):
            self.issues.append(
                f"Line {node.lineno}: Function name '{func_name}' should use snake_case",
            )

        self.generic_visit(node)


class GenericPatternChecker(ast.NodeVisitor):
    """Check for generic anti-patterns."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function patterns."""
        func_name = node.name

        # Check for overly generic function names
        generic_names = [
            "process",
            "handle",
            "execute",
            "run",
            "do",
            "perform",
            "manage",
            "control",
            "work",
            "operate",
            "action",
        ]

        if func_name.lower() in generic_names:
            self.issues.append(
                f"Line {node.lineno}: Function name '{func_name}' is too generic - use specific domain terminology",
            )

        # Check for functions with too many parameters
        if len(node.args.args) > 5:
            self.issues.append(
                f"Line {node.lineno}: Function '{func_name}' has {len(node.args.args)} parameters - consider using a model or breaking into smaller functions",
            )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class patterns."""
        class_name = node.name

        # Count methods to detect god classes
        method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))

        if method_count > 10:
            self.issues.append(
                f"Line {node.lineno}: Class '{class_name}' has {method_count} methods - consider breaking into smaller classes",
            )

        self.generic_visit(node)


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
