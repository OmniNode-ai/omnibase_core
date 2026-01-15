"""UnionUsageChecker - AST-based checker for Union type usage patterns.

This module provides the UnionUsageChecker class for analyzing Python source
code to detect Union type usage patterns that may indicate poor type design.

The checker visits AST nodes to find both Union[...] syntax and modern | syntax
unions, analyzes them for problematic patterns, and reports issues.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.models.validation.model_union_pattern

Example:
    >>> import ast
    >>> code = "x: str | int | bool | float"
    >>> tree = ast.parse(code)
    >>> checker = UnionUsageChecker("example.py")
    >>> checker.visit(tree)
    >>> print(checker.issues)  # Reports primitive overload
"""

import ast
import logging

from omnibase_core.models.validation.model_union_pattern import ModelUnionPattern

# Configure logger for this module
logger = logging.getLogger(__name__)


class UnionUsageChecker(ast.NodeVisitor):
    """AST visitor that checks Union type usage patterns for issues.

    This class walks a Python AST to find all Union type definitions (both
    Union[...] syntax and modern | syntax) and reports problematic patterns
    such as primitive overload, mixed primitive/complex types, and overly
    broad unions.

    Attributes:
        union_count: Total number of unions found.
        issues: List of validation issue strings.
        file_path: Path to the file being analyzed.
        union_patterns: List of all ModelUnionPattern instances found.
        complex_unions: Unions with 3+ types.
        primitive_heavy_unions: Unions with many primitive types.
        generic_unions: Unions with generic type patterns.
        problematic_combinations: Dict mapping type sets to problem types.

    Example:
        >>> import ast
        >>> code = "def f(x: str | int | bool | float): pass"
        >>> tree = ast.parse(code)
        >>> checker = UnionUsageChecker("test.py")
        >>> checker.visit(tree)
        >>> len(checker.issues) > 0
        True
    """

    # Common problematic type combinations (class-level for performance)
    # These frozensets are immutable and thread-safe
    _PROBLEMATIC_COMBINATIONS: dict[frozenset[str], str] = {
        frozenset(["str", "int", "bool", "float"]): "primitive_overload",
        # Mixed primitive/complex patterns (with generic annotations)
        frozenset(["str", "int", "bool", "dict[str, Any]"]): "mixed_primitive_complex",
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

    def __init__(self, file_path: str) -> None:
        """Initialize the UnionUsageChecker.

        Args:
            file_path: Path to the file being analyzed, used for error messages.
        """
        self.union_count = 0
        self.issues: list[str] = []
        self.file_path = file_path
        self.union_patterns: list[ModelUnionPattern] = []
        self._in_union_binop = False  # Track if we're inside a union BinOp chain

        # Track problematic patterns
        self.complex_unions: list[ModelUnionPattern] = []
        self.primitive_heavy_unions: list[ModelUnionPattern] = []
        self.generic_unions: list[ModelUnionPattern] = []

        # Reference class-level combinations for instance access
        self.problematic_combinations = self._PROBLEMATIC_COMBINATIONS

    def _extract_type_name(self, node: ast.AST) -> str:
        """Extract type name from an AST node.

        Handles various AST node types to extract the string representation
        of a type annotation.

        Args:
            node: AST node representing a type annotation.

        Returns:
            String representation of the type name, or "Unknown" for
            unrecognized node types.
        """
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
        """Analyze a union pattern for potential issues.

        Checks for problematic patterns such as:
        - Primitive overload (4+ primitive types)
        - Mixed primitive/complex types
        - Overly broad "everything" unions

        Note:
            Per ONEX conventions, `T | None` is the PREFERRED syntax for nullable
            types and is NOT flagged as a violation. The validator only flags
            actually problematic patterns like primitive overload.

        Args:
            union_pattern: The ModelUnionPattern to analyze.

        Side Effects:
            Appends issues to self.issues for any problems found.
            Categorizes pattern into self.complex_unions if applicable.
        """
        types_set = frozenset(union_pattern.types)

        # NOTE: Per ONEX conventions, T | None is the PREFERRED pattern for nullable types.
        # We do NOT flag simple nullable unions (T | None) as violations.
        # Only complex unions with 3+ types are checked for problematic patterns.

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

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Visit subscript nodes to detect Union[...] and Optional[...] type definitions.

        Called by the AST visitor for each subscript node. Checks if the
        subscript is a Union or Optional type and processes it.

        Args:
            node: AST Subscript node to visit.
        """
        if isinstance(node.value, ast.Name):
            if node.value.id == "Union":
                self._process_union_types(node, node.slice, node.lineno)
            elif node.value.id == "Optional":
                self._process_optional_type(node, node.slice, node.lineno)
        self.generic_visit(node)

    def _process_optional_type(
        self, _node: ast.AST, slice_node: ast.AST, line_no: int
    ) -> None:
        """Process Optional[T] syntax and flag for PEP 604 conversion.

        Detects Optional[T] syntax and reports it as an issue,
        suggesting T | None as the preferred ONEX pattern per PEP 604.

        Args:
            _node: The AST node for the Optional subscript (unused but kept for signature).
            slice_node: The AST node for the subscript slice (the type argument).
            line_no: Line number where the Optional is defined.
        """
        # Extract the inner type from Optional[T]
        inner_type = self._extract_type_name(slice_node)

        # Create a synthetic union pattern for tracking
        union_types = [inner_type, "None"]
        self.union_count += 1

        union_pattern = ModelUnionPattern(union_types, line_no, self.file_path)
        self.union_patterns.append(union_pattern)

        # Analyze the pattern for consistency with other union handling
        self._analyze_union_pattern(union_pattern)

        # Flag Optional[T] - use T | None instead per PEP 604 (ONEX standard)
        self.issues.append(
            f"Line {line_no}: Use {inner_type} | None instead of Optional[{inner_type}] (PEP 604)"
        )

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Visit binary operation nodes to detect modern union syntax (A | B).

        Called by the AST visitor for each binary operation node. Checks if
        the operation is a BitOr (|) that represents a type union.

        Args:
            node: AST BinOp node to visit.

        Note:
            Uses _in_union_binop flag to prevent double-counting nested unions
            like (str | int) | bool.
        """
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
        """Extract union types from modern union syntax (A | B | C).

        Recursively traverses nested BitOr operations to collect all type
        names in a union chain.

        Args:
            node: AST BinOp node representing a union expression.

        Returns:
            List of type name strings found in the union.
        """
        types: list[str] = []

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
        """Process union types from Union[...] syntax.

        Extracts type names from the Union subscript, creates a ModelUnionPattern,
        and analyzes it for issues.

        Args:
            node: The AST node for the Union subscript (unused but kept for signature).
            slice_node: The AST node for the subscript slice (type arguments).
            line_no: Line number where the union is defined.
        """
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

        # Analyze the pattern (delegates to _analyze_union_pattern which checks for soup unions)
        self._analyze_union_pattern(union_pattern)

        # For Union[T, None] syntax, suggest T | None as the preferred ONEX pattern
        if len(union_types) == 2 and "None" in union_types:
            non_none_types = [t for t in union_types if t != "None"]
            # Defensive validation: ensure exactly 1 non-None type exists
            # Edge case: malformed union like Union[None, None] would have empty list
            if len(non_none_types) == 1:
                self.issues.append(
                    f"Line {line_no}: Use {non_none_types[0]} | None instead of Union[{non_none_types[0]}, None]"
                )
            elif len(non_none_types) == 0:
                # Malformed: Union[None, None] - both types are None
                logger.warning(
                    "Line %d: Malformed Union with duplicate None types in %s",
                    line_no,
                    self.file_path,
                )
            else:
                # Unexpected: more than 1 non-None type after filtering 2-element union
                # This shouldn't happen unless union_types has duplicates
                logger.warning(
                    "Line %d: Unexpected Union structure with %d non-None types in %s",
                    line_no,
                    len(non_none_types),
                    self.file_path,
                )
