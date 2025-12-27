#!/usr/bin/env python3
"""
Validate proper generic patterns in method signatures.

Catches redundant union types when generics should be used instead.
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import NamedTuple


class GenericViolation(NamedTuple):
    """Represents a generic pattern violation."""

    file_path: str
    line_number: int
    method_name: str
    violation_type: str
    current_signature: str
    suggested_fix: str
    message: str


class GenericPatternValidator(ast.NodeVisitor):
    """AST visitor to detect generic pattern violations."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[GenericViolation] = []
        self.has_typevar = False
        self.typevar_names: set[str] = set()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track TypeVar imports."""
        if node.module == "typing":
            for alias in node.names:
                if alias.name == "TypeVar":
                    self.has_typevar = True
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track TypeVar assignments like T = TypeVar('T')."""
        if isinstance(node.value, ast.Call):
            if (
                isinstance(node.value.func, ast.Name)
                and node.value.func.id == "TypeVar"
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.typevar_names.add(target.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check method signatures for generic pattern violations."""
        if self._is_method(node):
            self._check_redundant_unions(node)
        self.generic_visit(node)

    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if function is a method (has self parameter)."""
        return len(node.args.args) > 0 and node.args.args[0].arg == "self"

    def _check_redundant_unions(self, node: ast.FunctionDef) -> None:
        """Check for redundant unions when generics should be used."""
        # Skip if no TypeVar available
        if not self.has_typevar or not self.typevar_names:
            return

        # Check parameters for redundant unions
        for arg in node.args.args[1:]:  # Skip 'self'
            if arg.annotation:
                self._check_parameter_annotation(node, arg)

        # Check return type for redundant unions
        if node.returns:
            self._check_return_annotation(node)

    def _check_parameter_annotation(self, node: ast.FunctionDef, arg: ast.arg) -> None:
        """Check parameter annotation for redundant unions."""
        annotation_str = self._annotation_to_string(arg.annotation)

        # Pattern: str | float | bool (should use T)
        if self._is_redundant_primitive_union(annotation_str):
            self.violations.append(
                GenericViolation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    method_name=node.name,
                    violation_type="redundant_union_parameter",
                    current_signature=f"{arg.arg}: {annotation_str}",
                    suggested_fix=f"{arg.arg}: T",
                    message=f"Parameter '{arg.arg}' uses redundant union '{annotation_str}' instead of generic type T",
                )
            )

    def _check_return_annotation(self, node: ast.FunctionDef) -> None:
        """Check return annotation for redundant unions."""
        annotation_str = self._annotation_to_string(node.returns)

        # Pattern: T | str | float | bool (should just be T)
        if self._is_redundant_generic_union(annotation_str):
            typevar_name = self._extract_typevar_from_union(annotation_str)
            self.violations.append(
                GenericViolation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    method_name=node.name,
                    violation_type="redundant_union_return",
                    current_signature=f"-> {annotation_str}",
                    suggested_fix=f"-> {typevar_name}" if typevar_name else "-> T",
                    message=f"Return type '{annotation_str}' mixes generic with explicit types - use only generic type",
                )
            )

    def _annotation_to_string(self, annotation: ast.AST) -> str:
        """Convert AST annotation to string representation."""
        try:
            return ast.unparse(annotation)
        except Exception:
            return str(annotation)

    def _is_redundant_primitive_union(self, annotation_str: str) -> bool:
        """Check if annotation is a redundant primitive union."""
        # Patterns like: str | float | bool, str | int | bool, etc.
        primitives = {"str", "int", "float", "bool"}

        if " | " not in annotation_str:
            return False

        parts = {part.strip() for part in annotation_str.split("|")}

        # If all parts are primitives and there are 2+ types, could use generic
        if len(parts) >= 2 and parts.issubset(primitives):
            return True

        return False

    def _is_redundant_generic_union(self, annotation_str: str) -> bool:
        """Check if annotation mixes generic with explicit types."""
        if " | " not in annotation_str:
            return False

        parts = {part.strip() for part in annotation_str.split("|")}
        primitives = {"str", "int", "float", "bool", "None"}

        # Check if we have both TypeVar and primitives
        has_typevar = any(part in self.typevar_names for part in parts)
        has_primitives = any(part in primitives for part in parts)

        return has_typevar and has_primitives

    def _extract_typevar_from_union(self, annotation_str: str) -> str | None:
        """Extract TypeVar name from union."""
        parts = {part.strip() for part in annotation_str.split("|")}
        for part in parts:
            if part in self.typevar_names:
                return part
        return None


def validate_file(file_path: Path) -> list[GenericViolation]:
    """Validate a single Python file for generic pattern violations."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        validator = GenericPatternValidator(str(file_path))
        validator.visit(tree)
        return validator.violations

    except SyntaxError:
        return []
    except Exception:
        return []


def validate_directory(
    directory: Path, max_violations: int = 0
) -> tuple[list[GenericViolation], bool]:
    """Validate all Python files in directory."""
    all_violations = []

    for py_file in directory.rglob("*.py"):
        if py_file.name.startswith("."):
            continue

        violations = validate_file(py_file)
        all_violations.extend(violations)

    return all_violations, len(all_violations) <= max_violations


def format_violations(violations: list[GenericViolation]) -> str:
    """Format violations for output."""
    if not violations:
        return "✅ No generic pattern violations found"

    output = []
    output.append(f"❌ Found {len(violations)} generic pattern violation(s):")
    output.append("")

    # Group by file
    by_file = {}
    for violation in violations:
        if violation.file_path not in by_file:
            by_file[violation.file_path] = []
        by_file[violation.file_path].append(violation)

    for file_path, file_violations in by_file.items():
        output.append(f"❌ {file_path}")
        for violation in file_violations:
            output.append(
                f"   Line {violation.line_number}: Method '{violation.method_name}' - {violation.message}"
            )
            output.append(f"   Current: {violation.current_signature}")
            output.append(f"   Fix: {violation.suggested_fix}")
            output.append("")

    output.append("🔧 FIXES:")
    output.append("1. Use generic type T instead of explicit union types")
    output.append("2. Don't mix generic types with explicit types in unions")
    output.append("3. Let the type system infer types from generic parameters")
    output.append("")
    output.append("📚 Examples:")
    output.append("❌ BAD:")
    output.append(
        "   def get_value(self, key: str, default: str | float | bool) -> str | float | bool:"
    )
    output.append("   def set_value(self, key: str, value: str | int | bool) -> None:")
    output.append("   def process(self, data: T) -> T | str | None:")
    output.append("")
    output.append("✅ GOOD:")
    output.append("   def get_value(self, key: str, default: T) -> T:")
    output.append("   def set_value(self, key: str, value: T) -> None:")
    output.append("   def process(self, data: T) -> T | None:")

    return "\n".join(output)


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate generic patterns")
    parser.add_argument("path", help="File or directory to validate")
    parser.add_argument(
        "--max-violations", type=int, default=0, help="Maximum allowed violations"
    )

    args = parser.parse_args()
    path = Path(args.path)

    if path.is_file():
        violations = validate_file(path)
        passed = len(violations) <= args.max_violations
    else:
        violations, passed = validate_directory(path, args.max_violations)

    print(format_violations(violations))

    if not passed:
        print("❌ Generic pattern validation FAILED")
        print(
            f"❌ Violation count ({len(violations)}) exceeds maximum allowed ({args.max_violations})"
        )
        sys.exit(1)
    else:
        print("✅ Generic pattern validation PASSED")


if __name__ == "__main__":
    main()
