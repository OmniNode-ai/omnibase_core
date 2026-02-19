# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for DB ownership validation (OMN-2150).

Tests the ownership model, validator, and CI twin logic:
1. ModelDbOwnershipMetadata Pydantic model
2. validate_db_ownership contract-level validator
3. CI twin migration/verification logic (via sqlite3)
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_database_engine import EnumDatabaseEngine
from omnibase_core.enums.enum_parameter_type import EnumParameterType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_db_operation import ModelDbOperation
from omnibase_core.models.contracts.model_db_ownership_metadata import (
    DB_METADATA_CREATE_SQL,
    DB_METADATA_INSERT_SQL,
    DB_METADATA_QUERY_SQL,
    ModelDbOwnershipMetadata,
)
from omnibase_core.models.contracts.model_db_param import ModelDbParam
from omnibase_core.models.contracts.model_db_repository_contract import (
    ModelDbRepositoryContract,
)
from omnibase_core.models.contracts.model_db_return import ModelDbReturn
from omnibase_core.validation.db.validator_db_ownership import validate_db_ownership

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ownership_golden_contract() -> ModelDbRepositoryContract:
    """A contract that passes ownership validation.

    Includes db_metadata in tables and a get_ownership operation.
    """
    return ModelDbRepositoryContract(
        name="omnibase_core_repository",
        engine=EnumDatabaseEngine.POSTGRES,
        database_ref="omninode_bridge",
        tables=["db_metadata", "learned_patterns"],
        models={"PatternRow": "omnibase_spi.models:ModelCompiledPattern"},
        ops={
            "get_ownership": ModelDbOperation(
                mode="read",
                sql="""
                    SELECT owner_service, schema_version, created_at
                    FROM db_metadata
                    ORDER BY id DESC
                    LIMIT 1
                """,
                params={},
                returns=ModelDbReturn(
                    model_ref="omnibase_core.models.contracts:ModelDbOwnershipMetadata",
                    many=False,
                ),
            ),
            "list_patterns": ModelDbOperation(
                mode="read",
                sql="""
                    SELECT pattern_id, domain
                    FROM learned_patterns
                    ORDER BY pattern_id ASC
                    LIMIT :limit
                """,
                params={
                    "limit": ModelDbParam(
                        name="limit",
                        param_type=EnumParameterType.INTEGER,
                        required=False,
                        default=ModelSchemaValue.create_number(100),
                        ge=1,
                        le=1000,
                    ),
                },
                returns=ModelDbReturn(model_ref="PatternRow", many=True),
            ),
        },
    )


@pytest.fixture
def no_metadata_contract() -> ModelDbRepositoryContract:
    """A contract without db_metadata in tables."""
    return ModelDbRepositoryContract(
        name="some_repository",
        engine=EnumDatabaseEngine.POSTGRES,
        database_ref="omninode_bridge",
        tables=["learned_patterns"],
        models={"PatternRow": "omnibase_spi.models:ModelCompiledPattern"},
        ops={
            "list_patterns": ModelDbOperation(
                mode="read",
                sql="""
                    SELECT pattern_id FROM learned_patterns ORDER BY pattern_id
                """,
                params={},
                returns=ModelDbReturn(model_ref="PatternRow", many=True),
            ),
        },
    )


@pytest.fixture
def metadata_table_no_op_contract() -> ModelDbRepositoryContract:
    """A contract with db_metadata in tables but no operation that reads it."""
    return ModelDbRepositoryContract(
        name="omnibase_core_repository",
        engine=EnumDatabaseEngine.POSTGRES,
        database_ref="omninode_bridge",
        tables=["db_metadata", "learned_patterns"],
        models={"PatternRow": "omnibase_spi.models:ModelCompiledPattern"},
        ops={
            "list_patterns": ModelDbOperation(
                mode="read",
                sql="""
                    SELECT pattern_id FROM learned_patterns ORDER BY pattern_id
                """,
                params={},
                returns=ModelDbReturn(model_ref="PatternRow", many=True),
            ),
        },
    )


