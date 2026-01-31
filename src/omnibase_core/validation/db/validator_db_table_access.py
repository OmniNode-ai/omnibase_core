"""Table access validation for DB repository contracts.

Validates:
- Tables referenced in SQL are subset of declared tables
- Fail-closed on unrecognized SQL patterns (CTEs, subqueries)

Uses regex-based extraction with conservative matching.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )

# Table extraction patterns
# Matches table names with optional schema qualification (e.g., public.users)
_TABLE_IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?"

_TABLE_PATTERNS = [
    # FROM table or FROM schema.table
    re.compile(rf"\bFROM\s+({_TABLE_IDENTIFIER})", re.IGNORECASE),
    # JOIN table (includes LEFT JOIN, RIGHT JOIN, INNER JOIN, etc.)
    re.compile(rf"\bJOIN\s+({_TABLE_IDENTIFIER})", re.IGNORECASE),
    # INTO table (INSERT INTO, MERGE INTO)
    re.compile(rf"\bINTO\s+({_TABLE_IDENTIFIER})", re.IGNORECASE),
    # UPDATE table
    re.compile(rf"\bUPDATE\s+({_TABLE_IDENTIFIER})", re.IGNORECASE),
    # DELETE FROM table
    re.compile(rf"\bDELETE\s+FROM\s+({_TABLE_IDENTIFIER})", re.IGNORECASE),
]

# Patterns that indicate unhandled complexity (fail closed)
_UNSUPPORTED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bWITH\s+\w+\s+AS\s*\(", re.IGNORECASE), "CTE (WITH ... AS)"),
    (re.compile(r"\(\s*SELECT\b", re.IGNORECASE), "subquery"),
]


def validate_db_table_access(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Validate that SQL only accesses declared tables.

    Extracts table references from SQL and verifies they're
    in the contract's tables list. Fails closed on unrecognized
    SQL patterns (CTEs, subqueries).

    Args:
        contract: The DB repository contract to validate.

    Returns:
        Validation result with any table access errors found.
    """
    errors: list[str] = []
    allowed_tables = {t.lower() for t in contract.tables}

    for op_name, op in contract.ops.items():
        normalized_sql = _normalize_sql(op.sql)
        sql_without_strings = _strip_sql_strings(normalized_sql)

        # Check for unsupported patterns (fail closed)
        unsupported_found = False
        for pattern, description in _UNSUPPORTED_PATTERNS:
            if pattern.search(sql_without_strings):
                errors.append(
                    f"Operation '{op_name}': SQL contains {description} which cannot be "
                    "reliably validated. Use simple table references or implement in v2 (OMN-1791)."
                )
                unsupported_found = True
                break  # Only report first unsupported pattern per operation

        if unsupported_found:
            continue

        # Extract referenced tables
        referenced_tables = _extract_tables(sql_without_strings)

        # Check each table against allowed list
        for table in referenced_tables:
            # Extract just table name if schema-qualified
            table_name = table.split(".")[-1].lower()

            if table_name not in allowed_tables:
                errors.append(
                    f"Operation '{op_name}': Table '{table}' is not in allowed tables list. "
                    f"Allowed: {sorted(contract.tables)}"
                )

    if errors:
        return ModelValidationResult.create_invalid(
            errors=errors,
            summary=f"Table access validation failed with {len(errors)} error(s)",
        )

    return ModelValidationResult.create_valid(
        summary="Table access validation passed: all operations use only declared tables",
    )


def _extract_tables(sql: str) -> set[str]:
    """Extract table names from SQL using regex patterns.

    Args:
        sql: Normalized SQL string with string literals removed.

    Returns:
        Set of table names (may include schema.table format).
    """
    tables: set[str] = set()

    for pattern in _TABLE_PATTERNS:
        for match in pattern.finditer(sql):
            tables.add(match.group(1))

    return tables


def _normalize_sql(sql: str) -> str:
    """Normalize SQL by stripping comments and collapsing whitespace.

    Args:
        sql: Raw SQL string.

    Returns:
        Normalized SQL with comments removed and whitespace collapsed.
    """
    # Remove single-line comments
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    # Remove multi-line comments
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # Collapse whitespace
    sql = " ".join(sql.split())
    return sql.strip()


def _strip_sql_strings(sql: str) -> str:
    """Remove string literals from SQL to avoid false positives.

    Handles both single-quoted and double-quoted strings.
    Also handles escaped quotes within strings.

    Args:
        sql: SQL string to process.

    Returns:
        SQL with string literals replaced by empty strings.
    """
    # Handle escaped single quotes ('') within strings
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    # Handle double-quoted identifiers/strings
    sql = re.sub(r'"(?:[^"]|"")*"', '""', sql)
    return sql


__all__ = ["validate_db_table_access"]
