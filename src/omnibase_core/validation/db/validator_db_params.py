"""Parameter validation for DB repository contracts.

Validates:
- Only named parameters (:param) are used (no positional $N)
- All SQL placeholders are defined in params
- All defined params are used in SQL
- Handles SQL comments and string literals properly
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )

# Named parameter pattern (:param_name)
_NAMED_PARAM_PATTERN = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")

# Positional parameter pattern ($1, $2, etc.) - these are NOT allowed
_POSITIONAL_PARAM_PATTERN = re.compile(r"\$(\d+)")


def validate_db_params(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Validate parameter declarations in a DB repository contract.

    Ensures:
    - Only named parameters (:param) are used (no positional $N)
    - All SQL placeholders are defined in params
    - All defined params are used in SQL

    Args:
        contract: The DB repository contract to validate.

    Returns:
        Validation result with any parameter errors found.
    """
    errors: list[str] = []

    for op_name, op in contract.ops.items():
        normalized_sql = _normalize_sql(op.sql)
        sql_without_strings = _strip_sql_strings(normalized_sql)

        # Check for forbidden positional parameters
        positional_matches = _POSITIONAL_PARAM_PATTERN.findall(sql_without_strings)
        if positional_matches:
            formatted_positions = ", ".join(f"${p}" for p in positional_matches)
            errors.append(
                f"Operation '{op_name}': Positional parameters ({formatted_positions}) "
                "are not allowed. Use named parameters (:param_name) instead."
            )
            continue  # Skip further checks for this operation

        # Extract named parameters from SQL
        sql_params = set(_NAMED_PARAM_PATTERN.findall(sql_without_strings))

        # Get declared parameter names
        declared_params = set(op.params.keys())

        # Check for undefined parameters (in SQL but not declared)
        undefined_params = sql_params - declared_params
        if undefined_params:
            errors.append(
                f"Operation '{op_name}': Undefined parameters in SQL: "
                f"{sorted(undefined_params)}. Add them to the params definition."
            )

        # Check for unused parameters (declared but not in SQL)
        unused_params = declared_params - sql_params
        if unused_params:
            errors.append(
                f"Operation '{op_name}': Unused parameters declared: "
                f"{sorted(unused_params)}. Remove them or use them in the SQL."
            )

    if errors:
        return ModelValidationResult.create_invalid(
            errors=errors,
            summary=f"Parameter validation failed with {len(errors)} error(s)",
        )

    return ModelValidationResult.create_valid(
        summary="Parameter validation passed: all parameters match SQL placeholders",
    )


def _normalize_sql(sql: str) -> str:
    """Normalize SQL by stripping comments and collapsing whitespace.

    Removes:
    - Single-line comments (-- ...)
    - Multi-line comments (/* ... */)
    - Collapses whitespace

    Args:
        sql: Raw SQL string.

    Returns:
        Normalized SQL with comments removed.
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

    Removes:
    - Single-quoted strings ('...')
    - Double-quoted identifiers ("...")

    This prevents detecting :param patterns inside string literals.

    Args:
        sql: SQL string (ideally normalized first).

    Returns:
        SQL with string literals removed.
    """
    # Remove single-quoted strings
    sql = re.sub(r"'[^']*'", "", sql)
    # Remove double-quoted identifiers
    sql = re.sub(r'"[^"]*"', "", sql)
    return sql


__all__ = ["validate_db_params"]
