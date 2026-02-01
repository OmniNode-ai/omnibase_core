"""Table access validation for DB repository contracts.

Validates SQL only references declared tables. Fails closed on
unrecognized patterns (CTEs, subqueries) for safety.

Table Matching Rules:
- Simple allowed table (e.g., "users"): Matches "users", "public.users", "schema.users"
- Schema-qualified allowed table (e.g., "public.users"): Only matches exact "public.users"

Quoted Identifier Handling:
- SQL quoted identifiers like `"TableName"` are valid table references
- Extracted before string stripping to prevent evasion
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.validation.db.sql_utils import normalize_sql, strip_sql_strings

# Pattern to match single-quoted strings (for stripping)
# Handles backslash escapes and doubled single quotes
_SINGLE_QUOTED_STRING = re.compile(r"'(?:[^'\\]|\\.|'')*'")

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )

# Table extraction patterns
# Matches table names with optional schema qualification (e.g., public.users)
_TABLE_IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?"

# Quoted identifier pattern (e.g., "TableName" or "schema"."table")
_QUOTED_IDENTIFIER = r'"[^"]+"(?:\."[^"]+")?'

_TABLE_PATTERNS = [
    # FROM table or FROM schema.table (unquoted)
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

# Patterns for quoted identifiers (must be extracted before strip_sql_strings)
_QUOTED_TABLE_PATTERNS = [
    # FROM "table" or FROM "schema"."table"
    re.compile(rf"\bFROM\s+({_QUOTED_IDENTIFIER})", re.IGNORECASE),
    # JOIN "table"
    re.compile(rf"\bJOIN\s+({_QUOTED_IDENTIFIER})", re.IGNORECASE),
    # INTO "table"
    re.compile(rf"\bINTO\s+({_QUOTED_IDENTIFIER})", re.IGNORECASE),
    # UPDATE "table"
    re.compile(rf"\bUPDATE\s+({_QUOTED_IDENTIFIER})", re.IGNORECASE),
    # DELETE FROM "table"
    re.compile(rf"\bDELETE\s+FROM\s+({_QUOTED_IDENTIFIER})", re.IGNORECASE),
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

    Table matching rules:
    - Simple allowed table (e.g., "users"): Matches "users", "public.users", "schema.users"
    - Schema-qualified allowed table (e.g., "public.users"): Only matches exact "public.users"

    Args:
        contract: The DB repository contract to validate.

    Returns:
        Validation result with any table access errors found.
    """
    errors: list[str] = []

    # Build two sets for different matching strategies
    # Schema-qualified tables require exact match, simple tables match any schema prefix
    allowed_exact: set[str] = set()  # Schema-qualified (e.g., "public.users")
    allowed_simple: set[str] = set()  # Simple names (e.g., "users")

    for table in contract.tables:
        table_lower = table.lower()
        if "." in table:
            allowed_exact.add(table_lower)
        else:
            allowed_simple.add(table_lower)

    for op_name, op in contract.ops.items():
        normalized_sql = normalize_sql(op.sql)

        # Strip all strings (single and double quoted) for unsupported pattern checks
        sql_without_all_strings = strip_sql_strings(normalized_sql)

        # Check for unsupported patterns (fail closed)
        unsupported_found = False
        for pattern, description in _UNSUPPORTED_PATTERNS:
            if pattern.search(sql_without_all_strings):
                errors.append(
                    f"Operation '{op_name}': SQL contains {description} which cannot be "
                    "reliably validated. Use simple table references or implement in v2 (OMN-1791)."
                )
                unsupported_found = True
                break  # Only report first unsupported pattern per operation

        if unsupported_found:
            continue

        # Extract quoted identifiers from normalized SQL (before any stripping)
        quoted_tables = _extract_quoted_tables(normalized_sql)

        # Strip only single-quoted strings for unquoted table extraction
        # This preserves double-quoted identifiers so aliases after them
        # aren't mistakenly matched as table names
        sql_without_string_literals = _strip_single_quoted_strings(normalized_sql)

        # Extract unquoted table references
        unquoted_tables = _extract_tables(sql_without_string_literals)

        # Combine all referenced tables
        referenced_tables = unquoted_tables | quoted_tables

        # Check each table against allowed list
        for table in referenced_tables:
            if not _is_table_allowed(table, allowed_exact, allowed_simple):
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


