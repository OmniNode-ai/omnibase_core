"""
GenericPatternChecker

Check for generic anti-patterns.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

import ast


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
        # Exempt __init__ methods - they commonly need many parameters for DI
        if len(node.args.args) > 5 and func_name != "__init__":
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
