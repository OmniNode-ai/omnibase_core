"""
AnyTypeVisitor - AST visitor for detecting Any type usage patterns.

This module provides the AnyTypeVisitor class which is an AST visitor that
walks Python source code to find all usages of the Any type, including
imports, annotations, and parameterized generics like dict[str, Any] or
list[Any].

The visitor is used by ValidatorAnyType to detect Any type usage patterns
that may violate ONEX type safety standards.

Usage Example:
    >>> import ast
    >>> from pathlib import Path
    >>> from omnibase_core.validation.checker_visitor_any_type import AnyTypeVisitor
    >>> from omnibase_core.enums import EnumSeverity
    >>>
    >>> source = "from typing import Any\\ndef foo(x: Any) -> Any: pass"
    >>> tree = ast.parse(source)
    >>> visitor = AnyTypeVisitor(
    ...     source_lines=source.splitlines(),
    ...     suppression_patterns=["# noqa:"],
    ...     file_path=Path("example.py"),
    ...     severity=EnumSeverity.ERROR,
    ... )
    >>> visitor.visit(tree)
    >>> print(len(visitor.issues))  # Number of Any type violations found
    2

Thread Safety:
    AnyTypeVisitor instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorAnyType: Main validator that uses this visitor
    - decorator_allow_any_type: Decorator for exempting functions from Any checks
    - decorator_allow_dict_any: Decorator for exempting dict[str, Any] usage
"""

import ast
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue

# Rule IDs for Any type violations
RULE_ANY_IMPORT = "any_import"
RULE_ANY_ANNOTATION = "any_annotation"
RULE_DICT_STR_ANY = "dict_str_any"
RULE_LIST_ANY = "list_any"
RULE_UNION_WITH_ANY = "union_with_any"

# Decorator names that exempt functions from Any type checks
EXEMPT_DECORATORS: frozenset[str] = frozenset(
    {
        "allow_any_type",
        "allow_dict_any",
    }
)


