# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Checksum-aware migration-ledger declaration for a deployment database."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelDeploymentTopologyDatabaseMigrationLedger"]

_SQL_IDENTIFIER_PATTERN = r"^[a-z_][a-z0-9_]*$"


class ModelDeploymentTopologyDatabaseMigrationLedger(BaseModel):
    """Typed shape of an existing ledger selected for a migration stream."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Pydantic v2 keeps BaseModel.schema as a deprecated compatibility callable.
    schema: str = Field(  # type: ignore[assignment]
        ..., min_length=1, max_length=63, pattern=_SQL_IDENTIFIER_PATTERN
    )
    relation: str = Field(
        ..., min_length=1, max_length=63, pattern=_SQL_IDENTIFIER_PATTERN
    )
    stream_column: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
    )
    domain_column: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
    )
    # string-version-ok: SQL identifier naming a ledger column, not a version value.
    version_column: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
    )
    checksum_column: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
    )

    @model_validator(mode="after")
    def ledger_columns_are_distinct(
        self,
    ) -> "ModelDeploymentTopologyDatabaseMigrationLedger":
        """Each required migration identity dimension needs its own column."""
        columns = {
            self.stream_column,
            self.domain_column,
            self.version_column,
            self.checksum_column,
        }
        if len(columns) != 4:
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError("Migration ledger columns must be distinct")
        return self