@pytest.fixture
def in_memory_db() -> sqlite3.Connection:
    """Provide an in-memory SQLite database for CI twin tests."""
    conn = sqlite3.connect(":memory:")
    yield conn  # type: ignore[misc]
    conn.close()


# ============================================================================
# ModelDbOwnershipMetadata - Pydantic Model Tests
# ============================================================================


@pytest.mark.unit
class TestModelDbOwnershipMetadata:
    """Tests for the ownership metadata Pydantic model."""

    @pytest.mark.unit
    def test_valid_model(self) -> None:
        """Construct a valid ownership record and verify field assignment."""
        model = ModelDbOwnershipMetadata(
            owner_service="omnibase_core",
            schema_version="1.0.0",
            created_at=datetime.now(tz=UTC),
        )
        assert model.owner_service == "omnibase_core"
        assert model.schema_version == "1.0.0"

    @pytest.mark.unit
    def test_frozen(self) -> None:
        """Verify the model is immutable after construction (frozen=True)."""
        model = ModelDbOwnershipMetadata(
            owner_service="test",
            schema_version="1.0.0",
            created_at=datetime.now(tz=UTC),
        )
        with pytest.raises(Exception):
            model.owner_service = "changed"  # type: ignore[misc]

    @pytest.mark.unit
    def test_empty_owner_rejected(self) -> None:
        """Reject empty-string owner_service to prevent unattributed rows."""
        with pytest.raises(ValueError):
            ModelDbOwnershipMetadata(
                owner_service="",
                schema_version="1.0.0",
                created_at=datetime.now(tz=UTC),
            )

    @pytest.mark.unit
    def test_invalid_schema_version_rejected(self) -> None:
        """Reject non-semver schema_version strings at the Pydantic boundary."""
        with pytest.raises(ValueError):
            ModelDbOwnershipMetadata(
                owner_service="test",
                schema_version="not-semver",
                created_at=datetime.now(tz=UTC),
            )

    @pytest.mark.unit
    def test_semver_pattern_valid_cases(self) -> None:
        """Accept several well-formed semver strings including multi-digit components."""
        for version in ("0.0.1", "1.0.0", "10.20.30"):
            model = ModelDbOwnershipMetadata(
                owner_service="test",
                schema_version=version,
                created_at=datetime.now(tz=UTC),
            )
            assert model.schema_version == version

    @pytest.mark.unit
    def test_naive_datetime_rejected(self) -> None:
        """Reject naive (timezone-unaware) datetimes to enforce UTC contract."""
        with pytest.raises(ValueError, match="timezone-aware"):
            ModelDbOwnershipMetadata(
                owner_service="test",
                schema_version="1.0.0",
                created_at=datetime(2024, 1, 1),
            )


# ============================================================================
# validate_db_ownership - Contract Validator Tests
# ============================================================================


