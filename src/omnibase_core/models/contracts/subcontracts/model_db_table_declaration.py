# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DB table declaration model for contract-first projection nodes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDbTableDeclaration"]


class ModelDbTableDeclaration(BaseModel):
    """Declaration of a DB table owned or accessed by this node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., min_length=1, max_length=63, pattern=r"^[a-z_][a-z0-9_]*$")
    database_ref: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z_][a-z0-9_]*$",
        description="Logical database reference from ModelDeploymentTopology.",
    )
    # Pydantic v2 keeps BaseModel.schema as a deprecated compatibility callable.
    schema: str = Field(  # type: ignore[assignment]
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z_][a-z0-9_]*$",
        description="Schema reference whose topology domain is authoritative.",
    )
    migration: str = Field(..., min_length=1)
    access: Literal["read", "write", "read_write"] = "write"
    role: str = Field(
        ...,
        min_length=1,
        description="Semantic table role; never a PostgreSQL principal.",
    )
