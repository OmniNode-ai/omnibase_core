# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Checksum-aware migration-ledger declaration for a deployment database."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_migration_ledger_shape import EnumMigrationLedgerShape

__all__ = ["ModelDeploymentTopologyDatabaseMigrationLedger"]

_SQL_IDENTIFIER_PATTERN = r"^[a-z_][a-z0-9_]*$"


class ModelDeploymentTopologyDatabaseMigrationLedger(BaseModel):
    """Typed shape of an existing ledger selected for a migration stream."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    # OMN-17427: the contract key stays `schema`; the Python attribute is
    # `schema_name` because `schema` shadows pydantic's BaseModel.schema().
    schema_name: str = Field(
        ...,
        alias="schema",
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
    )
    shape: EnumMigrationLedgerShape = Field(
        default=EnumMigrationLedgerShape.STREAM_DOMAIN_VERSION_CHECKSUM,
        description=(
            "Ledger column shape: the four-column stream/domain/version/checksum "
            "form (default) or the version/checksum form."
        ),
    )
    relation: str = Field(
        ..., min_length=1, max_length=63, pattern=_SQL_IDENTIFIER_PATTERN
    )
    stream_column: str | None = Field(
        default=None,
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
    )
    domain_column: str | None = Field(
        default=None,
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
    def ledger_columns_match_shape(
        self,
    ) -> "ModelDeploymentTopologyDatabaseMigrationLedger":
        """Require exactly the columns the declared shape names, all distinct."""
        problem = ""
        if self.shape is EnumMigrationLedgerShape.STREAM_DOMAIN_VERSION_CHECKSUM:
            columns = [
                self.stream_column,
                self.domain_column,
                self.version_column,
                self.checksum_column,
            ]
            if self.stream_column is None or self.domain_column is None:
                problem = (
                    "shape stream_domain_version_checksum requires stream_column "
                    "and domain_column"
                )
        else:
            columns = [self.version_column, self.checksum_column]
            if self.stream_column is not None or self.domain_column is not None:
                problem = (
                    "shape version_checksum forbids stream_column and domain_column"
                )
        if not problem and len(set(columns)) != len(columns):
            problem = "Migration ledger columns must be distinct"
        if problem:
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(problem)
        return self
