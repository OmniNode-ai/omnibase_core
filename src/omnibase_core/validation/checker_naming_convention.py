"""
NamingConventionChecker

Check naming conventions.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

import ast
import re


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
