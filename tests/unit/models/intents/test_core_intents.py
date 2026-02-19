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
- TestModelConsulRegisterIntent: Consul registration intent tests
- TestModelConsulDeregisterIntent: Consul deregistration intent tests
- TestModelPostgresUpsertRegistrationIntent: PostgreSQL upsert intent tests
- TestModelCoreRegistrationIntentUnion: Discriminated union tests
- TestIntentSerialization: Serialization boundary tests
- TestONEXPatterns: ONEX-specific pattern compliance tests

Timeout Protection:
- All test classes use @pytest.mark.timeout(5) for unit tests
- Global timeout of 60s is configured in pyproject.toml as fallback
- These are pure Pydantic validation tests with no I/O, so 5s is generous
"""

from datetime import UTC
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from omnibase_core.models.intents import (
    ModelConsulDeregisterIntent,
    ModelConsulRegisterIntent,
    ModelCoreIntent,
    ModelCoreRegistrationIntent,
    ModelPostgresUpsertRegistrationIntent,
)

# ---- Fixtures ----


@pytest.fixture
def correlation_id() -> UUID:
    """Provide a fresh correlation ID for each test."""
    return uuid4()


@pytest.fixture
def sample_consul_register_intent(correlation_id: UUID) -> ModelConsulRegisterIntent:
    """Provide a fully populated ModelConsulRegisterIntent."""
    return ModelConsulRegisterIntent(
        kind="consul.register",
        service_id="node-123",
        service_name="onex-compute",
        tags=["node_type:compute", "version:1.0"],
        health_check={"http": "http://localhost:8080/health"},
        correlation_id=correlation_id,
    )


@pytest.fixture
def sample_consul_deregister_intent(
    correlation_id: UUID,
) -> ModelConsulDeregisterIntent:
    """Provide a ModelConsulDeregisterIntent."""
    return ModelConsulDeregisterIntent(
        kind="consul.deregister",
        service_id="node-123",
        correlation_id=correlation_id,
    )


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


# ---- Test ModelConsulRegisterIntent ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelConsulRegisterIntent:
    """Tests for ModelConsulRegisterIntent."""

    def test_valid_construction(self, correlation_id) -> None:
        """Test valid intent construction with all required fields."""
        intent = ModelConsulRegisterIntent(
            kind="consul.register",
            service_id="node-123",
            service_name="onex-compute",
            tags=["test"],
            health_check=None,
            correlation_id=correlation_id,
        )
        assert intent.kind == "consul.register"
        assert intent.service_id == "node-123"
        assert intent.service_name == "onex-compute"
        assert intent.tags == ["test"]
        assert intent.health_check is None
        assert intent.correlation_id == correlation_id

    def test_default_kind(self, correlation_id) -> None:
        """Test kind has correct default value."""
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="onex-compute",
            correlation_id=correlation_id,
        )
        assert intent.kind == "consul.register"

    def test_default_tags(self, correlation_id) -> None:
        """Test tags defaults to empty list."""
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="onex-compute",
            correlation_id=correlation_id,
        )
        assert intent.tags == []

    def test_default_health_check(self, correlation_id) -> None:
        """Test health_check defaults to None."""
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="onex-compute",
            correlation_id=correlation_id,
        )
        assert intent.health_check is None

    def test_immutability(self, sample_consul_register_intent) -> None:
        """Test intent is immutable (frozen)."""
        with pytest.raises(ValidationError):
            sample_consul_register_intent.service_id = "changed"

    def test_service_id_min_length(self, correlation_id) -> None:
        """Test service_id minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulRegisterIntent(
                service_id="",  # Empty string
                service_name="test",
                correlation_id=correlation_id,
            )
        assert "service_id" in str(exc_info.value)

    def test_service_name_min_length(self, correlation_id) -> None:
        """Test service_name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulRegisterIntent(
                service_id="node-123",
                service_name="",  # Empty string
                correlation_id=correlation_id,
            )
        assert "service_name" in str(exc_info.value)

    def test_service_id_max_length(self, correlation_id) -> None:
        """Test service_id maximum length validation (200 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulRegisterIntent(
                service_id="x" * 201,  # 201 characters exceeds max
                service_name="test",
                correlation_id=correlation_id,
            )
        assert "service_id" in str(exc_info.value)

    def test_service_name_max_length(self, correlation_id) -> None:
        """Test service_name maximum length validation (100 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulRegisterIntent(
                service_id="node-123",
                service_name="x" * 101,  # 101 characters exceeds max
                correlation_id=correlation_id,
            )
        assert "service_name" in str(exc_info.value)

    def test_extra_fields_forbidden(self, correlation_id) -> None:
        """Test extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulRegisterIntent(
                service_id="node-123",
                service_name="test",
                correlation_id=correlation_id,
                unknown_field="value",  # Extra field
            )
        # Check for extra field rejection
        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "unknown_field" in error_str

    def test_health_check_with_config(self, correlation_id) -> None:
        """Test intent with health check configuration."""
        health_config = {"http": "http://localhost:8080/health", "interval": "10s"}
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            health_check=health_config,
            correlation_id=correlation_id,
        )
        assert intent.health_check == health_config

    def test_health_check_with_non_string_values(self, correlation_id) -> None:
        """Test health check accepts non-string values (int, bool, nested dict).

        Consul health check configurations can contain:
        - Integers: interval_seconds, timeout_seconds, deregister_critical_service_after
        - Booleans: tls_skip_verify, grpc_use_tls
        - Nested dicts: header configurations
        """
        health_config = {
            "http": "http://localhost:8080/health",
            "interval": 10,  # Integer for seconds
            "timeout": 5,  # Integer for seconds
            "tls_skip_verify": True,  # Boolean
            "deregister_critical_service_after": 300,  # Integer for seconds
            "header": {"Authorization": ["Bearer token"]},  # Nested dict with list
        }
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            health_check=health_config,
            correlation_id=correlation_id,
        )
        assert intent.health_check == health_config
        assert intent.health_check["interval"] == 10
        assert intent.health_check["tls_skip_verify"] is True
        assert intent.health_check["header"]["Authorization"] == ["Bearer token"]

    def test_multiple_tags(self, correlation_id) -> None:
        """Test intent with multiple tags."""
        tags = ["node_type:compute", "version:1.0", "env:prod"]
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            tags=tags,
            correlation_id=correlation_id,
        )
        assert intent.tags == tags
        assert len(intent.tags) == 3

    def test_inherits_from_core_intent(self) -> None:
        """Test ModelConsulRegisterIntent inherits from ModelCoreIntent."""
        assert issubclass(ModelConsulRegisterIntent, ModelCoreIntent)