@pytest.mark.unit
class TestValidateDbOwnership:
    """Tests for the ownership contract validator."""

    @pytest.mark.unit
    def test_golden_contract_passes(
        self, ownership_golden_contract: ModelDbRepositoryContract
    ) -> None:
        """A well-formed contract with db_metadata table and operation passes cleanly."""
        result = validate_db_ownership(ownership_golden_contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    @pytest.mark.unit
    def test_missing_db_metadata_table(
        self, no_metadata_contract: ModelDbRepositoryContract
    ) -> None:
        """Fail when the contract omits db_metadata from its tables list."""
        result = validate_db_ownership(no_metadata_contract)
        assert not result.is_valid
        assert any("db_metadata" in e and "tables" in e for e in result.errors)

    @pytest.mark.unit
    def test_no_metadata_operation(
        self, metadata_table_no_op_contract: ModelDbRepositoryContract
    ) -> None:
        """Fail when db_metadata is listed but no operation queries it."""
        result = validate_db_ownership(metadata_table_no_op_contract)
        assert not result.is_valid
        assert any("operation" in e.lower() for e in result.errors)

    @pytest.mark.unit
    def test_expected_owner_match(
        self, ownership_golden_contract: ModelDbRepositoryContract
    ) -> None:
        """Pass when expected_owner_service matches the contract's repository name prefix."""
        result = validate_db_ownership(
            ownership_golden_contract,
            expected_owner_service="omnibase_core",
        )
        assert result.is_valid

    @pytest.mark.unit
    def test_expected_owner_mismatch(
        self, ownership_golden_contract: ModelDbRepositoryContract
    ) -> None:
        """Fail and surface the mismatched service name in errors."""
        result = validate_db_ownership(
            ownership_golden_contract,
            expected_owner_service="wrong_service",
        )
        assert not result.is_valid
        assert any("wrong_service" in e for e in result.errors)


# ============================================================================
# CI Twin Logic - SQLite Integration Tests
# ============================================================================


@pytest.mark.unit
class TestCITwinLogic:
    """Tests for the CI twin database provisioning and verification logic."""

    @pytest.mark.unit
    def test_migration_creates_table(self, in_memory_db: sqlite3.Connection) -> None:
        """Verify the CREATE SQL actually provisions the db_metadata table."""
        in_memory_db.executescript(DB_METADATA_CREATE_SQL)
        cursor = in_memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'"
        )
        assert cursor.fetchone() is not None

    @pytest.mark.unit
    def test_insert_and_read_roundtrip(self, in_memory_db: sqlite3.Connection) -> None:
        """Write an ownership row via INSERT_SQL and read it back via QUERY_SQL."""
        in_memory_db.executescript(DB_METADATA_CREATE_SQL)
        now = datetime.now(tz=UTC).isoformat()
        in_memory_db.execute(
            DB_METADATA_INSERT_SQL,
            {
                "owner_service": "omnibase_core",
                "schema_version": "1.0.0",
                "created_at": now,
            },
        )
        in_memory_db.commit()

        cursor = in_memory_db.execute(DB_METADATA_QUERY_SQL)
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "omnibase_core"
        assert row[1] == "1.0.0"

    @pytest.mark.unit
    def test_pydantic_roundtrip(self, in_memory_db: sqlite3.Connection) -> None:
        """Ensure a DB row can hydrate into ModelDbOwnershipMetadata without loss."""
        in_memory_db.executescript(DB_METADATA_CREATE_SQL)
        now = datetime.now(tz=UTC)
        in_memory_db.execute(
            DB_METADATA_INSERT_SQL,
            {
                "owner_service": "omnibase_core",
                "schema_version": "1.0.0",
                "created_at": now.isoformat(),
            },
        )
        in_memory_db.commit()

        cursor = in_memory_db.execute(DB_METADATA_QUERY_SQL)
        row = cursor.fetchone()
        assert row is not None

        model = ModelDbOwnershipMetadata(
            owner_service=row[0],
            schema_version=row[1],
            created_at=datetime.fromisoformat(row[2]),
        )
        assert model.owner_service == "omnibase_core"

    @pytest.mark.unit
    def test_wrong_owner_detected(self, in_memory_db: sqlite3.Connection) -> None:
        """Detect a foreign owner_service value in the CI twin database."""
        in_memory_db.executescript(DB_METADATA_CREATE_SQL)
        in_memory_db.execute(
            DB_METADATA_INSERT_SQL,
            {
                "owner_service": "wrong_service",
                "schema_version": "1.0.0",
                "created_at": datetime.now(tz=UTC).isoformat(),
            },
        )
        in_memory_db.commit()

        cursor = in_memory_db.execute(DB_METADATA_QUERY_SQL)
        row = cursor.fetchone()
        assert row is not None
        assert row[0] != "omnibase_core"

    @pytest.mark.unit
    def test_missing_table_detected(self) -> None:
        """Confirm a fresh database has no db_metadata table before migration."""
        conn = sqlite3.connect(":memory:")
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'"
        )
        assert cursor.fetchone() is None
        conn.close()

    @pytest.mark.unit
    def test_idempotent_migration(self, in_memory_db: sqlite3.Connection) -> None:
        """Migration uses IF NOT EXISTS and can be run multiple times."""
        in_memory_db.executescript(DB_METADATA_CREATE_SQL)
        in_memory_db.executescript(DB_METADATA_CREATE_SQL)
        cursor = in_memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'"
        )
        assert cursor.fetchone() is not None
