# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Field projection validation for DB repository contracts.

Validates that SQL SELECT projections match declared fields when
strict mode is enabled (default when fields are declared).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.validation.db.sql_utils import extract_select_columns

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )


def validate_db_projection(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Validate SQL projections match declared fields.

    Validation Rules:
    - If `fields` is absent: skip validation (unless strict=True explicitly)
    - If `fields` is present: strict mode is enabled by default
    - SELECT * or table.* in strict mode: ERROR (unless allow_select_star=True -> WARN)
    - Complex expressions (functions, CASE) in strict mode: ERROR
    - Field mismatch in strict mode: ERROR
    - In lenient mode: issues become WARNINGs instead of ERRORs
    """
    # Create result early to use add_warning/add_error API consistently
    result: ModelValidationResult[None] = ModelValidationResult.create_valid(
        summary=f"Projection validation passed for {len(contract.ops)} operation(s)",
    )
    error_count = 0

    for op_name, op in contract.ops.items():
        returns = op.returns

        # Determine effective strict mode
        # Default: strict=True if fields is present and non-empty
        if returns.strict is None:
            is_strict = returns.fields is not None and len(returns.fields) > 0
        else:
            is_strict = returns.strict

        # Skip if no fields declared and not explicitly strict
        if returns.fields is None:
            if returns.strict is True:
                result.add_warning(
                    f"Operation '{op_name}': strict=True but no fields declared. "
                    "Strict validation requires fields to be specified."
                )
            continue

        declared_fields = {f.lower() for f in returns.fields}

        # Only check read operations (SELECT statements)
        if op.mode != "read":
            continue

        # Extract columns from SQL (normalize_sql is called internally)
        sql_columns, is_complex = extract_select_columns(op.sql)

        # Check for SELECT * or table.*
        if "*" in sql_columns:
            if returns.allow_select_star:
                result.add_warning(
                    f"Operation '{op_name}': SELECT * used with allow_select_star=True. "
                    "This bypasses field projection validation and may cause schema drift."
                )
                continue
            if is_strict:
                result.add_error(
                    f"Operation '{op_name}': SELECT * is not allowed in strict mode. "
                    "Either enumerate fields explicitly or set allow_select_star=True."
                )
                error_count += 1
                continue
            result.add_warning(
                f"Operation '{op_name}': SELECT * detected. "
                "Consider enumerating fields explicitly for deterministic projections."
            )
            continue

        # Check for complex expressions
        if is_complex:
            if is_strict:
                result.add_error(
                    f"Operation '{op_name}': SQL projection contains complex expressions "
                    "(functions, CASE, subqueries) that cannot be reliably parsed. "
                    "Simplify projection or set strict=False for lenient validation."
                )
                error_count += 1
            else:
                result.add_warning(
                    f"Operation '{op_name}': SQL projection contains complex expressions. "
                    "Field validation skipped."
                )
            continue

        # Compare projected columns with declared fields (case-insensitive)
        # SQL column names are case-insensitive, so lowercase both sides
        projected_fields = {c.lower() for c in sql_columns}

        missing_in_sql = declared_fields - projected_fields
        extra_in_sql = projected_fields - declared_fields

        if missing_in_sql or extra_in_sql:
            msg_parts = [f"Operation '{op_name}': Projection mismatch."]
            if missing_in_sql:
                msg_parts.append(f"Declared but not in SQL: {sorted(missing_in_sql)}")
            if extra_in_sql:
                msg_parts.append(f"In SQL but not declared: {sorted(extra_in_sql)}")

            full_msg = " ".join(msg_parts)

            if is_strict:
                result.add_error(full_msg)
                error_count += 1
            else:
                result.add_warning(full_msg)

    # Update summary if errors were found
    if error_count > 0:
        result.summary = f"Projection validation failed with {error_count} error(s)"

    return result


__all__ = ["validate_db_projection"]
