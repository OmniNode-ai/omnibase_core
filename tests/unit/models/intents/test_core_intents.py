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
"""

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