class AnyTypeVisitor(ast.NodeVisitor):
    """AST visitor that detects Any type usage patterns.

    This visitor walks a Python AST to find all usages of the Any type,
    including imports, annotations, and parameterized generics like
    dict[str, Any] or list[Any].

    Attributes:
        issues: List of ModelValidationIssue instances for detected violations.
        source_lines: Source code lines for suppression checking.
        suppression_patterns: Patterns that suppress violations on a line.
        file_path: Path to the file being analyzed.
        severity: Default severity for detected violations.
    """

    def __init__(
        self,
        source_lines: list[str],
        suppression_patterns: list[str],
        file_path: Path,
        severity: EnumSeverity = EnumSeverity.ERROR,
    ) -> None:
        """Initialize the AnyTypeVisitor.

        Args:
            source_lines: List of source code lines for the file.
            suppression_patterns: Comment patterns that suppress violations.
            file_path: Path to the file being analyzed.
            severity: Default severity for violations.
        """
        self.issues: list[ModelValidationIssue] = []
        self.source_lines = source_lines
        self.suppression_patterns = suppression_patterns
        self.file_path = file_path
        self.severity = severity
        self._any_imported = False
        self._current_class_exempted = False
        self._current_function_exempted = False

    def _is_suppressed(self, lineno: int) -> bool:
        """Check if a line has a suppression comment.

        Args:
            lineno: Line number to check (1-indexed).

        Returns:
            True if the line contains a suppression pattern.
        """
        if lineno <= 0 or lineno > len(self.source_lines):
            return False

        line = self.source_lines[lineno - 1]
        for pattern in self.suppression_patterns:
            if pattern in line:
                return True

        return False

    def _is_exempt_decorator(self, decorator: ast.expr) -> bool:
        """Check if a decorator exempts the node from Any checks.

        Handles decorator patterns:
        - @allow_any_type
        - @allow_any_type(reason="...")
        - @allow_dict_any
        - @allow_dict_any(reason="...")

        Args:
            decorator: AST node for the decorator.

        Returns:
            True if this decorator exempts the function/class.
        """
        # Handle @decorator
        if isinstance(decorator, ast.Name):
            return decorator.id in EXEMPT_DECORATORS

        # Handle @decorator() or @decorator(args)
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id in EXEMPT_DECORATORS
            if isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr in EXEMPT_DECORATORS

        # Handle @module.decorator
        if isinstance(decorator, ast.Attribute):
            return decorator.attr in EXEMPT_DECORATORS

        return False

    def _has_exempt_decorator(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
    ) -> bool:
        """Check if a function or class has an exempting decorator.

        Args:
            node: AST node for the function or class.

        Returns:
            True if the node has an exempting decorator.
        """
        for decorator in node.decorator_list:
            if self._is_exempt_decorator(decorator):
                return True
        return False

    def _add_issue(
        self,
        lineno: int,
        rule_code: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        """Add a validation issue if not suppressed.

        Args:
            lineno: Line number of the violation.
            rule_code: Rule code for the violation type.
            message: Human-readable description of the issue.
            suggestion: Optional suggestion for fixing the issue.
        """
        if self._is_suppressed(lineno):
            return

        if self._current_class_exempted or self._current_function_exempted:
            return

        self.issues.append(
            ModelValidationIssue(
                severity=self.severity,
                message=message,
                code=rule_code,
                file_path=self.file_path,
                line_number=lineno,
                rule_name=rule_code,
                suggestion=suggestion,
            )
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit import-from statements to detect 'from typing import Any'.

        Args:
            node: AST ImportFrom node.
        """
        if node.module == "typing":
            for alias in node.names:
                if alias.name == "Any":
                    self._any_imported = True
                    self._add_issue(
                        lineno=node.lineno,
                        rule_code=RULE_ANY_IMPORT,
                        message="Import of 'Any' from typing module",
                        suggestion="Consider using a more specific type or creating a Protocol",
                    )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements to detect 'import typing'.

        Note: We track typing imports but don't flag them. We'll detect
        typing.Any usage in annotations instead.

        Args:
            node: AST Import node.
        """
        # Just visit children
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to check for exempting decorators.

        Args:
            node: AST ClassDef node.
        """
        # Save previous state
        prev_class_exempted = self._current_class_exempted

        # Check for exempt decorators
        self._current_class_exempted = self._has_exempt_decorator(node)

        # Visit all children
        self.generic_visit(node)

        # Restore state
        self._current_class_exempted = prev_class_exempted

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check for exempting decorators and annotations.

        Args:
            node: AST FunctionDef node.
        """
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions.

        Args:
            node: AST AsyncFunctionDef node.
        """
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Common handler for function definitions.

        Args:
            node: AST FunctionDef or AsyncFunctionDef node.
        """
        # Save previous state
        prev_function_exempted = self._current_function_exempted

        # Check for exempt decorators
        self._current_function_exempted = self._has_exempt_decorator(node)

        # Check return annotation
        if node.returns is not None:
            self._check_annotation(node.returns, node.lineno, "return type")

        # Check argument annotations
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.annotation is not None:
                self._check_annotation(
                    arg.annotation, arg.lineno, f"parameter '{arg.arg}'"
                )

        if node.args.vararg and node.args.vararg.annotation:
            self._check_annotation(
                node.args.vararg.annotation,
                node.args.vararg.lineno,
                f"*{node.args.vararg.arg}",
            )

        if node.args.kwarg and node.args.kwarg.annotation:
            self._check_annotation(
                node.args.kwarg.annotation,
                node.args.kwarg.lineno,
                f"**{node.args.kwarg.arg}",
            )

        # Visit all children
        self.generic_visit(node)

        # Restore state
        self._current_function_exempted = prev_function_exempted

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments to check type annotations.

        Args:
            node: AST AnnAssign node.
        """
        if node.target is not None and isinstance(node.target, ast.Name):
            context = f"variable '{node.target.id}'"
        else:
            context = "variable"

        self._check_annotation(node.annotation, node.lineno, context)
        self.generic_visit(node)

    def _check_annotation(
        self, annotation: ast.expr, lineno: int, context: str
    ) -> None:
        """Check a type annotation for Any usage.

        Args:
            annotation: AST node for the annotation.
            lineno: Line number of the annotation.
            context: Description of where the annotation appears.
        """
        # Check for bare 'Any'
        if isinstance(annotation, ast.Name) and annotation.id == "Any":
            self._add_issue(
                lineno=annotation.lineno,
                rule_code=RULE_ANY_ANNOTATION,
                message=f"Use of 'Any' type in {context}",
                suggestion="Consider using a more specific type, TypeVar, or Protocol",
            )
            return

        # Check for typing.Any
        if isinstance(annotation, ast.Attribute):
            if annotation.attr == "Any" and isinstance(annotation.value, ast.Name):
                if annotation.value.id == "typing":
                    self._add_issue(
                        lineno=annotation.lineno,
                        rule_code=RULE_ANY_ANNOTATION,
                        message=f"Use of 'typing.Any' in {context}",
                        suggestion="Consider using a more specific type, TypeVar, or Protocol",
                    )
            return

        # Check for subscript types like dict[str, Any], list[Any]
        if isinstance(annotation, ast.Subscript):
            self._check_subscript_annotation(annotation, lineno, context)
            return

        # Check for Union with Any (using | syntax)
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            self._check_union_binop(annotation, lineno, context)
            return

    def _check_subscript_annotation(
        self,
        node: ast.Subscript,
        lineno: int,
        context: str,
    ) -> None:
        """Check subscript annotations like dict[str, Any] or list[Any].

        Args:
            node: AST Subscript node.
            lineno: Line number.
            context: Description of where the annotation appears.
        """
        # Get the base type name
        base_name = self._get_type_name(node.value)

        # Check for dict[str, Any]
        if base_name in ("dict", "Dict", "typing.Dict"):
            if isinstance(node.slice, ast.Tuple) and len(node.slice.elts) == 2:
                value_type = node.slice.elts[1]
                if self._is_any_type(value_type):
                    self._add_issue(
                        lineno=node.lineno,
                        rule_code=RULE_DICT_STR_ANY,
                        message=f"Use of 'dict[str, Any]' in {context}",
                        suggestion="Consider using a TypedDict or Pydantic model",
                    )
                    return

        # Check for list[Any]
        if base_name in ("list", "List", "typing.List"):
            if self._is_any_type(node.slice):
                self._add_issue(
                    lineno=node.lineno,
                    rule_code=RULE_LIST_ANY,
                    message=f"Use of 'list[Any]' in {context}",
                    suggestion="Consider using a more specific element type",
                )
                return

        # Check for Union[..., Any]
        if base_name in ("Union", "typing.Union"):
            if isinstance(node.slice, ast.Tuple):
                for elt in node.slice.elts:
                    if self._is_any_type(elt):
                        self._add_issue(
                            lineno=node.lineno,
                            rule_code=RULE_UNION_WITH_ANY,
                            message=f"Use of 'Union[..., Any]' in {context}",
                            suggestion="Consider using a more specific type",
                        )
                        return
            elif self._is_any_type(node.slice):
                self._add_issue(
                    lineno=node.lineno,
                    rule_code=RULE_UNION_WITH_ANY,
                    message=f"Use of 'Union[Any]' in {context}",
                    suggestion="Consider using a more specific type",
                )
                return

        # Check for Optional[Any] (equivalent to Union[Any, None])
        if base_name in ("Optional", "typing.Optional"):
            if self._is_any_type(node.slice):
                self._add_issue(
                    lineno=node.lineno,
                    rule_code=RULE_UNION_WITH_ANY,
                    message=f"Use of 'Optional[Any]' in {context}",
                    suggestion="Consider using a more specific type or 'T | None'",
                )
                return

        # Recursively check nested subscripts
        if isinstance(node.slice, ast.Tuple):
            for elt in node.slice.elts:
                self._check_annotation(elt, lineno, context)
        else:
            self._check_annotation(node.slice, lineno, context)

    def _check_union_binop(
        self,
        node: ast.BinOp,
        lineno: int,
        context: str,
    ) -> None:
        """Check union expressions using | syntax for Any.

        Args:
            node: AST BinOp node with BitOr operator.
            lineno: Line number.
            context: Description of where the annotation appears.
        """
        # Collect all types in the union chain
        types_in_union = self._collect_union_types(node)

        for type_node in types_in_union:
            if self._is_any_type(type_node):
                self._add_issue(
                    lineno=node.lineno,
                    rule_code=RULE_UNION_WITH_ANY,
                    message=f"Use of 'Any' in union type in {context}",
                    suggestion="Consider using a more specific type",
                )
                return

        # Also recursively check nested types
        for type_node in types_in_union:
            if isinstance(type_node, ast.Subscript):
                self._check_subscript_annotation(type_node, lineno, context)

    def _collect_union_types(self, node: ast.expr) -> list[ast.expr]:
        """Collect all types from a union expression.

        Args:
            node: AST expression node.

        Returns:
            List of type expression nodes in the union.
        """
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self._collect_union_types(node.left)
            right = self._collect_union_types(node.right)
            return left + right
        return [node]

    def _is_any_type(self, node: ast.expr) -> bool:
        """Check if a node represents the Any type.

        Args:
            node: AST expression node.

        Returns:
            True if the node is Any or typing.Any.
        """
        if isinstance(node, ast.Name) and node.id == "Any":
            return True

        if isinstance(node, ast.Attribute):
            if node.attr == "Any" and isinstance(node.value, ast.Name):
                return node.value.id == "typing"

        return False

    def _get_type_name(self, node: ast.expr) -> str:
        """Get the name of a type from an AST node.

        Args:
            node: AST expression node.

        Returns:
            String name of the type.
        """
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            base = self._get_type_name(node.value)
            return f"{base}.{node.attr}"

        return ""


__all__ = [
    "AnyTypeVisitor",
    "EXEMPT_DECORATORS",
    "RULE_ANY_ANNOTATION",
    "RULE_ANY_IMPORT",
    "RULE_DICT_STR_ANY",
    "RULE_LIST_ANY",
    "RULE_UNION_WITH_ANY",
]
