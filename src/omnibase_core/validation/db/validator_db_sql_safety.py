# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""SQL safety validation for DB repository contracts.

Validates read/write mode consistency, forbids DDL statements, and
requires safety policy opt-in for DELETE/UPDATE without WHERE.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.validation.db.sql_utils import normalize_sql, strip_sql_strings

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )

# Dangerous DDL keywords - forbidden in all repository operations
_DDL_KEYWORDS = re.compile(
    r"\b(DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

# SQL statement type detection patterns
_SELECT_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_INSERT_PATTERN = re.compile(r"^\s*INSERT\b", re.IGNORECASE)
_UPDATE_PATTERN = re.compile(r"^\s*UPDATE\b", re.IGNORECASE)
_DELETE_PATTERN = re.compile(r"^\s*DELETE\b", re.IGNORECASE)

# WHERE clause detection
_WHERE_PATTERN = re.compile(r"\bWHERE\b", re.IGNORECASE)


def validate_db_sql_safety(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Validate SQL safety requirements of a DB repository contract.

    Validates:
    - Read operations (mode=read) only use SELECT statements
    - Write operations (mode=write) use INSERT/UPDATE/DELETE statements
    - DDL statements (CREATE, DROP, ALTER, TRUNCATE, GRANT, REVOKE) are forbidden
    - DELETE without WHERE requires safety_policy.allow_delete_without_where=True
    - UPDATE without WHERE requires safety_policy.allow_update_without_where=True
    - Multi-statement SQL requires safety_policy.allow_multi_statement=True

    Args:
        contract: The DB repository contract to validate.

    Returns:
        Validation result with any errors found.
    """
    errors: list[str] = []

    for op_name, op in contract.ops.items():
        # Normalize SQL by stripping comments and collapsing whitespace
        normalized_sql = normalize_sql(op.sql)

        # Strip string literals to avoid false positives on keywords inside strings
        sql_without_strings = strip_sql_strings(normalized_sql)

        # Check for forbidden DDL keywords
        ddl_match = _DDL_KEYWORDS.search(sql_without_strings)
        if ddl_match:
            errors.append(
                f"Operation '{op_name}': Forbidden DDL keyword '{ddl_match.group(1)}' detected. "
                "DDL operations are not allowed in repository contracts."
            )
            # Skip further checks for this operation - DDL is a hard failure
            continue

        # Validate mode vs SQL verb consistency
        if op.mode == "read":
            if not _SELECT_PATTERN.match(normalized_sql):
                errors.append(
                    f"Operation '{op_name}': read mode requires SELECT statement, "
                    "but SQL starts with different keyword."
                )
        else:  # write mode
            is_insert = _INSERT_PATTERN.match(normalized_sql)
            is_update = _UPDATE_PATTERN.match(normalized_sql)
            is_delete = _DELETE_PATTERN.match(normalized_sql)

            if not (is_insert or is_update or is_delete):
                errors.append(
                    f"Operation '{op_name}': write mode requires INSERT, UPDATE, or DELETE statement."
                )

            # Check DELETE without WHERE clause
            if is_delete and not _WHERE_PATTERN.search(sql_without_strings):
                if not op.safety_policy.allow_delete_without_where:
                    errors.append(
                        f"Operation '{op_name}': DELETE without WHERE clause is dangerous. "
                        "Add WHERE clause or set safety_policy.allow_delete_without_where=True."
                    )

            # Check UPDATE without WHERE clause
            if is_update and not _WHERE_PATTERN.search(sql_without_strings):
                if not op.safety_policy.allow_update_without_where:
                    errors.append(
                        f"Operation '{op_name}': UPDATE without WHERE clause is dangerous. "
                        "Add WHERE clause or set safety_policy.allow_update_without_where=True."
                    )

        # Check for multi-statement SQL (semicolons between statements)
        # Strip trailing whitespace and trailing semicolon before checking
        # A single statement ending with ';' is valid (e.g., "SELECT * FROM test;")
        # Only flag if there's a semicolon BETWEEN statements
        sql_for_multi_check = sql_without_strings.rstrip().rstrip(";")
        if ";" in sql_for_multi_check and not op.safety_policy.allow_multi_statement:
            errors.append(
                f"Operation '{op_name}': Multiple statements detected (semicolon found). "
                "Use single statement or set safety_policy.allow_multi_statement=True."
            )

    if errors:
        return ModelValidationResult.create_invalid(
            errors=errors,
            summary=f"SQL safety validation failed with {len(errors)} error(s)",
        )

    return ModelValidationResult.create_valid(
        summary=f"SQL safety validation passed for {len(contract.ops)} operation(s)",
    )


__all__ = ["validate_db_sql_safety"]
