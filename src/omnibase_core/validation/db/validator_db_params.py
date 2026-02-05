"""Parameter validation for DB repository contracts.

Validates named params (:param) and positional ($N with param_order), ensuring
all SQL placeholders match declared parameters.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.validation.db.sql_utils import normalize_sql, strip_sql_strings

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_operation import ModelDbOperation
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )

# Named parameter pattern (:param_name) - excludes PostgreSQL type casts (::type)
_NAMED_PARAM_PATTERN = re.compile(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)")

# Positional parameter pattern ($1, $2, etc.)
_POSITIONAL_PARAM_PATTERN = re.compile(r"\$(\d+)")


def _validate_positional_params(
    op_name: str,
    op: ModelDbOperation,
    positional_indices: list[str],
) -> list[str]:
    """Validate positional parameters when param_order is provided.

    Checks:
    - Index contiguity (no gaps: $1, $2, $3 OK; $1, $3 NOT OK)
    - Length match (param_order length == max positional index)
    - All param_order names reference valid params (done at model level)
    """
    errors: list[str] = []

    # Convert to integers and sort
    indices = sorted(int(i) for i in positional_indices)

    if not indices:
        return errors

    # Positional indices are 1-based ($1, $2, ...)
    min_index = indices[0]
    max_index = indices[-1]

    # Check indices start at 1
    if min_index != 1:
        errors.append(
            f"Operation '{op_name}': Positional parameters must start at $1, "
            f"but found minimum index ${min_index}."
        )

    # Check for contiguity (no gaps)
    expected_indices = set(range(1, max_index + 1))
    actual_indices = set(indices)
    missing_indices = expected_indices - actual_indices
    if missing_indices:
        missing_formatted = ", ".join(f"${i}" for i in sorted(missing_indices))
        errors.append(
            f"Operation '{op_name}': Positional parameter indices have gaps. "
            f"Missing: {missing_formatted}. Indices must be contiguous ($1, $2, ... $N)."
        )

    # Check param_order length matches max index
    if op.param_order is not None:
        if len(op.param_order) != max_index:
            errors.append(
                f"Operation '{op_name}': param_order has {len(op.param_order)} entries "
                f"but SQL uses up to ${max_index}. Length must match max positional index."
            )

    return errors


def _validate_named_params(
    op_name: str,
    op: ModelDbOperation,
    sql_without_strings: str,
) -> list[str]:
    """Validate named parameters (:param_name).

    Checks:
    - All SQL placeholders are defined in params
    - All defined params are used in SQL
    """
    errors: list[str] = []

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

    return errors


def validate_db_params(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Validate parameter declarations in a DB repository contract.

    Ensures:
    - Named parameters (:param) or positional ($N with param_order), not both
    - All SQL placeholders are defined in params
    - All defined params are used in SQL
    - Positional indices are contiguous (no gaps)
    - param_order length matches max positional index

    Args:
        contract: The DB repository contract to validate.

    Returns:
        Validation result with any parameter errors found.
    """
    errors: list[str] = []

    for op_name, op in contract.ops.items():
        normalized_sql = normalize_sql(op.sql)
        sql_without_strings = strip_sql_strings(normalized_sql)

        # Detect both parameter styles
        positional_matches = _POSITIONAL_PARAM_PATTERN.findall(sql_without_strings)
        named_matches = _NAMED_PARAM_PATTERN.findall(sql_without_strings)

        has_positional = bool(positional_matches)
        has_named = bool(named_matches)

        # Check for mixing styles (forbidden)
        if has_positional and has_named:
            errors.append(
                f"Operation '{op_name}': Cannot mix positional ($N) and named (:param) "
                f"parameters in the same SQL. Found positional: "
                f"{', '.join(f'${p}' for p in positional_matches)}, "
                f"named: {', '.join(f':{n}' for n in named_matches)}. "
                "Use one style consistently."
            )
            continue

        # Handle positional parameters
        if has_positional:
            if op.param_order is None:
                # Helpful hint for migration
                formatted_positions = ", ".join(f"${p}" for p in positional_matches)
                errors.append(
                    f"Operation '{op_name}': Positional parameters ({formatted_positions}) "
                    "require a param_order field to map indices to param names. "
                    "Either add param_order: [param1, param2, ...] or convert to "
                    "named parameters (:param_name) which is the recommended approach."
                )
                continue

            # Validate positional params with param_order
            positional_errors = _validate_positional_params(
                op_name, op, positional_matches
            )
            errors.extend(positional_errors)

            # Also validate that all params in param_order are used
            # (param_order references are validated at model level)
            # Check for unused params not in param_order
            param_order_set = set(op.param_order) if op.param_order else set()
            declared_params = set(op.params.keys())
            unused_params = declared_params - param_order_set
            if unused_params:
                errors.append(
                    f"Operation '{op_name}': Unused parameters declared: "
                    f"{sorted(unused_params)}. Remove them or include them in param_order."
                )

        # Handle named parameters
        elif has_named:
            if op.param_order is not None:
                errors.append(
                    f"Operation '{op_name}': param_order is only used with positional "
                    f"parameters ($1, $2, ...). This operation uses named parameters "
                    f"(:param). Remove param_order or convert SQL to use $N placeholders."
                )
                continue

            named_errors = _validate_named_params(op_name, op, sql_without_strings)
            errors.extend(named_errors)

        # No parameters in SQL - check for declared but unused params
        else:
            declared_params = set(op.params.keys())
            if declared_params:
                errors.append(
                    f"Operation '{op_name}': Unused parameters declared: "
                    f"{sorted(declared_params)}. Remove them or use them in the SQL."
                )

            if op.param_order is not None:
                errors.append(
                    f"Operation '{op_name}': param_order specified but SQL has no "
                    "parameters. Remove param_order or add parameters to SQL."
                )

    if errors:
        return ModelValidationResult.create_invalid(
            errors=errors,
            summary=f"Parameter validation failed with {len(errors)} error(s)",
        )

    return ModelValidationResult.create_valid(
        summary="Parameter validation passed: all parameters match SQL placeholders",
    )


__all__ = ["validate_db_params"]
