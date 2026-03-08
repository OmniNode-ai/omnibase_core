# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for core infrastructure intents (discriminated union pattern).

Tests verify:
- Individual intent class validation
- Discriminated union routing
- Serialization at I/O boundary
- Immutability and thread safety guarantees
- ONEX patterns (ConfigDict settings, from_attributes)

Test Organization:
- TestModelCoreIntent: Base class tests
- TestModelPostgresUpsertRegistrationIntent: PostgreSQL upsert intent tests
- TestModelCoreRegistrationIntentUnion: Discriminated union tests
- TestIntentSerialization: Serialization boundary tests
- TestONEXPatterns: ONEX-specific pattern compliance tests

Timeout Protection:
- All test classes use @pytest.mark.timeout(5) for unit tests
- Global timeout of 60s is configured in pyproject.toml as fallback
- These are pure Pydantic validation tests with no I/O, so 5s is generous
"""

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.intents import (
    ModelCoreIntent,
    ModelPostgresUpsertRegistrationIntent,
)

# ---- Fixtures ----


@pytest.fixture
def correlation_id() -> UUID:
    """Provide a fresh correlation ID for each test."""
    return uuid4()


@pytest.fixture
def sample_record() -> BaseModel:
    """Provide a sample Pydantic record for PostgreSQL intent."""

    class SampleRecord(BaseModel):
        node_id: str
        node_type: str
        status: str

    return SampleRecord(node_id="node-123", node_type="compute", status="active")


@pytest.fixture
def sample_postgres_intent(
    correlation_id: UUID, sample_record: BaseModel
) -> ModelPostgresUpsertRegistrationIntent:
    """Provide a ModelPostgresUpsertRegistrationIntent."""
    return ModelPostgresUpsertRegistrationIntent(
        kind="postgres.upsert_registration",
        record=sample_record,
        correlation_id=correlation_id,
    )


# ---- Test ModelCoreIntent Base Class ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelCoreIntent:
    """Tests for ModelCoreIntent base class."""

    def test_config_dict_frozen(self) -> None:
        """Test that ModelCoreIntent is configured as frozen (immutable)."""
        assert ModelCoreIntent.model_config.get("frozen") is True

    def test_config_dict_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""
        assert ModelCoreIntent.model_config.get("extra") == "forbid"

    def test_config_dict_from_attributes(self) -> None:
        """Test that from_attributes is enabled for pytest-xdist compatibility."""
        assert ModelCoreIntent.model_config.get("from_attributes") is True

    def test_config_dict_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled."""
        assert ModelCoreIntent.model_config.get("validate_assignment") is True

    def test_serialize_for_io_method_exists(self) -> None:
        """Test that serialize_for_io method exists on base class."""
        assert hasattr(ModelCoreIntent, "serialize_for_io")
        assert callable(ModelCoreIntent.serialize_for_io)


