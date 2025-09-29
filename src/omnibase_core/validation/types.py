"""
Type validation tools for ONEX compliance.

This module provides validation functions for proper type usage:
- Union type validation
- String typing anti-pattern detection
- Pydantic pattern validation
- Generic type validation
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from .validation_utils import ValidationResult


class ModelUnionPattern:
    """Represents a Union pattern for analysis."""

    def __init__(self, types: list[str], line: int, file_path: str):
        self.types = sorted(types)  # Sort for consistent comparison
        self.line = line
        self.file_path = file_path
        self.type_count = len(types)

    def __hash__(self) -> int:
        return hash(tuple(self.types))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ModelUnionPattern) and self.types == other.types

    def get_signature(self) -> str:
        """Get a string signature for this union pattern."""
        return f"Union[{', '.join(self.types)}]"


class UnionUsageChecker(ast.NodeVisitor):
    """Enhanced checker for Union type usage patterns."""

    def __init__(self, file_path: str):
        self.union_count = 0
        self.issues: list[str] = []
        self.file_path = file_path
        self.union_patterns: list[ModelUnionPattern] = []

        # Track problematic patterns
        self.complex_unions: list[ModelUnionPattern] = []
        self.primitive_heavy_unions: list[ModelUnionPattern] = []
        self.generic_unions: list[ModelUnionPattern] = []

        # Common problematic type combinations
        self.problematic_combinations = {
            frozenset(["str", "int", "bool", "float"]): "primitive_overload",
            frozenset(["str", "int", "bool", "dict"]): "mixed_primitive_complex",
            frozenset(["str", "int", "dict", "list"]): "mixed_primitive_complex",
            frozenset(["str", "int", "bool", "float", "dict"]): "everything_union",
            frozenset(["str", "int", "bool", "float", "list"]): "everything_union",
        }

    def _extract_type_name(self, node: ast.AST) -> str:
        """Extract type name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            return type(node.value).__name__
        if isinstance(node, ast.Subscript):
            # Handle List[str], Dict[str, int], etc.
            if isinstance(node.value, ast.Name):
                return node.value.id
        elif isinstance(node, ast.Attribute):
            # Handle module.Type patterns
            return f"{self._extract_type_name(node.value)}.{node.attr}"
        return "Unknown"

    def _analyze_union_pattern(self, union_pattern: ModelUnionPattern) -> None:
        """Analyze a union pattern for potential issues."""
        types_set = frozenset(union_pattern.types)

        # Check for complex unions (configurable complexity threshold)
        if union_pattern.type_count >= 3:
            self.complex_unions.append(union_pattern)

            # Check for specific problematic combinations
            for problem_set, problem_type in self.problematic_combinations.items():
                if problem_set.issubset(types_set):
                    if problem_type == "primitive_overload":
                        self.issues.append(
                            f"Line {union_pattern.line}: Union with 4+ primitive types "
                            f"{union_pattern.get_signature()} should use a specific type, generic TypeVar, or strongly-typed model",
                        )
                    elif problem_type == "mixed_primitive_complex":
                        self.issues.append(
                            f"Line {union_pattern.line}: Mixed primitive/complex Union "
                            f"{union_pattern.get_signature()} should use a specific type, generic TypeVar, or strongly-typed model",
                        )
                    elif problem_type == "everything_union":
                        self.issues.append(
                            f"Line {union_pattern.line}: Overly broad Union "
                            f"{union_pattern.get_signature()} should use a specific type, generic TypeVar, or proper domain model",
                        )

        # Check for redundant None patterns
        if "None" in union_pattern.types and union_pattern.type_count > 2:
            non_none_types = [t for t in union_pattern.types if t != "None"]
            if len(non_none_types) == 1:
                self.issues.append(
                    f"Line {union_pattern.line}: Use Optional[{non_none_types[0]}] "
                    f"instead of {union_pattern.get_signature()}",
                )

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Visit subscript nodes (e.g., Union[str, int])."""
        if isinstance(node.value, ast.Name) and node.value.id == "Union":
            self._process_union_types(node, node.slice, node.lineno)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Visit binary operation nodes (e.g., str | int | float)."""
        if isinstance(node.op, ast.BitOr):
            # Modern union syntax: str | int | float
            union_types = self._extract_union_from_binop(node)
            if len(union_types) >= 2:  # Only process if we have multiple types
                self.union_count += 1

                # Create union pattern for analysis
                union_pattern = ModelUnionPattern(
                    union_types, node.lineno, self.file_path
                )
                self.union_patterns.append(union_pattern)

                # Analyze the pattern
                self._analyze_union_pattern(union_pattern)

        self.generic_visit(node)

    def _extract_union_from_binop(self, node: ast.BinOp) -> list[str]:
        """Extract union types from modern union syntax (A | B | C)."""
        types = []

        def collect_types(n: ast.AST) -> None:
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                collect_types(n.left)
                collect_types(n.right)
            else:
                type_name = self._extract_type_name(n)
                if type_name not in types:  # Avoid duplicates
                    types.append(type_name)

        collect_types(node)
        return types

    def _process_union_types(
        self,
        node: ast.AST,
        slice_node: ast.AST,
        line_no: int,
    ) -> None:
        """Process union types from Union[...] syntax."""
        # Extract union types
        union_types = []
        if isinstance(slice_node, ast.Tuple):
            for elt in slice_node.elts:
                type_name = self._extract_type_name(elt)
                union_types.append(type_name)
        else:
            # Single element in Union (shouldn't happen, but handle it)
            type_name = self._extract_type_name(slice_node)
            union_types.append(type_name)

        self.union_count += 1

        # Create union pattern for analysis
        union_pattern = ModelUnionPattern(union_types, line_no, self.file_path)
        self.union_patterns.append(union_pattern)

        # Analyze the pattern
        self._analyze_union_pattern(union_pattern)

        # Check for Union with None
        if len(union_types) == 2 and "None" in union_types:
            self.issues.append(
                f"Line {line_no}: Use Optional[T] or T | None instead of T | None",
            )


