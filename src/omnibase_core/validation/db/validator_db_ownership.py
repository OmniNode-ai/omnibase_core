"""Ownership validation for DB repository contracts.

Validates that a DB repository contract declares ``db_metadata`` in its
table list and includes a ``get_ownership`` operation that reads from it.
This mirrors runtime assertion B1 at the contract level: if the contract
does not declare ownership access, the service cannot verify database
ownership at boot time.

See: OMN-2150 -- Handshake hardening: CI twin for DB ownership test script
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )


def validate_db_ownership(
    contract: ModelDbRepositoryContract,
    *,
    expected_owner_service: str | None = None,
) -> ModelValidationResult[None]:
    """Validate that a DB repository contract declares ownership metadata.

    Checks:
    1. ``db_metadata`` is in the contract's ``tables`` list.
    2. At least one operation reads from ``db_metadata``.
    3. If *expected_owner_service* is provided, validates the contract name
       matches the expected owner (convention: contract name starts with
       the owner service identifier).

    Args:
        contract: The DB repository contract to validate.
        expected_owner_service: Optional owner service name to match.

    Returns:
        Validation result with any ownership errors found.
    """
    errors: list[str] = []

    # Check 1: db_metadata must be in the declared tables
    if "db_metadata" not in contract.tables:
        errors.append(
            "Contract must declare 'db_metadata' in its tables list. "
            "This table is required for runtime ownership verification (B1)."
        )

    # Check 2: at least one operation references db_metadata
    has_metadata_op = False
    for op_name, op in contract.ops.items():
        sql_lower = op.sql.lower()
        if "db_metadata" in sql_lower:
            has_metadata_op = True
            break

    if not has_metadata_op:
        errors.append(
            "Contract must include at least one operation that queries "
            "'db_metadata'. This is required for runtime ownership "
            "verification (B1)."
        )

    # Check 3: optional owner service name matching
    if expected_owner_service is not None and not errors:
        if not contract.name.startswith(expected_owner_service):
            errors.append(
                f"Contract name '{contract.name}' does not match expected "
                f"owner service '{expected_owner_service}'. Convention: "
                f"contract name should start with the owner service identifier."
            )

    if errors:
        return ModelValidationResult.create_invalid(
            errors=errors,
            summary=f"Ownership validation failed with {len(errors)} error(s)",
        )

    return ModelValidationResult.create_valid(
        summary=(
            f"Ownership validation passed for contract '{contract.name}' "
            f"(db_metadata declared, ownership operation present)"
        ),
    )


__all__ = ["validate_db_ownership"]