# ---- Test ModelPostgresUpsertRegistrationIntent ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelPostgresUpsertRegistrationIntent:
    """Tests for ModelPostgresUpsertRegistrationIntent."""

    def test_valid_construction(self, correlation_id) -> None:
        """Test valid intent construction with BaseModel record."""

        class SampleRecord(BaseModel):
            node_id: str
            node_type: str

        record = SampleRecord(node_id="123", node_type="compute")
        intent = ModelPostgresUpsertRegistrationIntent(
            kind="postgres.upsert_registration",
            record=record,
            correlation_id=correlation_id,
        )
        assert intent.kind == "postgres.upsert_registration"
        assert intent.record == record

    def test_default_kind(self, correlation_id, sample_record) -> None:
        """Test kind has correct default value."""
        intent = ModelPostgresUpsertRegistrationIntent(
            record=sample_record,
            correlation_id=correlation_id,
        )
        assert intent.kind == "postgres.upsert_registration"

    def test_missing_record(self, correlation_id) -> None:
        """Test record is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPostgresUpsertRegistrationIntent(
                correlation_id=correlation_id,
            )
        assert "record" in str(exc_info.value)

    def test_immutability(self, sample_postgres_intent) -> None:
        """Test intent is immutable (frozen)."""
        with pytest.raises(ValidationError):
            sample_postgres_intent.kind = "changed"

    def test_record_with_nested_model(self, correlation_id) -> None:
        """Test record can contain nested Pydantic models."""

        class NestedConfig(BaseModel):
            timeout: int
            retries: int

        class RecordWithNested(BaseModel):
            node_id: str
            config: NestedConfig

        record = RecordWithNested(
            node_id="node-123",
            config=NestedConfig(timeout=30, retries=3),
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )
        assert intent.record.node_id == "node-123"  # type: ignore[attr-defined]
        assert intent.record.config.timeout == 30  # type: ignore[attr-defined]

    def test_inherits_from_core_intent(self) -> None:
        """Test ModelPostgresUpsertRegistrationIntent inherits from ModelCoreIntent."""
        assert issubclass(ModelPostgresUpsertRegistrationIntent, ModelCoreIntent)


# ---- Test Discriminated Union ----


# ---- Test Serialization ----


# ---- Test ONEX Patterns ----


# ---- Test Edge Cases ----


# ---- Test Type Safety ----


# ---- Test Serialization Edge Cases ----


# ---- Test ModelRegistrationRecordBase Integration ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelRegistrationRecordBaseIntegration:
    """Tests for ModelRegistrationRecordBase with PostgreSQL intent.

    These tests verify that the new ModelRegistrationRecordBase works correctly
    with ModelPostgresUpsertRegistrationIntent.
    """

    def test_base_class_record_with_intent(self, correlation_id: UUID) -> None:
        """Test ModelRegistrationRecordBase works with PostgreSQL intent."""
        from omnibase_core.models.intents import ModelRegistrationRecordBase

        class NodeRecord(ModelRegistrationRecordBase):
            node_id: str
            node_type: str
            status: str

        record = NodeRecord(
            node_id="node-123",
            node_type="compute",
            status="active",
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        assert intent.record == record
        assert intent.kind == "postgres.upsert_registration"

    def test_base_class_to_persistence_dict_integration(
        self, correlation_id: UUID
    ) -> None:
        """Test to_persistence_dict works with intent serialization."""
        from omnibase_core.models.intents import ModelRegistrationRecordBase

        class ServiceRecord(ModelRegistrationRecordBase):
            service_id: str
            endpoint: str
            is_healthy: bool

        record = ServiceRecord(
            service_id="svc-456",
            endpoint="http://localhost:8080",
            is_healthy=True,
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # to_persistence_dict should work on the record
        persistence_data = record.to_persistence_dict()
        assert persistence_data["service_id"] == "svc-456"
        assert persistence_data["endpoint"] == "http://localhost:8080"
        assert persistence_data["is_healthy"] is True

    def test_protocol_registration_record_isinstance_check(
        self, correlation_id: UUID
    ) -> None:
        """Test that base class instances pass protocol isinstance check."""
        from omnibase_core.models.intents import ModelRegistrationRecordBase
        from omnibase_core.protocols.intents import ProtocolRegistrationRecord

        class TestRecord(ModelRegistrationRecordBase):
            value: str

        record = TestRecord(value="test")

        # Record should implement the protocol
        assert isinstance(record, ProtocolRegistrationRecord)

    def test_intent_with_nested_record_fields(self, correlation_id: UUID) -> None:
        """Test intent with complex nested record using base class."""
        from omnibase_core.models.intents import ModelRegistrationRecordBase

        class ConfigData(BaseModel):
            timeout_ms: int
            max_retries: int

        class ComplexRecord(ModelRegistrationRecordBase):
            node_id: str
            config: ConfigData
            tags: list[str]

        record = ComplexRecord(
            node_id="complex-node",
            config=ConfigData(timeout_ms=5000, max_retries=3),
            tags=["production", "critical"],
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Verify record data
        persistence_data = record.to_persistence_dict()
        assert persistence_data["node_id"] == "complex-node"
        assert persistence_data["config"]["timeout_ms"] == 5000
        assert persistence_data["config"]["max_retries"] == 3
        assert persistence_data["tags"] == ["production", "critical"]

        # Verify intent serialization with serialize_as_any
        intent_data = intent.model_dump(mode="json", serialize_as_any=True)
        assert intent_data["record"]["node_id"] == "complex-node"
        assert intent_data["record"]["config"]["timeout_ms"] == 5000