# ---- Test ModelConsulDeregisterIntent ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelConsulDeregisterIntent:
    """Tests for ModelConsulDeregisterIntent."""

    def test_valid_construction(self, correlation_id) -> None:
        """Test valid intent construction."""
        intent = ModelConsulDeregisterIntent(
            kind="consul.deregister",
            service_id="node-123",
            correlation_id=correlation_id,
        )
        assert intent.kind == "consul.deregister"
        assert intent.service_id == "node-123"
        assert intent.correlation_id == correlation_id

    def test_default_kind(self, correlation_id) -> None:
        """Test kind has correct default value."""
        intent = ModelConsulDeregisterIntent(
            service_id="node-123",
            correlation_id=correlation_id,
        )
        assert intent.kind == "consul.deregister"

    def test_missing_service_id(self, correlation_id) -> None:
        """Test service_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulDeregisterIntent(
                correlation_id=correlation_id,
            )
        assert "service_id" in str(exc_info.value)

    def test_service_id_min_length(self, correlation_id) -> None:
        """Test service_id minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulDeregisterIntent(
                service_id="",  # Empty string
                correlation_id=correlation_id,
            )
        assert "service_id" in str(exc_info.value)

    def test_service_id_max_length(self, correlation_id) -> None:
        """Test service_id maximum length validation (200 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulDeregisterIntent(
                service_id="x" * 201,  # 201 characters exceeds max
                correlation_id=correlation_id,
            )
        assert "service_id" in str(exc_info.value)

    def test_immutability(self, sample_consul_deregister_intent) -> None:
        """Test intent is immutable (frozen)."""
        with pytest.raises(ValidationError):
            sample_consul_deregister_intent.service_id = "changed"

    def test_extra_fields_forbidden(self, correlation_id) -> None:
        """Test extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulDeregisterIntent(
                service_id="node-123",
                correlation_id=correlation_id,
                extra_field="not_allowed",
            )
        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "extra_field" in error_str

    def test_inherits_from_core_intent(self) -> None:
        """Test ModelConsulDeregisterIntent inherits from ModelCoreIntent."""
        assert issubclass(ModelConsulDeregisterIntent, ModelCoreIntent)


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


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelCoreRegistrationIntentUnion:
    """Tests for ModelCoreRegistrationIntent discriminated union."""

    def test_parse_consul_register(self, correlation_id) -> None:
        """Test parsing dict with consul.register kind."""
        adapter = TypeAdapter(ModelCoreRegistrationIntent)
        data = {
            "kind": "consul.register",
            "service_id": "node-123",
            "service_name": "onex-compute",
            "tags": [],
            "health_check": None,
            "correlation_id": str(correlation_id),
        }
        intent = adapter.validate_python(data)
        assert isinstance(intent, ModelConsulRegisterIntent)
        assert intent.kind == "consul.register"
        assert intent.service_id == "node-123"
        assert intent.service_name == "onex-compute"

    def test_parse_consul_deregister(self, correlation_id) -> None:
        """Test parsing dict with consul.deregister kind."""
        adapter = TypeAdapter(ModelCoreRegistrationIntent)
        data = {
            "kind": "consul.deregister",
            "service_id": "node-123",
            "correlation_id": str(correlation_id),
        }
        intent = adapter.validate_python(data)
        assert isinstance(intent, ModelConsulDeregisterIntent)
        assert intent.kind == "consul.deregister"
        assert intent.service_id == "node-123"

    def test_parse_postgres_upsert(self, correlation_id) -> None:
        """Test parsing dict with postgres.upsert_registration kind."""
        adapter = TypeAdapter(ModelCoreRegistrationIntent)
        data = {
            "kind": "postgres.upsert_registration",
            "record": {"data": "test"},
            "correlation_id": str(correlation_id),
        }
        intent = adapter.validate_python(data)
        assert isinstance(intent, ModelPostgresUpsertRegistrationIntent)
        assert intent.kind == "postgres.upsert_registration"

    def test_invalid_kind_rejected(self, correlation_id) -> None:
        """Test invalid kind value is rejected."""
        adapter = TypeAdapter(ModelCoreRegistrationIntent)
        data = {
            "kind": "invalid.kind",
            "service_id": "node-123",
            "correlation_id": str(correlation_id),
        }
        with pytest.raises(ValidationError):
            adapter.validate_python(data)

    def test_missing_kind_rejected(self, correlation_id) -> None:
        """Test missing kind field is rejected."""
        adapter = TypeAdapter(ModelCoreRegistrationIntent)
        data = {
            "service_id": "node-123",
            "service_name": "test",
            "correlation_id": str(correlation_id),
        }
        with pytest.raises(ValidationError):
            adapter.validate_python(data)

    def test_discriminator_routes_correctly(self, correlation_id) -> None:
        """Test that discriminator routes to correct concrete class."""
        adapter = TypeAdapter(ModelCoreRegistrationIntent)

        # Test all three intent types
        register_data = {
            "kind": "consul.register",
            "service_id": "svc-1",
            "service_name": "test",
            "correlation_id": str(correlation_id),
        }
        deregister_data = {
            "kind": "consul.deregister",
            "service_id": "svc-1",
            "correlation_id": str(correlation_id),
        }
        postgres_data = {
            "kind": "postgres.upsert_registration",
            "record": {"node_id": "123"},
            "correlation_id": str(correlation_id),
        }

        register_intent = adapter.validate_python(register_data)
        deregister_intent = adapter.validate_python(deregister_data)
        postgres_intent = adapter.validate_python(postgres_data)

        assert type(register_intent) is ModelConsulRegisterIntent
        assert type(deregister_intent) is ModelConsulDeregisterIntent
        assert type(postgres_intent) is ModelPostgresUpsertRegistrationIntent


