"""
Unit tests for ProtocolRegistrationRecord.

Tests verify:
- Protocol is runtime_checkable
- Protocol defines required methods (to_persistence_dict, model_dump)
- Pydantic models can implement the protocol
- Custom classes can implement the protocol
- isinstance checks work correctly

Timeout Protection:
- All test classes use @pytest.mark.timeout(5) for unit tests
- These are pure protocol tests with no I/O
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.models.intents import ModelRegistrationRecordBase
from omnibase_core.protocols.intents import ProtocolRegistrationRecord

# ---- Test Fixtures ----


class SamplePydanticRecord(BaseModel):
    """Sample Pydantic model implementing ProtocolRegistrationRecord."""

    node_id: str
    record_type: str  # Named 'record_type' to avoid YAML validation hook false positive
    status: str

    def to_persistence_dict(self) -> dict[str, object]:
        """Serialize for database persistence."""
        return self.model_dump(mode="json")


class SampleCustomRecord:
    """Sample non-Pydantic class implementing ProtocolRegistrationRecord."""

    def __init__(self, node_id: str, status: str) -> None:
        self._node_id = node_id
        self._status = status

    def to_persistence_dict(self) -> dict[str, object]:
        """Serialize for database persistence."""
        return {"node_id": self._node_id, "status": self._status}

    def model_dump(
        self,
        *,
        mode: str = "python",
        include: Any = None,
        exclude: Any = None,
        context: Any = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | str = True,
        serialize_as_any: bool = False,
    ) -> dict[str, Any]:
        """Standard Pydantic-compatible serialization."""
        return self.to_persistence_dict()


class InheritedRecord(ModelRegistrationRecordBase):
    """Sample record inheriting from ModelRegistrationRecordBase."""

    service_id: str
    endpoint_url: str
    is_active: bool = True


class IncompleteRecord:
    """Class that does NOT implement the protocol (missing methods)."""

    def __init__(self, data: str) -> None:
        self.data = data


# ---- Test Protocol Definition ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestProtocolDefinition:
    """Tests for ProtocolRegistrationRecord definition."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that protocol is decorated with @runtime_checkable."""
        # Should be able to use isinstance() with the protocol
        record = SamplePydanticRecord(
            node_id="123", record_type="compute", status="active"
        )
        # This should not raise - protocol is runtime_checkable
        result = isinstance(record, ProtocolRegistrationRecord)
        assert result is True

    def test_protocol_has_to_persistence_dict_method(self) -> None:
        """Test that protocol defines to_persistence_dict method."""
        # Check that the method is defined in the protocol
        assert hasattr(ProtocolRegistrationRecord, "to_persistence_dict")

    def test_protocol_has_model_dump_method(self) -> None:
        """Test that protocol defines model_dump method."""
        assert hasattr(ProtocolRegistrationRecord, "model_dump")


# ---- Test Pydantic Implementation ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestPydanticImplementation:
    """Tests for Pydantic model implementations."""

    def test_pydantic_model_implements_protocol(self) -> None:
        """Test that Pydantic model with to_persistence_dict implements protocol."""
        record = SamplePydanticRecord(
            node_id="node-123", record_type="compute", status="active"
        )
        assert isinstance(record, ProtocolRegistrationRecord)

    def test_pydantic_to_persistence_dict(self) -> None:
        """Test to_persistence_dict returns correct data."""
        record = SamplePydanticRecord(
            node_id="node-456", record_type="effect", status="initializing"
        )
        data = record.to_persistence_dict()

        assert data["node_id"] == "node-456"
        assert data["record_type"] == "effect"
        assert data["status"] == "initializing"

    def test_pydantic_model_dump_json_mode(self) -> None:
        """Test model_dump with mode='json' returns serializable data."""
        record = SamplePydanticRecord(
            node_id="node-789", record_type="reducer", status="ready"
        )
        data = record.model_dump(mode="json")

        assert isinstance(data, dict)
        assert data["node_id"] == "node-789"

    def test_pydantic_with_uuid_field(self) -> None:
        """Test Pydantic model with UUID field serializes correctly."""

        class RecordWithUUID(BaseModel):
            record_id: UUID
            name: str

            def to_persistence_dict(self) -> dict[str, object]:
                return self.model_dump(mode="json")

        test_uuid = uuid4()
        record = RecordWithUUID(record_id=test_uuid, name="test")
        data = record.to_persistence_dict()

        # UUID should be serialized as string
        assert data["record_id"] == str(test_uuid)
        assert isinstance(data["record_id"], str)


# ---- Test Custom Class Implementation ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestCustomImplementation:
    """Tests for custom (non-Pydantic) implementations."""

    def test_custom_class_implements_protocol(self) -> None:
        """Test that custom class with required methods implements protocol."""
        record = SampleCustomRecord(node_id="custom-123", status="active")
        assert isinstance(record, ProtocolRegistrationRecord)

    def test_custom_to_persistence_dict(self) -> None:
        """Test custom implementation to_persistence_dict."""
        record = SampleCustomRecord(node_id="custom-456", status="pending")
        data = record.to_persistence_dict()

        assert data["node_id"] == "custom-456"
        assert data["status"] == "pending"

    def test_custom_model_dump(self) -> None:
        """Test custom implementation model_dump."""
        record = SampleCustomRecord(node_id="custom-789", status="completed")
        data = record.model_dump()

        assert data["node_id"] == "custom-789"
        assert data["status"] == "completed"

    def test_incomplete_class_does_not_implement_protocol(self) -> None:
        """Test that incomplete class does NOT implement protocol."""
        record = IncompleteRecord(data="test")
        # Should NOT be an instance since it's missing required methods
        assert not isinstance(record, ProtocolRegistrationRecord)


