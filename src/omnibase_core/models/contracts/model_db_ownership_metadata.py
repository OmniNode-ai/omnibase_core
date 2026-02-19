# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Database ownership metadata model.

Defines the schema for the ``db_metadata`` table used by runtime assertion B1
to verify that a database is owned by the expected service.  The CI twin
(``scripts/check_db_ownership.py``) provisions a temporary database, runs
migrations, and asserts this metadata is present.

See: OMN-2150 -- Handshake hardening: CI twin for DB ownership test script
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    # Strict MAJOR.MINOR.PATCH only -- pre-release and build metadata suffixes
    # (e.g. "1.0.0-rc.1+build.42") are intentionally rejected.
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

    @field_validator("created_at")
    @classmethod
    def _require_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(
                "created_at must be timezone-aware (use datetime with tz=UTC)"
            )
        return v


# ---------------------------------------------------------------------------
# Migration SQL
# ---------------------------------------------------------------------------

DB_METADATA_CREATE_SQL = (  # env-var-ok: static SQL, not an env variable
    "CREATE TABLE IF NOT EXISTS db_metadata (\n"
    "    id          INTEGER PRIMARY KEY CHECK (id = 1),\n"
    "    owner_service   TEXT    NOT NULL,\n"
    "    schema_version  TEXT    NOT NULL,\n"
    "    created_at      TEXT    NOT NULL\n"
    ");\n"
)

# SQLite-only: INSERT OR REPLACE is used exclusively by the CI twin's SQLite
# provisioning (scripts/check_db_ownership.py).  Production PostgreSQL uses its
# own migration tooling and does not execute this SQL.
DB_METADATA_INSERT_SQL = (  # env-var-ok: static SQL, not an env variable
    "INSERT OR REPLACE INTO db_metadata (id, owner_service, schema_version, created_at)\n"
    "VALUES (1, :owner_service, :schema_version, :created_at);\n"
)

DB_METADATA_QUERY_SQL = (  # env-var-ok: static SQL, not an env variable
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
