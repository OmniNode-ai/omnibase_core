# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-node DB table ownership subcontract for contract-first projection nodes."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.contracts.subcontracts.model_db_table_declaration import (
    ModelDbTableDeclaration,
)

__all__ = ["ModelDbTableDeclaration", "ModelDbOwnershipSubcontract"]


class ModelDbOwnershipSubcontract(BaseModel):
    """Per-node declaration of DB tables owned or accessed by this node."""

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    db_tables: list[ModelDbTableDeclaration] = Field(default_factory=list)

    @field_validator("db_tables")
    @classmethod
    def roles_must_be_unique(
        cls, v: list[ModelDbTableDeclaration]
    ) -> list[ModelDbTableDeclaration]:
        roles = [t.role for t in v]
        seen = set()
        duplicates = [r for r in roles if r in seen or seen.add(r)]  # type: ignore[func-returns-value]
        if duplicates:
            raise ValueError(f"Duplicate db_table roles: {duplicates}")
        return v
