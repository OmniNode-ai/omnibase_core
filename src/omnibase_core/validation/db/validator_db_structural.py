"""Structural validation for DB repository contracts.

Validates:
- Table names are valid SQL identifiers
- Operation names are valid identifiers

Note: Basic field constraints (name, engine, database_ref, mode) are enforced
by Pydantic model validation. This validator adds semantic validation rules.

Note: Multi-statement SQL validation is handled by validator_db_sql_safety.py
to avoid duplicate error messages.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )

# Valid identifier pattern: starts with letter, contains letters/numbers/underscores
_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$", re.IGNORECASE)


def validate_db_structural(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Validate structural requirements of a DB repository contract.

    Validates:
    - contract.tables contains valid SQL identifiers
    - operation names are valid identifiers

    Note: Basic field presence and type constraints (name, engine, database_ref,
    mode) are already enforced by Pydantic model validation (min_length, Literal).
    This validator provides additional semantic validation beyond type constraints.

    Note: Multi-statement SQL validation is handled by validator_db_sql_safety.py.

    Args:
        contract: The DB repository contract to validate.

    Returns:
        Validation result with any structural errors found.
    """
    errors: list[str] = []

    # Note: contract.engine is Literal["postgres"], so Pydantic enforces the constraint
    # at model construction time. No runtime validation needed here.

    # Validate table names are valid SQL identifiers
    if not contract.tables:
        errors.append("tables list cannot be empty")
    else:
        for table in contract.tables:
            if not table:
                errors.append("Table name cannot be empty")
            elif not _IDENTIFIER_PATTERN.match(table):
                errors.append(
                    f"Invalid table name '{table}'. "
                    "Must be a valid SQL identifier (start with letter, "
                    "contain only letters, numbers, and underscores)."
                )

    # Validate operations
    if not contract.ops:
        errors.append("ops dict cannot be empty")

    for op_name in contract.ops:
        # Validate operation name is a valid identifier
        if not op_name:
            errors.append("Operation name cannot be empty")
        elif not _IDENTIFIER_PATTERN.match(op_name):
            errors.append(
                f"Invalid operation name '{op_name}'. "
                "Must be a valid identifier (start with letter, "
                "contain only letters, numbers, and underscores)."
            )

    if errors:
        return ModelValidationResult.create_invalid(
            errors=errors,
            summary=f"Structural validation failed with {len(errors)} error(s)",
        )

    return ModelValidationResult.create_valid(
        summary=(
            f"Structural validation passed for contract '{contract.name}' "
            f"with {len(contract.ops)} operation(s)"
        ),
    )


__all__ = ["validate_db_structural"]
