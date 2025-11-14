from typing import Any, Optional, TypeVar, Union

"""
UnionUsageChecker

Enhanced checker for Union type usage patterns.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

import ast

from omnibase_core.models.validation.model_union_pattern import ModelUnionPattern


class UnionUsageChecker(ast.NodeVisitor):
    """Enhanced checker for Union type usage patterns."""

    def __init__(self, file_path: str):
        self.union_count = 0
        self.issues: list[str] = []
        self.file_path = file_path
        self.union_patterns: list[ModelUnionPattern] = []
        self._in_union_binop = False  # Track if we're inside a union BinOp chain

        # Track problematic patterns
        self.complex_unions: list[ModelUnionPattern] = []
        self.primitive_heavy_unions: list[ModelUnionPattern] = []
        self.generic_unions: list[ModelUnionPattern] = []

        # Common problematic type combinations
        self.problematic_combinations = {
            frozenset(["str", "int", "bool", "float"]): "primitive_overload",
            # Mixed primitive/complex patterns (with generic annotations)
            frozenset(
                ["str", "int", "bool", "dict[str, Any]"]
            ): "mixed_primitive_complex",
            frozenset(
                ["str", "int", "dict[str, Any]", "list[Any]"]
            ): "mixed_primitive_complex",
            # Mixed primitive/complex patterns (without generic annotations)
            frozenset(["str", "int", "bool", "dict"]): "mixed_primitive_complex",
            frozenset(["str", "int", "bool", "Dict"]): "mixed_primitive_complex",
            frozenset(["str", "int", "dict", "list"]): "mixed_primitive_complex",
            frozenset(["str", "int", "Dict", "List"]): "mixed_primitive_complex",
            # Everything union patterns (with generic annotations)
            frozenset(
                ["str", "int", "bool", "float", "dict[str, Any]"]
            ): "everything_union",
            frozenset(["str", "int", "bool", "float", "list[Any]"]): "everything_union",
            # Everything union patterns (without generic annotations)
            frozenset(["str", "int", "bool", "float", "dict"]): "everything_union",
            frozenset(["str", "int", "bool", "float", "list"]): "everything_union",
            frozenset(["str", "int", "bool", "float", "Dict"]): "everything_union",
            frozenset(["str", "int", "bool", "float", "List"]): "everything_union",
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

        # Check for Union[T, None] which should use Optional[T]
        if "None" in union_pattern.types and union_pattern.type_count == 2:
            non_none_types = [t for t in union_pattern.types if t != "None"]
            self.issues.append(
                f"Line {union_pattern.line}: Use Optional[{non_none_types[0]}] "
                f"instead of {union_pattern.get_signature()}"
            )

        # Check for complex unions (configurable complexity threshold)
        if union_pattern.type_count >= 3:
            self.complex_unions.append(union_pattern)

            # Check for specific problematic combinations
            for problem_set, problem_type in self.problematic_combinations.items():
                if problem_set.issubset(types_set):
                    if problem_type == "primitive_overload":
                        self.issues.append(
                            f"Line {union_pattern.line}: Union with 4+ primitive types "
                            f"{union_pattern.get_signature()} should use a specific type, generic TypeVar, or strongly-typed model"
                        )
                    elif problem_type == "mixed_primitive_complex":
                        self.issues.append(
                            f"Line {union_pattern.line}: Mixed primitive/complex Union "
                            f"{union_pattern.get_signature()} should use a specific type, generic TypeVar, or strongly-typed model"
                        )
                    elif problem_type == "everything_union":
                        self.issues.append(
                            f"Line {union_pattern.line}: Overly broad Union "
                            f"{union_pattern.get_signature()} should use a specific type, generic TypeVar, or proper domain model"
                        )

        # Check for redundant None patterns
        if "None" in union_pattern.types and union_pattern.type_count > 2:
            non_none_types = [t for t in union_pattern.types if t != "None"]
            if len(non_none_types) == 1:
                self.issues.append(
                    f"Line {union_pattern.line}: Use Optional[{non_none_types[0]}] "
                    f"instead of {union_pattern.get_signature()}"
                )

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Visit subscript nodes (e.g., Union[str, int])."""
        if isinstance(node.value, ast.Name) and node.value.id == "Union":
            self._process_union_types(node, node.slice, node.lineno)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Visit binary operation nodes (e.g., str | int | float)."""
        if isinstance(node.op, ast.BitOr):
            # Skip if we're already inside a union BinOp chain
            # This prevents double-counting nested unions like (str | int) | bool
            if self._in_union_binop:
                return

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

            # Mark that we're inside a union BinOp chain and visit children
            # This ensures we still visit Subscript nodes and other structures
            # but skip nested BinOp unions that are part of the same chain
            self._in_union_binop = True
            self.generic_visit(node)
            self._in_union_binop = False
            return

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
        self, node: ast.AST, slice_node: ast.AST, line_no: int
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
                f"Line {line_no}: Use Optional[T] or T | None instead of T | None"
            )
