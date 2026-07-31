# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Schema declaration for a typed deployment database resource."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_database_schema_domain import EnumDatabaseSchemaDomain

__all__ = ["ModelDeploymentTopologyDatabaseSchema"]

_SQL_IDENTIFIER_PATTERN = r"^[a-z_][a-z0-9_]*$"


class ModelDeploymentTopologyDatabaseSchema(BaseModel):
    """Database schema with an authoritative domain and NOLOGIN owner reference."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    domain: EnumDatabaseSchemaDomain = Field(
        ...,
        description="Authoritative tenant, internal, or platform-catalog domain.",
    )
    owner: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
        description="Reference to a NOLOGIN owner declared on the database resource.",
    )
