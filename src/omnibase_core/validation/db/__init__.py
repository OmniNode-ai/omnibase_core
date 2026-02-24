# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Database repository contract validators.

Validators for ModelDbRepositoryContract: structural, SQL safety,
table access, deterministic ordering, parameter, and ownership validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.validation.db.sql_utils import (
    extract_select_columns,
    normalize_sql,
    strip_sql_strings,
)
from omnibase_core.validation.db.validator_db_deterministic import (
    validate_db_deterministic,
)
from omnibase_core.validation.db.validator_db_ownership import (
    validate_db_ownership,
)
from omnibase_core.validation.db.validator_db_params import (
    validate_db_params,
)
from omnibase_core.validation.db.validator_db_projection import (
    validate_db_projection,
)
from omnibase_core.validation.db.validator_db_sql_safety import (
    validate_db_sql_safety,
)
from omnibase_core.validation.db.validator_db_structural import (
    validate_db_structural,
)
from omnibase_core.validation.db.validator_db_table_access import (
    validate_db_table_access,
)

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_db_repository_contract import (
        ModelDbRepositoryContract,
    )


def validate_db_repository_contract(
    contract: ModelDbRepositoryContract,
) -> ModelValidationResult[None]:
    """Run all DB repository validators in sequence.

    Validates structural requirements, SQL safety, table access,
    deterministic ordering, and parameter declarations.

    Returns on first validation failure for efficiency.

    Args:
        contract: The DB repository contract to validate.

    Returns:
        ModelValidationResult with is_valid=True if all validations pass,
        or the first failing result if any validator fails.
    """
    validators = [
        validate_db_structural,
        validate_db_sql_safety,
        validate_db_table_access,
        validate_db_deterministic,
        validate_db_params,
    ]
    for validator in validators:
        result = validator(contract)
        if not result.is_valid:
            return result
    return ModelValidationResult.create_valid(
        summary=f"All validations passed for contract '{contract.name}'"
    )


__all__ = [
    "extract_select_columns",
    "normalize_sql",
    "strip_sql_strings",
    "validate_db_deterministic",
    "validate_db_ownership",
    "validate_db_params",
    "validate_db_projection",
    "validate_db_repository_contract",
    "validate_db_sql_safety",
    "validate_db_structural",
    "validate_db_table_access",
]