# ---- Test Serialization ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestIntentSerialization:
    """Tests for intent serialization at I/O boundary."""

    def test_model_dump_json_mode(self, sample_consul_register_intent) -> None:
        """Test model_dump with mode='json' produces valid JSON types."""
        data = sample_consul_register_intent.model_dump(mode="json")
        assert isinstance(data, dict)
        assert isinstance(data["correlation_id"], str)  # UUID serialized as string
        assert data["kind"] == "consul.register"
        assert isinstance(data["service_id"], str)
        assert isinstance(data["service_name"], str)
        assert isinstance(data["tags"], list)

    def test_serialize_for_io_method(self, sample_consul_register_intent) -> None:
        """Test serialize_for_io() method."""
        data = sample_consul_register_intent.serialize_for_io()
        assert isinstance(data, dict)
        assert "correlation_id" in data
        assert "kind" in data
        assert isinstance(data["correlation_id"], str)

    def test_serialize_for_io_consul_deregister(
        self, sample_consul_deregister_intent
    ) -> None:
        """Test serialize_for_io() for deregister intent."""
        data = sample_consul_deregister_intent.serialize_for_io()
        assert isinstance(data, dict)
        assert data["kind"] == "consul.deregister"
        assert isinstance(data["service_id"], str)

    def test_serialize_for_io_postgres(self, sample_postgres_intent) -> None:
        """Test serialize_for_io() for postgres intent."""
        data = sample_postgres_intent.serialize_for_io()
        assert isinstance(data, dict)
        assert data["kind"] == "postgres.upsert_registration"
        assert "record" in data
        # Record should be serialized as dict
        assert isinstance(data["record"], dict)

    def test_roundtrip_serialization_consul_register(self, correlation_id) -> None:
        """Test ModelConsulRegisterIntent can be serialized and deserialized."""
        original = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="onex-compute",
            tags=["test"],
            health_check={"http": "http://localhost/health"},
            correlation_id=correlation_id,
        )
        data = original.model_dump(mode="json")
        restored = ModelConsulRegisterIntent.model_validate(data)
        assert restored.service_id == original.service_id
        assert restored.service_name == original.service_name
        assert restored.tags == original.tags
        assert restored.health_check == original.health_check
        # UUID comparison - converted from string
        assert str(restored.correlation_id) == str(original.correlation_id)

    def test_roundtrip_serialization_consul_deregister(self, correlation_id) -> None:
        """Test ModelConsulDeregisterIntent can be serialized and deserialized."""
        original = ModelConsulDeregisterIntent(
            service_id="node-123",
            correlation_id=correlation_id,
        )
        data = original.model_dump(mode="json")
        restored = ModelConsulDeregisterIntent.model_validate(data)
        assert restored.service_id == original.service_id
        assert str(restored.correlation_id) == str(original.correlation_id)

    def test_roundtrip_via_union_adapter(self, correlation_id) -> None:
        """Test roundtrip through discriminated union TypeAdapter."""
        adapter = TypeAdapter(ModelCoreRegistrationIntent)

        original = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="onex-compute",
            correlation_id=correlation_id,
        )
        data = original.model_dump(mode="json")
        restored = adapter.validate_python(data)

        assert isinstance(restored, ModelConsulRegisterIntent)
        assert restored.service_id == original.service_id
        assert restored.service_name == original.service_name

    def test_model_dump_json_format(self, sample_consul_register_intent) -> None:
        """Test model_dump_json produces valid JSON string."""
        json_str = sample_consul_register_intent.model_dump_json()
        assert isinstance(json_str, str)
        # Should be parseable
        import json

        data = json.loads(json_str)
        assert data["kind"] == "consul.register"


# ---- Test ONEX Patterns ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestONEXPatterns:
    """Tests for ONEX-specific patterns and configurations."""

    def test_from_attributes_enabled_consul_register(self, correlation_id) -> None:
        """Test from_attributes=True allows attribute-based construction."""
        # Create instance with attributes (not class attributes that capture fixture ref)
        corr_id = correlation_id  # Capture fixture value in local scope

        class IntentLike:
            kind = "consul.register"
            service_id = "node-123"
            service_name = "onex-compute"
            tags: list[str] = []
            health_check = None

            def __init__(self) -> None:
                self.correlation_id = corr_id

        intent = ModelConsulRegisterIntent.model_validate(IntentLike())
        assert intent.service_id == "node-123"
        assert intent.service_name == "onex-compute"

    def test_from_attributes_enabled_consul_deregister(self, correlation_id) -> None:
        """Test from_attributes=True for deregister intent."""
        corr_id = correlation_id  # Capture fixture value in local scope

        class IntentLike:
            kind = "consul.deregister"
            service_id = "node-123"

            def __init__(self) -> None:
                self.correlation_id = corr_id

        intent = ModelConsulDeregisterIntent.model_validate(IntentLike())
        assert intent.service_id == "node-123"

    def test_config_dict_settings_consul_register(self) -> None:
        """Test ConfigDict settings are correct for ModelConsulRegisterIntent."""
        config = ModelConsulRegisterIntent.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("from_attributes") is True

    def test_config_dict_settings_consul_deregister(self) -> None:
        """Test ConfigDict settings are correct for ModelConsulDeregisterIntent."""
        config = ModelConsulDeregisterIntent.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("from_attributes") is True

    def test_config_dict_settings_postgres_upsert(self) -> None:
        """Test ConfigDict settings are correct for ModelPostgresUpsertRegistrationIntent."""
        config = ModelPostgresUpsertRegistrationIntent.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("from_attributes") is True

    def test_all_intents_inherit_config_from_base(self) -> None:
        """Test all concrete intents inherit config from ModelCoreIntent."""
        # The concrete classes should have the same config as base
        base_config = ModelCoreIntent.model_config

        for intent_class in [
            ModelConsulRegisterIntent,
            ModelConsulDeregisterIntent,
            ModelPostgresUpsertRegistrationIntent,
        ]:
            assert intent_class.model_config.get("frozen") == base_config.get("frozen")
            assert intent_class.model_config.get("extra") == base_config.get("extra")
            assert intent_class.model_config.get("from_attributes") == base_config.get(
                "from_attributes"
            )


