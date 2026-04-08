# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-node DB table ownership subcontract for contract-first projection nodes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDbTableDeclaration", "ModelDbOwnershipSubcontract"]


class ModelDbTableDeclaration(BaseModel):
    """Declaration of a DB table owned or accessed by this node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str
    migration: str
    access: Literal["read", "write", "read_write"] = "write"
    database: str = "omnidash_analytics"
    role: str


class ModelDbOwnershipSubcontract(BaseModel):
    """Per-node declaration of DB tables owned or accessed by this node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    db_tables: list[ModelDbTableDeclaration] = Field(default_factory=list)