def validate_union_usage_file(
    file_path: Path,
) -> tuple[int, list[str], list[ModelUnionPattern]]:
    """Validate Union usage in a Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        checker = UnionUsageChecker(str(file_path))
        checker.visit(tree)

        return checker.union_count, checker.issues, checker.union_patterns

    except Exception as e:
        return 0, [f"Error parsing {file_path}: {e}"], []


def validate_union_usage_directory(
    directory: Path,
    max_unions: int = 100,
    strict: bool = False,
) -> ValidationResult:
    """Validate Union usage in a directory."""
    python_files = []
    for py_file in directory.rglob("*.py"):
        # Filter out archived files, examples, and __pycache__
        if any(
            part in str(py_file)
            for part in [
                "/archived/",
                "archived",
                "/archive/",
                "archive",
                "/examples/",
                "examples",
                "__pycache__",
            ]
        ):
            continue
        python_files.append(py_file)

    if not python_files:
        return ValidationResult(
            success=True,
            errors=[],
            files_checked=0,
            metadata={"message": "No Python files to validate"},
        )

    total_unions = 0
    total_issues = []
    all_patterns = []

    # Process all files
    for py_file in python_files:
        union_count, issues, patterns = validate_union_usage_file(py_file)
        total_unions += union_count
        all_patterns.extend(patterns)

        if issues:
            total_issues.extend([f"{py_file}: {issue}" for issue in issues])

    success = (total_unions <= max_unions) and (not total_issues or not strict)

    return ValidationResult(
        success=success,
        errors=total_issues,
        files_checked=len(python_files),
        violations_found=len(total_issues),
        metadata={
            "validation_type": "union_usage",
            "total_unions": total_unions,
            "max_unions": max_unions,
            "complex_patterns": len([p for p in all_patterns if p.type_count >= 3]),
            "strict_mode": strict,
        },
    )


def validate_union_usage_cli() -> int:
    """CLI interface for union usage validation."""
    parser = argparse.ArgumentParser(
        description="Enhanced Union type usage validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool detects complex Union types that should be replaced with proper models:

• Unions with 3+ types that could be models
• Repeated union patterns across files
• Mixed primitive/complex type unions
• Overly broad unions that should use specific types, generics, or strongly-typed models

Examples of problematic patterns:
• Union[str, int, bool, float] → Use specific type (str), generic TypeVar, or domain-specific model
• Union[str, int, dict] → Use specific type or generic TypeVar
• Union[dict, list, str] → Use specific collection type or generic
        """,
    )
    parser.add_argument(
        "--max-unions",
        type=int,
        default=100,
        help="Maximum allowed Union types",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to validate")
    args = parser.parse_args()

    base_path = Path(args.path)
    if base_path.is_file() and base_path.suffix == ".py":
        # Single file validation
        union_count, issues, patterns = validate_union_usage_file(base_path)

        if issues:
            print(f"❌ Union validation issues found in {base_path}:")
            for issue in issues:
                print(f"   {issue}")
            return 1

        print(
            f"✅ Union validation: {union_count} unions in {base_path} (limit: {args.max_unions})",
        )
        return 0
    # Directory validation
    result = validate_union_usage_directory(base_path, args.max_unions, args.strict)

    if result.errors:
        print("❌ Union validation issues found:")
        for error in result.errors:
            print(f"   {error}")

    total_unions = result.metadata.get("total_unions", 0) if result.metadata else 0
    if total_unions > args.max_unions:
        print(
            f"❌ Union count exceeded: {total_unions} > {args.max_unions}",
        )
        return 1

    if result.errors:
        return 1

    total_unions_final = (
        result.metadata.get("total_unions", 0) if result.metadata else 0
    )
    print(
        f"✅ Union validation: {total_unions_final} unions in {result.files_checked} files",
    )
    return 0


if __name__ == "__main__":
    sys.exit(validate_union_usage_cli())