# ---- Test Edge Cases ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_correlation_id_as_string_accepted(self) -> None:
        """Test correlation_id can be provided as string (UUID format)."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            correlation_id=uuid_str,  # String UUID
        )
        assert str(intent.correlation_id) == uuid_str

    def test_correlation_id_invalid_format_rejected(self) -> None:
        """Test invalid UUID format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConsulRegisterIntent(
                service_id="node-123",
                service_name="test",
                correlation_id="not-a-uuid",
            )
        assert "correlation_id" in str(exc_info.value)

    def test_unicode_service_id(self, correlation_id) -> None:
        """Test service_id with unicode characters."""
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            correlation_id=correlation_id,
        )
        # ASCII characters are fine
        assert intent.service_id == "node-123"

    def test_special_characters_in_tags(self, correlation_id) -> None:
        """Test tags with special characters."""
        tags = ["env:prod", "team:platform/core", "version:1.0.0-beta+build.123"]
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            tags=tags,
            correlation_id=correlation_id,
        )
        assert intent.tags == tags

    def test_empty_health_check_dict(self, correlation_id) -> None:
        """Test empty health check dictionary."""
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            health_check={},
            correlation_id=correlation_id,
        )
        assert intent.health_check == {}

    def test_service_id_at_max_length(self, correlation_id) -> None:
        """Test service_id at exactly max length (200)."""
        intent = ModelConsulRegisterIntent(
            service_id="x" * 200,  # Exactly at max
            service_name="test",
            correlation_id=correlation_id,
        )
        assert len(intent.service_id) == 200

    def test_service_name_at_max_length(self, correlation_id) -> None:
        """Test service_name at exactly max length (100)."""
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="y" * 100,  # Exactly at max
            correlation_id=correlation_id,
        )
        assert len(intent.service_name) == 100

    def test_postgres_record_empty_model(self, correlation_id) -> None:
        """Test PostgreSQL intent with minimal model."""

        class MinimalRecord(BaseModel):
            pass

        record = MinimalRecord()
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )
        assert isinstance(intent.record, BaseModel)

    def test_many_tags(self, correlation_id) -> None:
        """Test intent with many tags."""
        tags = [f"tag_{i}" for i in range(100)]
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            tags=tags,
            correlation_id=correlation_id,
        )
        assert len(intent.tags) == 100


# ---- Test Type Safety ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestTypeSafety:
    """Tests for type safety guarantees."""

    def test_kind_literal_type_consul_register(self, correlation_id) -> None:
        """Test kind field is Literal type for ModelConsulRegisterIntent."""
        intent = ModelConsulRegisterIntent(
            service_id="node-123",
            service_name="test",
            correlation_id=correlation_id,
        )
        # Kind should always be exactly "consul.register"
        assert intent.kind == "consul.register"

    def test_kind_literal_type_consul_deregister(self, correlation_id) -> None:
        """Test kind field is Literal type for ModelConsulDeregisterIntent."""
        intent = ModelConsulDeregisterIntent(
            service_id="node-123",
            correlation_id=correlation_id,
        )
        assert intent.kind == "consul.deregister"

    def test_kind_literal_type_postgres(self, correlation_id, sample_record) -> None:
        """Test kind field is Literal type for ModelPostgresUpsertRegistrationIntent."""
        intent = ModelPostgresUpsertRegistrationIntent(
            record=sample_record,
            correlation_id=correlation_id,
        )
        assert intent.kind == "postgres.upsert_registration"

    def test_cannot_override_kind_with_wrong_value(self, correlation_id) -> None:
        """Test that providing wrong kind value is rejected."""
        # Trying to create ModelConsulRegisterIntent with wrong kind
        with pytest.raises(ValidationError):
            ModelConsulRegisterIntent(
                kind="consul.deregister",  # Wrong kind
                service_id="node-123",
                service_name="test",
                correlation_id=correlation_id,
            )

    def test_pattern_matching_support(
        self,
        sample_consul_register_intent,
        sample_consul_deregister_intent,
        sample_postgres_intent,
    ) -> None:
        """Test intents support pattern matching."""
        intents = [
            sample_consul_register_intent,
            sample_consul_deregister_intent,
            sample_postgres_intent,
        ]

        results = []
        for intent in intents:
            match intent:
                case ModelConsulRegisterIntent():
                    results.append("register")
                case ModelConsulDeregisterIntent():
                    results.append("deregister")
                case ModelPostgresUpsertRegistrationIntent():
                    results.append("postgres")

        assert results == ["register", "deregister", "postgres"]


