# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""SQL parser adapter for table extraction.

Provides AST-based table extraction using sqlglot when available.
Falls back gracefully when parser is unavailable or fails.

This module isolates all sqlglot interactions to prevent dependency
leakage into the rest of the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

# Lazy-loaded sqlglot module reference
_sqlglot: Any | None = None
_HAS_PARSER: bool | None = None


def _ensure_parser_loaded() -> bool:
    """Lazy-load sqlglot and cache availability.

    Returns:
        True if sqlglot is available, False otherwise.
    """
    global _sqlglot, _HAS_PARSER
    if _HAS_PARSER is None:
        try:
            import sqlglot

            _sqlglot = sqlglot
            _HAS_PARSER = True
        except ImportError:
            _HAS_PARSER = False
    return _HAS_PARSER


@dataclass(frozen=True)
class ParserResult:
    """Result of parser-based table extraction.

    Attributes:
        tables: Extracted table names (may include schema.table format).
        cte_names: CTE alias names that should be filtered out.
        success: Whether parsing succeeded.
        error: Error message if parsing failed.
    """

    tables: frozenset[str]
    cte_names: frozenset[str]
    success: bool
    error: str | None = None

    @classmethod
    def failure(cls, error: str) -> ParserResult:
        """Create a failed result with error message."""
        return cls(
            tables=frozenset(),
            cte_names=frozenset(),
            success=False,
            error=error,
        )

    @classmethod
    def ok(cls, tables: frozenset[str], cte_names: frozenset[str]) -> ParserResult:
        """Create a successful result with extracted tables."""
        return cls(
            tables=tables,
            cte_names=cte_names,
            success=True,
            error=None,
        )


def has_parser() -> bool:
    """Check if SQL parser is available.

    Returns:
        True if sqlglot is installed and importable.
    """
    return _ensure_parser_loaded()


def extract_tables_with_parser(
    sql: str,
    max_depth: int = 10,
) -> ParserResult | None:
    """Extract tables using AST-based parsing.

    Args:
        sql: SQL string to parse.
        max_depth: Maximum nesting depth to traverse (safety limit).

    Returns:
        ParserResult if parser available, None if parser unavailable.
        ParserResult.success=False indicates parse failure (caller should fail closed).
    """
    if not _ensure_parser_loaded():
        return None

    assert _sqlglot is not None  # For type checker
    # Capture in local variable for nested function access
    sqlglot_module = _sqlglot

    try:
        # Parse SQL into AST
        # Use dialect=None for generic SQL parsing
        ast = sqlglot_module.parse_one(sql)

        # Extract all table references
        tables: set[str] = set()
        cte_names: set[str] = set()

        # First pass: collect CTE names
        for cte in ast.find_all(sqlglot_module.exp.CTE):
            alias = cte.alias
            if alias:
                cte_names.add(alias)

        # Second pass: collect table references with depth limit
        depth_exceeded = False

        def collect_tables(node: Any, current_depth: int = 0) -> None:
            nonlocal depth_exceeded

            if current_depth > max_depth:
                depth_exceeded = True
                return

            # Check if this node is a Table reference
            if isinstance(node, sqlglot_module.exp.Table):
                table_name = _format_table_name(node)
                if table_name:
                    tables.add(table_name)

            # Recursively process children
            for child in node.iter_expressions():
                collect_tables(child, current_depth + 1)

        collect_tables(ast)

        if depth_exceeded:
            return ParserResult.failure(
                f"SQL nesting depth exceeds maximum of {max_depth}"
            )

        return ParserResult.ok(
            tables=frozenset(tables),
            cte_names=frozenset(cte_names),
        )

    except sqlglot_module.errors.ParseError as e:
        return ParserResult.failure(f"Parse error: {e}")
    except (
        Exception
    ) as e:  # fallback-ok: fail-closed security - return failure to reject SQL
        return ParserResult.failure(f"Unexpected parser error: {e}")


def _format_table_name(table_node: Any) -> str | None:
    """Format a sqlglot Table node into a table name string.

    Handles both simple tables (e.g., "users") and schema-qualified
    tables (e.g., "public.users").

    Args:
        table_node: A sqlglot Table expression node.

    Returns:
        Formatted table name, or None if the node has no name.
    """
    if not _sqlglot:
        return None

    # Get the table name
    name = cast(str, table_node.name)
    if not name:
        return None

    # Check for schema qualification
    db = table_node.db  # In sqlglot, 'db' is the schema for Table nodes
    if db:
        return f"{db}.{name}"

    return name


__all__ = [
    "ParserResult",
    "extract_tables_with_parser",
    "has_parser",
]