def _strip_single_quoted_strings(sql: str) -> str:
    """Strip only single-quoted string literals from SQL.

    Unlike strip_sql_strings(), this preserves double-quoted identifiers
    so they can be matched by the quoted table patterns and don't leave
    behind aliases that could be mistaken for table names.

    Args:
        sql: SQL string to process.

    Returns:
        SQL with single-quoted strings removed.
    """
    return _SINGLE_QUOTED_STRING.sub("", sql)


def _extract_tables(sql: str) -> set[str]:
    """Extract unquoted table names from SQL using regex patterns.

    Args:
        sql: Normalized SQL string with single-quoted strings removed.
              Double-quoted identifiers should still be present.

    Returns:
        Set of table names (may include schema.table format).
    """
    tables: set[str] = set()

    for pattern in _TABLE_PATTERNS:
        for match in pattern.finditer(sql):
            tables.add(match.group(1))

    return tables


def _extract_quoted_tables(sql: str) -> set[str]:
    """Extract quoted identifier table names from SQL.

    Must be called BEFORE strip_sql_strings() to capture quoted tables
    that would otherwise be stripped (preventing evasion attacks).

    Args:
        sql: Normalized SQL string (with string literals still present).

    Returns:
        Set of table names extracted from quoted identifiers.
        Quotes are stripped from the returned names.
    """
    tables: set[str] = set()

    for pattern in _QUOTED_TABLE_PATTERNS:
        for match in pattern.finditer(sql):
            quoted_name = match.group(1)
            # Strip surrounding quotes and handle schema.table format
            # e.g., "schema"."table" -> schema.table
            # e.g., "TableName" -> TableName
            table_name = _unquote_identifier(quoted_name)
            tables.add(table_name)

    return tables


def _unquote_identifier(quoted: str) -> str:
    """Remove double quotes from a SQL identifier.

    Handles both simple identifiers ("table") and schema-qualified
    identifiers ("schema"."table").

    Args:
        quoted: A quoted identifier like '"TableName"' or '"schema"."table"'.

    Returns:
        The unquoted identifier (e.g., 'TableName' or 'schema.table').
    """
    # Split on "." to handle "schema"."table" case
    parts = quoted.split('"."')
    if len(parts) == 2:
        # Schema-qualified: "schema"."table"
        schema = parts[0].strip('"')
        table = parts[1].strip('"')
        return f"{schema}.{table}"
    else:
        # Simple: "table"
        return quoted.strip('"')


def _is_table_allowed(
    table: str,
    allowed_exact: set[str],
    allowed_simple: set[str],
) -> bool:
    """Check if a table reference is in the allowed list.

    Matching rules:
    - If the referenced table is schema-qualified (e.g., "public.users"):
      1. Check for exact match in allowed_exact (schema-qualified allowlist)
      2. Check if table part matches any simple allowlist entry
    - If the referenced table is simple (e.g., "users"):
      1. Check for exact match in allowed_simple
      2. Check for exact match in allowed_exact (in case "users" is declared as "public.users")

    Args:
        table: The table reference from SQL (may be schema-qualified).
        allowed_exact: Set of schema-qualified allowed tables (lowercase).
        allowed_simple: Set of simple allowed table names (lowercase).

    Returns:
        True if the table is allowed, False otherwise.
    """
    table_lower = table.lower()

    if "." in table:
        # Schema-qualified reference (e.g., "public.users")
        # Check 1: Exact match against schema-qualified allowlist
        if table_lower in allowed_exact:
            return True
        # Check 2: Table part matches simple allowlist
        table_part = table_lower.split(".")[-1]
        if table_part in allowed_simple:
            return True
        return False
    else:
        # Simple reference (e.g., "users")
        # Check 1: Direct match in simple allowlist
        if table_lower in allowed_simple:
            return True
        # Check 2: Match against exact allowlist (unlikely but consistent)
        if table_lower in allowed_exact:
            return True
        return False


__all__ = ["validate_db_table_access"]
