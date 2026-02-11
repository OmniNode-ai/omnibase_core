"""Database ownership metadata model.

Defines the schema for the ``db_metadata`` table used by runtime assertion B1
to verify that a database is owned by the expected service.  The CI twin
(``scripts/check_db_ownership.py``) provisions a temporary database, runs
migrations, and asserts this metadata is present.

See: OMN-2150 -- Handshake hardening: CI twin for DB ownership test script
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelDbOwnershipMetadata(BaseModel):
    """Ownership attestation record stored in the ``db_metadata`` table.

    At bootstrap each service writes exactly one row asserting that it is the
    rightful owner of the database.  Runtime assertion B1 and its CI twin read
    this row back and fail loudly if the ``owner_service`` does not match
    expectations.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    owner_service: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description=(
            "Canonical name of the service that owns this database. "
            "Must match the service's own identity at runtime."
        ),
    )

    schema_version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version of the applied migration schema.",
    )

    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the ownership record was written.",
    )


# ---------------------------------------------------------------------------
# Migration SQL
# ---------------------------------------------------------------------------

DB_METADATA_CREATE_SQL = (  # env-var-ok: constant SQL definition
    "CREATE TABLE IF NOT EXISTS db_metadata (\n"
    "    id          INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    "    owner_service   TEXT    NOT NULL,\n"
    "    schema_version  TEXT    NOT NULL,\n"
    "    created_at      TEXT    NOT NULL\n"
    ");\n"
)

DB_METADATA_INSERT_SQL = (  # env-var-ok: constant SQL definition
    "INSERT INTO db_metadata (owner_service, schema_version, created_at)\n"
    "VALUES (:owner_service, :schema_version, :created_at);\n"
)

DB_METADATA_QUERY_SQL = (  # env-var-ok: constant SQL definition
    "SELECT owner_service, schema_version, created_at\n"
    "FROM db_metadata\n"
    "ORDER BY id DESC\n"
    "LIMIT 1;\n"
)


__all__ = [
    "DB_METADATA_CREATE_SQL",
    "DB_METADATA_INSERT_SQL",
    "DB_METADATA_QUERY_SQL",
    "ModelDbOwnershipMetadata",
]