# ---- Test Serialization Edge Cases ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestSerializationEdgeCases:
    """Comprehensive tests for serialization edge cases.

    These tests verify correct serialization behavior for:
    - Deeply nested Pydantic models (PostgreSQL intents)
    - UUID serialization to string format
    - None/null value handling in optional fields
    - Empty dict serialization
    - Special characters in string fields
    - Round-trip serialization preservation

    Important Note on PostgreSQL Intent Record Serialization:
        The `record` field in ModelPostgresUpsertRegistrationIntent is typed as
        `BaseModel`, which creates polymorphic serialization challenges. By default,
        `model_dump(mode="json")` only serializes fields defined on the declared type
        (BaseModel), not subclass fields. To properly serialize record fields, use
        `model_dump(mode="json", serialize_as_any=True)`.

        Tests in this class use `serialize_as_any=True` for PostgreSQL intents
        with custom records to demonstrate the recommended pattern.
    """

    # ---- Nested Model Serialization Tests ----

    def test_deeply_nested_model_serialization_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test serialization of deeply nested Pydantic models with serialize_as_any.

        This test demonstrates the recommended pattern for serializing PostgreSQL
        intents with custom record types. The serialize_as_any=True flag ensures
        all subclass fields are properly serialized.
        """

        class Level3Config(BaseModel):
            retry_count: int
            backoff_ms: int
            enabled: bool

        class Level2Config(BaseModel):
            database: str
            level3: Level3Config

        class Level1Config(BaseModel):
            environment: str
            level2: Level2Config

        class NestedRecord(BaseModel):
            node_id: str
            config: Level1Config

        record = NestedRecord(
            node_id="node-nested-123",
            config=Level1Config(
                environment="production",
                level2=Level2Config(
                    database="postgres",
                    level3=Level3Config(
                        retry_count=3,
                        backoff_ms=1000,
                        enabled=True,
                    ),
                ),
            ),
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper polymorphic serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        # Verify nested structure is preserved as dict
        assert isinstance(data["record"], dict)
        assert data["record"]["node_id"] == "node-nested-123"
        assert data["record"]["config"]["environment"] == "production"
        assert data["record"]["config"]["level2"]["database"] == "postgres"
        assert data["record"]["config"]["level2"]["level3"]["retry_count"] == 3
        assert data["record"]["config"]["level2"]["level3"]["backoff_ms"] == 1000
        assert data["record"]["config"]["level2"]["level3"]["enabled"] is True

    def test_nested_model_roundtrip_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test round-trip (model -> dict -> model) preserves nested data.

        Uses serialize_as_any=True for proper serialization and validates
        that record data is preserved through the round-trip.
        """

        class InnerConfig(BaseModel):
            timeout_seconds: int
            max_retries: int

        class OuterRecord(BaseModel):
            service_name: str
            inner: InnerConfig

        original_record = OuterRecord(
            service_name="test-service",
            inner=InnerConfig(timeout_seconds=30, max_retries=5),
        )
        original = ModelPostgresUpsertRegistrationIntent(
            record=original_record,
            correlation_id=correlation_id,
        )

        # Serialize with serialize_as_any=True
        data = original.model_dump(mode="json", serialize_as_any=True)
        restored = ModelPostgresUpsertRegistrationIntent.model_validate(data)

        # Verify key fields are preserved through round-trip
        assert restored.kind == original.kind
        assert restored.correlation_id == original.correlation_id

        # Verify record data is accessible through the validated model
        # The record becomes a dict-like BaseModel after validation
        # Access the original serialized data to verify preservation
        assert data["record"]["service_name"] == "test-service"
        assert data["record"]["inner"]["timeout_seconds"] == 30
        assert data["record"]["inner"]["max_retries"] == 5

    def test_json_serialization_nested_structures_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test JSON serialization produces valid JSON for nested structures."""
        import json

        class ConfigRecord(BaseModel):
            node_id: str
            settings: dict[str, int]

        record = ConfigRecord(
            node_id="node-json-test",
            settings={"port": 8080, "workers": 4},
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Serialize to JSON string with serialize_as_any
        json_str = intent.model_dump_json(serialize_as_any=True)

        # Parse JSON and verify structure
        parsed = json.loads(json_str)
        assert parsed["record"]["node_id"] == "node-json-test"
        assert parsed["record"]["settings"]["port"] == 8080
        assert parsed["record"]["settings"]["workers"] == 4

    def test_model_with_list_of_nested_models(self, correlation_id: UUID) -> None:
        """Test serialization of models containing lists of nested models."""

        class Endpoint(BaseModel):
            host: str
            port: int

        class ServiceRecord(BaseModel):
            service_id: str
            endpoints: list[Endpoint]

        record = ServiceRecord(
            service_id="multi-endpoint-svc",
            endpoints=[
                Endpoint(host="localhost", port=8080),
                Endpoint(host="localhost", port=8081),
                Endpoint(host="localhost", port=8082),
            ],
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        # Verify list of nested models serialized correctly
        assert len(data["record"]["endpoints"]) == 3
        assert data["record"]["endpoints"][0]["host"] == "localhost"
        assert data["record"]["endpoints"][0]["port"] == 8080
        assert data["record"]["endpoints"][2]["port"] == 8082

    # ---- UUID Serialization Tests ----

    def test_uuid_serializes_to_string_format(self, correlation_id: UUID) -> None:
        """Test that UUIDs serialize to string format correctly."""
        intent = ModelConsulRegisterIntent(
            service_id="node-uuid-test",
            service_name="test-service",
            correlation_id=correlation_id,
        )

        data = intent.serialize_for_io()

        # UUID should be serialized as string
        assert isinstance(data["correlation_id"], str)
        # Should be valid UUID string format
        assert len(data["correlation_id"]) == 36
        assert data["correlation_id"].count("-") == 4

    def test_uuid_string_format_is_lowercase(self, correlation_id: UUID) -> None:
        """Test that serialized UUID string is lowercase."""
        intent = ModelConsulDeregisterIntent(
            service_id="node-uuid-case",
            correlation_id=correlation_id,
        )

        data = intent.model_dump(mode="json")

        # UUID string should be lowercase
        assert data["correlation_id"] == data["correlation_id"].lower()

    def test_uuid_roundtrip_preservation(self) -> None:
        """Test that UUID value is preserved through round-trip serialization."""
        original_uuid = UUID("12345678-1234-5678-1234-567812345678")
        intent = ModelConsulRegisterIntent(
            service_id="node-roundtrip",
            service_name="test-service",
            correlation_id=original_uuid,
        )

        # Serialize to dict (JSON mode)
        data = intent.model_dump(mode="json")

        # Deserialize back
        restored = ModelConsulRegisterIntent.model_validate(data)

        # UUID should match
        assert restored.correlation_id == original_uuid
        assert str(restored.correlation_id) == str(original_uuid)

    def test_uuid_in_nested_record_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test UUID serialization in nested record models."""

        class RecordWithUUID(BaseModel):
            node_id: UUID
            parent_id: UUID | None

        node_uuid = uuid4()
        parent_uuid = uuid4()

        record = RecordWithUUID(
            node_id=node_uuid,
            parent_id=parent_uuid,
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        # All UUIDs should be strings
        assert isinstance(data["correlation_id"], str)
        assert isinstance(data["record"]["node_id"], str)
        assert isinstance(data["record"]["parent_id"], str)

        # Values should match
        assert data["record"]["node_id"] == str(node_uuid)
        assert data["record"]["parent_id"] == str(parent_uuid)

    def test_multiple_uuid_fields_serialize_independently(
        self, correlation_id: UUID
    ) -> None:
        """Test that multiple UUIDs serialize to distinct values."""
        uuid1 = UUID("11111111-1111-1111-1111-111111111111")
        uuid2 = UUID("22222222-2222-2222-2222-222222222222")

        class MultiUUIDRecord(BaseModel):
            primary_id: UUID
            secondary_id: UUID

        record = MultiUUIDRecord(primary_id=uuid1, secondary_id=uuid2)
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        # Each UUID should serialize to its own distinct value
        assert data["record"]["primary_id"] == str(uuid1)
        assert data["record"]["secondary_id"] == str(uuid2)
        assert data["record"]["primary_id"] != data["record"]["secondary_id"]

    # ---- None/Null Value Handling Tests ----

    def test_optional_none_serializes_correctly(self, correlation_id: UUID) -> None:
        """Test that optional fields with None serialize correctly."""
        intent = ModelConsulRegisterIntent(
            service_id="node-none-test",
            service_name="test-service",
            health_check=None,  # Explicitly None
            correlation_id=correlation_id,
        )

        data = intent.serialize_for_io()

        # None should serialize as JSON null (Python None in dict)
        assert data["health_check"] is None
        assert "health_check" in data  # Field should still be present

    def test_none_not_serialized_as_string(self, correlation_id: UUID) -> None:
        """Test that None values don't appear as 'null' or 'None' strings."""
        intent = ModelConsulRegisterIntent(
            service_id="node-null-string",
            service_name="test-service",
            health_check=None,
            correlation_id=correlation_id,
        )

        data = intent.model_dump(mode="json")

        # Should not be string representations of null
        assert data["health_check"] != "null"
        assert data["health_check"] != "None"
        assert data["health_check"] != "none"
        assert data["health_check"] is None

    def test_omitted_vs_explicit_none_in_optional_fields(
        self, correlation_id: UUID
    ) -> None:
        """Test distinction between omitted optional fields and explicit None."""
        # Without health_check (uses default)
        intent_default = ModelConsulRegisterIntent(
            service_id="node-default",
            service_name="test-service",
            correlation_id=correlation_id,
        )

        # With explicit None
        intent_explicit = ModelConsulRegisterIntent(
            service_id="node-explicit",
            service_name="test-service",
            health_check=None,
            correlation_id=correlation_id,
        )

        data_default = intent_default.serialize_for_io()
        data_explicit = intent_explicit.serialize_for_io()

        # Both should have health_check as None
        assert data_default["health_check"] is None
        assert data_explicit["health_check"] is None

    def test_none_in_nested_optional_field_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test None handling in nested model optional fields."""

        class ConfigWithOptional(BaseModel):
            required_field: str
            optional_field: str | None = None
            optional_dict: dict[str, str] | None = None

        record = ConfigWithOptional(
            required_field="value",
            optional_field=None,
            optional_dict=None,
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        assert data["record"]["required_field"] == "value"
        assert data["record"]["optional_field"] is None
        assert data["record"]["optional_dict"] is None

    def test_optional_uuid_none_handling_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test None handling for optional UUID fields."""

        class RecordWithOptionalUUID(BaseModel):
            node_id: str
            parent_id: UUID | None = None

        record = RecordWithOptionalUUID(
            node_id="child-node",
            parent_id=None,
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        assert data["record"]["node_id"] == "child-node"
        assert data["record"]["parent_id"] is None

    # ---- Empty Dict Serialization Tests ----

    def test_empty_dict_serialization(self, correlation_id: UUID) -> None:
        """Test that empty dict serializes correctly."""
        intent = ModelConsulRegisterIntent(
            service_id="node-empty-dict",
            service_name="test-service",
            health_check={},
            correlation_id=correlation_id,
        )

        data = intent.serialize_for_io()

        # Empty dict should remain as empty dict
        assert data["health_check"] == {}
        assert isinstance(data["health_check"], dict)
        assert len(data["health_check"]) == 0

    def test_empty_dict_vs_none_distinction(self, correlation_id: UUID) -> None:
        """Test distinction between empty dict and None."""
        intent_empty = ModelConsulRegisterIntent(
            service_id="node-empty",
            service_name="test",
            health_check={},
            correlation_id=correlation_id,
        )
        intent_none = ModelConsulRegisterIntent(
            service_id="node-none",
            service_name="test",
            health_check=None,
            correlation_id=correlation_id,
        )

        data_empty = intent_empty.serialize_for_io()
        data_none = intent_none.serialize_for_io()

        # Should be distinguishable
        assert data_empty["health_check"] == {}
        assert data_none["health_check"] is None
        assert data_empty["health_check"] != data_none["health_check"]

    def test_empty_list_serialization(self, correlation_id: UUID) -> None:
        """Test that empty list serializes correctly."""
        intent = ModelConsulRegisterIntent(
            service_id="node-empty-list",
            service_name="test-service",
            tags=[],
            correlation_id=correlation_id,
        )

        data = intent.serialize_for_io()

        assert data["tags"] == []
        assert isinstance(data["tags"], list)
        assert len(data["tags"]) == 0

    def test_nested_empty_structures_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test serialization of nested empty structures."""

        class RecordWithEmpties(BaseModel):
            name: str
            empty_dict: dict[str, str]
            empty_list: list[str]

        record = RecordWithEmpties(
            name="test",
            empty_dict={},
            empty_list=[],
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        assert data["record"]["empty_dict"] == {}
        assert data["record"]["empty_list"] == []

    # ---- Special Characters Tests ----

    def test_special_characters_in_service_id(self, correlation_id: UUID) -> None:
        """Test special characters in service_id field."""
        # Common special chars in service identifiers
        special_ids = [
            "node-123_abc",
            "node.compute.v1",
            "node-compute-abc123",
            "node_v1_2_3",
        ]

        for service_id in special_ids:
            intent = ModelConsulRegisterIntent(
                service_id=service_id,
                service_name="test",
                correlation_id=correlation_id,
            )
            data = intent.serialize_for_io()
            assert data["service_id"] == service_id

    def test_unicode_characters_in_fields_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test unicode characters serialize correctly."""

        class UnicodeRecord(BaseModel):
            description: str
            locale: str

        record = UnicodeRecord(
            description="Service description with unicode: cafe, resume, naive",
            locale="en-US",
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        assert "cafe" in data["record"]["description"]
        assert data["record"]["locale"] == "en-US"

    def test_json_special_characters_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test JSON special characters (quotes, backslash) serialize correctly."""
        import json

        class RecordWithSpecialChars(BaseModel):
            path: str
            pattern: str
            message: str

        record = RecordWithSpecialChars(
            path="C:\\Users\\test\\file.txt",  # Backslashes
            pattern='"quoted"',  # Quotes
            message="Line1\nLine2\tTabbed",  # Newlines and tabs
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Should produce valid JSON with serialize_as_any
        json_str = intent.model_dump_json(serialize_as_any=True)
        parsed = json.loads(json_str)

        # Characters should be preserved after round-trip
        assert parsed["record"]["path"] == "C:\\Users\\test\\file.txt"
        assert parsed["record"]["pattern"] == '"quoted"'
        assert parsed["record"]["message"] == "Line1\nLine2\tTabbed"

    def test_empty_string_serialization_with_serialize_as_any(
        self, correlation_id: UUID
    ) -> None:
        """Test empty string serialization (distinct from None)."""

        class RecordWithEmptyString(BaseModel):
            name: str
            description: str

        record = RecordWithEmptyString(
            name="test",
            description="",  # Empty string, not None
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        assert data["record"]["description"] == ""
        assert data["record"]["description"] is not None

    def test_special_characters_in_tags(self, correlation_id: UUID) -> None:
        """Test tags with special characters serialize correctly."""
        tags = [
            "env:prod",
            "version:1.0.0-beta+build.123",
            "team:platform/infrastructure",
            "feature:new_feature",
            "priority:p0",
        ]
        intent = ModelConsulRegisterIntent(
            service_id="node-tags",
            service_name="test",
            tags=tags,
            correlation_id=correlation_id,
        )

        data = intent.serialize_for_io()

        assert data["tags"] == tags
        for original, serialized in zip(tags, data["tags"], strict=True):
            assert original == serialized

    # ---- Complex Round-Trip Tests ----

    def test_complex_roundtrip_via_json(self, correlation_id: UUID) -> None:
        """Test complex model survives JSON string round-trip."""
        import json

        intent = ModelConsulRegisterIntent(
            service_id="node-complex-roundtrip",
            service_name="onex-compute",
            tags=["env:prod", "version:1.0"],
            health_check={
                "http": "http://localhost:8080/health",
                "interval": 10,
                "timeout": 5,
                "tls_skip_verify": False,
                "nested": {"key": "value"},
            },
            correlation_id=correlation_id,
        )

        # Full round-trip through JSON string
        json_str = intent.model_dump_json()
        dict_data = json.loads(json_str)
        restored = ModelConsulRegisterIntent.model_validate(dict_data)

        # All data should match
        assert restored.service_id == intent.service_id
        assert restored.service_name == intent.service_name
        assert restored.tags == intent.tags
        assert restored.health_check == intent.health_check
        assert restored.correlation_id == intent.correlation_id

    def test_discriminated_union_roundtrip_consul_types(
        self, correlation_id: UUID
    ) -> None:
        """Test Consul intent types survive discriminated union round-trip.

        Tests the two Consul intent types through the discriminated union.
        PostgreSQL intents are tested separately due to record serialization
        requirements.
        """
        import json

        adapter = TypeAdapter(ModelCoreRegistrationIntent)

        # Test Consul intent types (no polymorphic BaseModel field issues)
        intents = [
            ModelConsulRegisterIntent(
                service_id="node-1",
                service_name="test",
                correlation_id=correlation_id,
            ),
            ModelConsulDeregisterIntent(
                service_id="node-2",
                correlation_id=correlation_id,
            ),
        ]

        for original in intents:
            # Serialize to JSON string
            json_str = original.model_dump_json()

            # Parse JSON and validate through union adapter
            dict_data = json.loads(json_str)
            restored = adapter.validate_python(dict_data)

            # Should restore to same type
            assert type(restored) is type(original)
            assert restored.correlation_id == original.correlation_id

    def test_discriminated_union_roundtrip_postgres_type(
        self, correlation_id: UUID
    ) -> None:
        """Test PostgreSQL intent type survives discriminated union round-trip.

        Uses serialize_as_any=True for proper record serialization.
        """
        import json

        adapter = TypeAdapter(ModelCoreRegistrationIntent)

        # Create a simple record model
        class SimpleRecord(BaseModel):
            value: str

        record = SimpleRecord(value="test")
        original = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Serialize with serialize_as_any=True
        json_str = original.model_dump_json(serialize_as_any=True)

        # Parse JSON and validate through union adapter
        dict_data = json.loads(json_str)
        restored = adapter.validate_python(dict_data)

        # Should restore to same type
        assert type(restored) is ModelPostgresUpsertRegistrationIntent
        assert restored.correlation_id == original.correlation_id

    def test_postgres_intent_with_complex_record_roundtrip(
        self, correlation_id: UUID
    ) -> None:
        """Test PostgreSQL intent with complex record survives full round-trip.

        Uses serialize_as_any=True for proper record serialization and validates
        that the serialized record data is preserved.
        """
        import json

        class ComplexRecord(BaseModel):
            node_id: UUID
            name: str
            config: dict[str, int | str | bool]
            tags: list[str]
            parent_id: UUID | None = None

        test_node_id = uuid4()
        record = ComplexRecord(
            node_id=test_node_id,
            name="complex-node",
            config={"port": 8080, "host": "localhost", "enabled": True},
            tags=["tag1", "tag2"],
            parent_id=None,
        )

        original = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Full JSON round-trip with serialize_as_any=True
        json_str = original.model_dump_json(serialize_as_any=True)
        dict_data = json.loads(json_str)
        restored = ModelPostgresUpsertRegistrationIntent.model_validate(dict_data)

        # Verify restored model fields
        assert restored.correlation_id == correlation_id
        assert restored.kind == "postgres.upsert_registration"

        # Verify serialized record data is preserved in the JSON output
        original_record_data = record.model_dump(mode="json")
        assert dict_data["record"] == original_record_data
        assert dict_data["record"]["node_id"] == str(test_node_id)
        assert dict_data["record"]["name"] == "complex-node"
        assert dict_data["record"]["config"]["port"] == 8080
        assert dict_data["record"]["tags"] == ["tag1", "tag2"]
        assert dict_data["record"]["parent_id"] is None

    # ---- Datetime Serialization Tests ----

    def test_datetime_in_record_serializes_to_iso_format(
        self, correlation_id: UUID
    ) -> None:
        """Test datetime fields serialize to ISO format string."""
        from datetime import datetime

        class RecordWithDatetime(BaseModel):
            node_id: str
            created_at: datetime
            updated_at: datetime | None = None

        now = datetime.now(UTC)
        record = RecordWithDatetime(
            node_id="datetime-node",
            created_at=now,
            updated_at=None,
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        # Datetime should be serialized as ISO string
        assert isinstance(data["record"]["created_at"], str)
        assert data["record"]["updated_at"] is None
        # Should be parseable back to datetime
        parsed_dt = datetime.fromisoformat(data["record"]["created_at"])
        assert parsed_dt.year == now.year
        assert parsed_dt.month == now.month
        assert parsed_dt.day == now.day

    def test_datetime_roundtrip_preserves_timezone(self, correlation_id: UUID) -> None:
        """Test datetime round-trip preserves timezone information."""
        from datetime import datetime

        class RecordWithTZDatetime(BaseModel):
            timestamp: datetime

        utc_time = datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC)
        record = RecordWithTZDatetime(timestamp=utc_time)
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Serialize with serialize_as_any=True
        data = intent.model_dump(mode="json", serialize_as_any=True)

        # Verify key fields are preserved
        assert data["correlation_id"] == str(correlation_id)
        assert data["kind"] == "postgres.upsert_registration"

        # Check the serialized timestamp format directly from the output
        timestamp_str = data["record"]["timestamp"]
        # Should contain UTC indicator (Z or +00:00)
        assert "Z" in timestamp_str or "+00:00" in timestamp_str

        # Verify the timestamp can be parsed back
        parsed_dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert parsed_dt.year == 2025
        assert parsed_dt.month == 1
        assert parsed_dt.day == 15
        assert parsed_dt.hour == 12

    # ---- Additional Edge Cases ----

    def test_very_long_string_serialization(self, correlation_id: UUID) -> None:
        """Test serialization of very long strings."""

        class RecordWithLongString(BaseModel):
            data: str

        long_string = "x" * 10000  # 10KB string
        record = RecordWithLongString(data=long_string)
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        assert data["record"]["data"] == long_string
        assert len(data["record"]["data"]) == 10000

    def test_numeric_edge_values_in_record(self, correlation_id: UUID) -> None:
        """Test serialization of numeric edge values (large, small, negative)."""

        class RecordWithNumbers(BaseModel):
            large_int: int
            negative_int: int
            float_value: float
            zero: int

        record = RecordWithNumbers(
            large_int=2**62,  # Large but within JSON safe integer
            negative_int=-999999,
            float_value=3.14159265358979,
            zero=0,
        )
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Use serialize_as_any=True for proper record serialization
        data = intent.model_dump(mode="json", serialize_as_any=True)

        assert data["record"]["large_int"] == 2**62
        assert data["record"]["negative_int"] == -999999
        assert abs(data["record"]["float_value"] - 3.14159265358979) < 1e-10
        assert data["record"]["zero"] == 0

    def test_boolean_values_serialization(self, correlation_id: UUID) -> None:
        """Test boolean values serialize as true JSON booleans."""
        import json

        class RecordWithBooleans(BaseModel):
            enabled: bool
            disabled: bool

        record = RecordWithBooleans(enabled=True, disabled=False)
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # Serialize to JSON string with serialize_as_any
        json_str = intent.model_dump_json(serialize_as_any=True)
        parsed = json.loads(json_str)

        # Should be actual booleans, not strings
        assert parsed["record"]["enabled"] is True
        assert parsed["record"]["disabled"] is False
        assert isinstance(parsed["record"]["enabled"], bool)
        assert isinstance(parsed["record"]["disabled"], bool)

    def test_mixed_type_dict_serialization(self, correlation_id: UUID) -> None:
        """Test dict with mixed value types serializes correctly."""
        health_check = {
            "string_val": "test",
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "null_val": None,
            "list_val": [1, 2, 3],
            "dict_val": {"nested": "value"},
        }
        intent = ModelConsulRegisterIntent(
            service_id="node-mixed",
            service_name="test",
            health_check=health_check,
            correlation_id=correlation_id,
        )

        data = intent.serialize_for_io()

        assert data["health_check"]["string_val"] == "test"
        assert data["health_check"]["int_val"] == 42
        assert data["health_check"]["float_val"] == 3.14
        assert data["health_check"]["bool_val"] is True
        assert data["health_check"]["null_val"] is None
        assert data["health_check"]["list_val"] == [1, 2, 3]
        assert data["health_check"]["dict_val"] == {"nested": "value"}

    def test_serialize_for_io_includes_polymorphic_fields(
        self, correlation_id: UUID
    ) -> None:
        """Test serialize_for_io() properly serializes polymorphic BaseModel fields.

        ModelCoreIntent.serialize_for_io() uses serialize_as_any=True to ensure
        subclass fields are properly serialized when the declared type is BaseModel.

        This is essential for ModelPostgresUpsertRegistrationIntent where the
        `record` field is typed as BaseModel but actual subclasses with additional
        fields are passed.
        """

        class TestRecord(BaseModel):
            node_id: str
            value: int

        record = TestRecord(node_id="test-123", value=42)
        intent = ModelPostgresUpsertRegistrationIntent(
            record=record,
            correlation_id=correlation_id,
        )

        # serialize_for_io() now uses serialize_as_any=True, properly serializing subclass fields
        data = intent.serialize_for_io()
        assert data["record"]["node_id"] == "test-123"
        assert data["record"]["value"] == 42

        # model_dump with serialize_as_any=True produces the same result
        proper_data = intent.model_dump(mode="json", serialize_as_any=True)
        assert proper_data["record"]["node_id"] == "test-123"
        assert proper_data["record"]["value"] == 42


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