# ---- Test ModelRegistrationRecordBase ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelRegistrationRecordBase:
    """Tests for ModelRegistrationRecordBase convenience class."""

    def test_base_class_implements_protocol(self) -> None:
        """Test that ModelRegistrationRecordBase implements protocol."""
        record = InheritedRecord(
            service_id="svc-123",
            endpoint_url="http://localhost:8080",
        )
        assert isinstance(record, ProtocolRegistrationRecord)

    def test_inherited_to_persistence_dict(self) -> None:
        """Test inherited to_persistence_dict method."""
        record = InheritedRecord(
            service_id="svc-456",
            endpoint_url="http://api.local:9000",
            is_active=False,
        )
        data = record.to_persistence_dict()

        assert data["service_id"] == "svc-456"
        assert data["endpoint_url"] == "http://api.local:9000"
        assert data["is_active"] is False

    def test_base_class_is_frozen(self) -> None:
        """Test that base class produces frozen (immutable) instances."""
        from pydantic import ValidationError

        record = InheritedRecord(
            service_id="svc-789",
            endpoint_url="http://test.local",
        )
        # Should raise on attempt to modify
        with pytest.raises(ValidationError, match="frozen"):
            record.service_id = "changed"  # type: ignore[misc]

    def test_base_class_forbids_extra_fields(self) -> None:
        """Test that base class forbids extra fields."""
        with pytest.raises(Exception):  # ValidationError for extra fields
            InheritedRecord(
                service_id="svc",
                endpoint_url="http://test",
                unknown_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_base_class_from_attributes(self) -> None:
        """Test from_attributes=True enables attribute-based construction."""

        class RecordLike:
            service_id = "attr-svc"
            endpoint_url = "http://attr.local"
            is_active = True

        # Should be able to validate from object with attributes
        record = InheritedRecord.model_validate(RecordLike())
        assert record.service_id == "attr-svc"
        assert record.endpoint_url == "http://attr.local"


# ---- Test Protocol Type Annotations ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestProtocolTypeAnnotations:
    """Tests for using protocol in type annotations."""

    def test_function_accepting_protocol(self) -> None:
        """Test function can accept protocol-typed parameter."""

        def process_record(record: ProtocolRegistrationRecord) -> dict[str, object]:
            return record.to_persistence_dict()

        # Pydantic implementation
        pydantic_record = SamplePydanticRecord(
            node_id="test", record_type="compute", status="active"
        )
        result = process_record(pydantic_record)
        assert result["node_id"] == "test"

        # Custom implementation
        custom_record = SampleCustomRecord(node_id="custom", status="ready")
        result = process_record(custom_record)
        assert result["node_id"] == "custom"

        # Base class implementation
        base_record = InheritedRecord(
            service_id="base",
            endpoint_url="http://base.local",
        )
        result = process_record(base_record)
        assert result["service_id"] == "base"

    def test_list_of_protocol_instances(self) -> None:
        """Test list can contain different protocol implementations."""
        records: list[ProtocolRegistrationRecord] = [
            SamplePydanticRecord(
                node_id="pydantic", record_type="compute", status="active"
            ),
            SampleCustomRecord(node_id="custom", status="ready"),
            InheritedRecord(
                service_id="inherited",
                endpoint_url="http://inherited.local",
            ),
        ]

        # All should serialize correctly
        for record in records:
            data = record.to_persistence_dict()
            assert isinstance(data, dict)


# ---- Test Edge Cases ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_record(self) -> None:
        """Test empty record (no fields beyond required methods)."""

        class EmptyRecord(ModelRegistrationRecordBase):
            pass

        record = EmptyRecord()
        data = record.to_persistence_dict()
        assert data == {}

    def test_nested_record(self) -> None:
        """Test record with nested Pydantic model."""

        class InnerConfig(BaseModel):
            timeout: int
            retries: int

        class NestedRecord(ModelRegistrationRecordBase):
            name: str
            config: InnerConfig

        record = NestedRecord(
            name="nested",
            config=InnerConfig(timeout=30, retries=3),
        )
        data = record.to_persistence_dict()

        assert data["name"] == "nested"
        assert data["config"]["timeout"] == 30
        assert data["config"]["retries"] == 3

    def test_record_with_optional_fields(self) -> None:
        """Test record with optional fields."""

        class OptionalRecord(ModelRegistrationRecordBase):
            required_field: str
            optional_field: str | None = None

        # With optional field set
        record_with = OptionalRecord(
            required_field="value",
            optional_field="optional",
        )
        data_with = record_with.to_persistence_dict()
        assert data_with["optional_field"] == "optional"

        # With optional field as None
        record_without = OptionalRecord(required_field="value")
        data_without = record_without.to_persistence_dict()
        assert data_without["optional_field"] is None

    def test_record_with_list_field(self) -> None:
        """Test record with list field."""

        class ListRecord(ModelRegistrationRecordBase):
            name: str
            tags: list[str]

        record = ListRecord(name="tagged", tags=["tag1", "tag2", "tag3"])
        data = record.to_persistence_dict()

        assert data["tags"] == ["tag1", "tag2", "tag3"]
        assert len(data["tags"]) == 3

    def test_record_with_dict_field(self) -> None:
        """Test record with dict field."""

        class DictRecord(ModelRegistrationRecordBase):
            name: str
            metadata: dict[str, str]

        record = DictRecord(
            name="metadata-record",
            metadata={"key1": "value1", "key2": "value2"},
        )
        data = record.to_persistence_dict()

        assert data["metadata"]["key1"] == "value1"
        assert data["metadata"]["key2"] == "value2"
