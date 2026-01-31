"""Deterministic ordering validator for DB repository contracts.

Validates:
- Queries returning many=True have ORDER BY clause
- Queries using LIMIT/OFFSET have ORDER BY clause

This prevents non-deterministic result ordering that would
make tests flaky and behavior unpredictable.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )

# Pattern detection for SQL keywords
_SELECT_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_ORDER_BY_PATTERN = re.compile(r"\bORDER\s+BY\b", re.IGNORECASE)
_LIMIT_PATTERN = re.compile(r"\bLIMIT\b", re.IGNORECASE)
_OFFSET_PATTERN = re.compile(r"\bOFFSET\b", re.IGNORECASE)


def validate_db_deterministic(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Validate deterministic ordering for multi-row queries.

    Ensures:
    - many=True queries have ORDER BY
    - LIMIT/OFFSET queries have ORDER BY

    This prevents non-deterministic result ordering that would
    make tests flaky and behavior unpredictable.

    Args:
        contract: The DB repository contract to validate.

    Returns:
        Validation result with any determinism errors found.
    """
    errors: list[str] = []

    for op_name, op in contract.ops.items():
        normalized_sql = _normalize_sql(op.sql)
        sql_without_strings = _strip_sql_strings(normalized_sql)

        # Only check SELECT statements
        if not _SELECT_PATTERN.match(normalized_sql):
            continue

        has_order_by = _ORDER_BY_PATTERN.search(sql_without_strings) is not None
        has_limit = _LIMIT_PATTERN.search(sql_without_strings) is not None
        has_offset = _OFFSET_PATTERN.search(sql_without_strings) is not None

        # Rule 1: many=True requires ORDER BY
        if op.returns.many and not has_order_by:
            errors.append(
                f"Operation '{op_name}': returns.many=True requires ORDER BY clause "
                "for deterministic result ordering. Add ORDER BY with a tie-breaker column."
            )

        # Rule 2: LIMIT/OFFSET requires ORDER BY
        if (has_limit or has_offset) and not has_order_by:
            clause = "LIMIT" if has_limit else "OFFSET"
            errors.append(
                f"Operation '{op_name}': {clause} without ORDER BY produces "
                "non-deterministic results. Add ORDER BY clause to ensure consistent pagination."
            )

    if errors:
        return ModelValidationResult.create_invalid(
            errors=errors,
            summary=f"Determinism validation failed with {len(errors)} error(s)",
        )

    return ModelValidationResult.create_valid(
        summary="Determinism validation passed: all multi-row queries have ORDER BY",
    )


def _normalize_sql(sql: str) -> str:
    """Normalize SQL by stripping comments and collapsing whitespace.

    Args:
        sql: Raw SQL string.

    Returns:
        Normalized SQL with comments removed and whitespace collapsed.
    """
    # Remove single-line comments (-- comment)
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    # Remove multi-line comments (/* comment */)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # Collapse whitespace to single spaces
    sql = " ".join(sql.split())
    return sql.strip()


def _strip_sql_strings(sql: str) -> str:
    """Remove string literals from SQL to avoid false positives.

    Prevents matching keywords inside string literals like:
    'ORDER BY is not a column' or 'LIMIT reached'

    Args:
        sql: Normalized SQL string.

    Returns:
        SQL with string literals removed.
    """
    # Remove single-quoted strings
    sql = re.sub(r"'[^']*'", "", sql)
    # Remove double-quoted strings (identifiers in some dialects)
    sql = re.sub(r'"[^"]*"', "", sql)
    return sql
