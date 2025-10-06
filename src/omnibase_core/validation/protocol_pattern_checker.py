"""
PatternChecker Protocol

Protocol for pattern checker classes.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

import ast
from typing import Protocol


class PatternChecker(Protocol):
    """Protocol for pattern checker classes."""

    issues: list[str]

    def visit(self, node: ast.AST) -> None: ...
