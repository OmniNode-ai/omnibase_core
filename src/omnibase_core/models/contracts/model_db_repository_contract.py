# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Database repository contract definition.

Defines a complete repository contract including:
- Repository identification
- Database connection reference
- Allowed tables (enforced by validators)
- Model mappings
- Named operations

This eliminates per-domain database adapters by making
data access a first-class, governed contract.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_database_engine import EnumDatabaseEngine
from omnibase_core.models.contracts.model_db_operation import ModelDbOperation


class ModelDbRepositoryContract(BaseModel):
    """Contract for database repository operations.

    Defines a complete repository contract including:
    - Repository identification
    - Database connection reference
    - Allowed tables (enforced by validators)
    - Model mappings
    - Named operations

    This eliminates per-domain database adapters by making
    data access a first-class, governed contract.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identity
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Repository contract name",
    )

    # Database engine type
    engine: EnumDatabaseEngine = Field(
        ...,
        description="Database engine type (postgres, mysql, sqlite)",
    )

    # Database reference
    database_ref: str = Field(
        ...,
        min_length=1,
        description="Database connection reference name",
    )

    # Allowed tables (enforced by validator_db_table_access)
    tables: list[str] = Field(
        ...,
        min_length=1,
        description="List of tables this contract is allowed to access",
    )

    # Model mappings (alias -> import path)
    models: dict[str, str] = Field(
        default_factory=dict,
        description="Model alias to import path mappings",
    )

    # Operations
    ops: dict[str, ModelDbOperation] = Field(
        ...,
        min_length=1,
        description="Named operations keyed by operation name",
    )

    # Documentation
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_model_refs(self) -> "ModelDbRepositoryContract":
        """Validate that operation return model_refs exist in models mapping."""
        for op_name, op in self.ops.items():
            model_ref = op.returns.model_ref
            # Allow fully qualified paths (containing ':' or '.')
            if ":" not in model_ref and "." not in model_ref:
                # Must be an alias - check it exists
                if model_ref not in self.models:
                    msg = f"Operation '{op_name}' references undefined model alias '{model_ref}'. Add it to 'models' mapping or use fully qualified path."
                    raise ValueError(msg)
        return self


__all__ = ["ModelDbRepositoryContract"]
