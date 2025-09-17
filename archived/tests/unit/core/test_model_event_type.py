"""
Test suite for ModelEventType - ONEX compliance validation.

Tests the ONEX-compliant event type model with proper Pydantic validation patterns.
This replaces factory method anti-patterns with proper validation.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_event_type import (
    ModelEventType,
    create_event_type_from_registry,
    get_event_type_value,
    is_event_equal,
)
from omnibase_core.models.core.model_semver import ModelSemVer


class TestModelEventType:
    """Test ModelEventType with ONEX compliance patterns."""

    def test_direct_instantiation_success(self):
        """Test direct instantiation with proper validation."""
        event_type = ModelEventType(
            event_name="TEST_EVENT",
            namespace="test",
            description="Test event description",
            category="test",
            severity="info",
        )

        assert event_type.event_name == "TEST_EVENT"
        assert event_type.namespace == "test"
        assert event_type.description == "Test event description"
        assert event_type.category == "test"
        assert event_type.severity == "info"
        assert not event_type.deprecated
        assert isinstance(event_type.schema_version, ModelSemVer)

    def test_from_contract_data_validation(self):
        """Test ONEX-compliant factory method using model_validate."""
        event_type = ModelEventType.from_contract_data(
            event_name="CONTRACT_EVENT",
            namespace="contract",
            description="Contract event description",
            category="contract",
            severity="warning",
        )

        assert event_type.event_name == "CONTRACT_EVENT"
        assert event_type.namespace == "contract"
        assert event_type.description == "Contract event description"
        assert event_type.category == "contract"
        assert event_type.severity == "warning"

    def test_from_contract_data_default_description(self):
        """Test automatic description generation."""
        event_type = ModelEventType.from_contract_data(
            event_name="AUTO_DESC_EVENT",
            namespace="test",
        )

        assert event_type.description == "AUTO_DESC_EVENT event"

    def test_create_event_type_from_registry_success(self):
        """Test registry-based event type creation."""
        event_type = create_event_type_from_registry(
            event_name="REGISTRY_EVENT",
            namespace="registry",
            description="Registry event description",
        )

        assert event_type.event_name == "REGISTRY_EVENT"
        assert event_type.namespace == "registry"
        assert event_type.description == "Registry event description"

    def test_create_event_type_from_registry_default_description(self):
        """Test automatic description in registry creation."""
        event_type = create_event_type_from_registry(
            event_name="DEFAULT_DESC_EVENT",
            namespace="test",
        )

        assert event_type.description == "Registry event type: DEFAULT_DESC_EVENT"

    def test_validation_error_invalid_event_name(self):
        """Test validation error for invalid event name pattern."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventType(
                event_name="invalid_event_name",  # Must be uppercase
                description="Test description",
            )

        assert "String should match pattern" in str(exc_info.value)

    def test_validation_error_invalid_severity(self):
        """Test validation error for invalid severity level."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventType(
                event_name="TEST_EVENT",
                description="Test description",
                severity="invalid",  # Must match pattern
            )

        assert "String should match pattern" in str(exc_info.value)

    def test_qualified_name_property(self):
        """Test qualified name property."""
        event_type = ModelEventType(
            event_name="QUALIFIED_EVENT",
            namespace="test",
            description="Test description",
        )

        assert event_type.qualified_name == "test:QUALIFIED_EVENT"

    def test_matches_method(self):
        """Test event name matching."""
        event_type = ModelEventType(
            event_name="MATCH_EVENT", description="Test description"
        )

        assert event_type.matches("MATCH_EVENT")
        assert not event_type.matches("OTHER_EVENT")

    def test_is_compatible_with_method(self):
        """Test compatibility checking between event types."""
        event_type1 = ModelEventType(
            event_name="COMPAT_EVENT",
            namespace="test",
            description="Test description",
        )

        event_type2 = ModelEventType(
            event_name="COMPAT_EVENT",
            namespace="test",
            description="Different description",
        )

        event_type3 = ModelEventType(
            event_name="OTHER_EVENT",
            namespace="test",
            description="Other description",
        )

        # Test compatibility with same event name and namespace
        # Note: is_compatible_with method checks schema_version compatibility
        # which requires matching event names and namespaces
        assert event_type1.is_compatible_with(event_type2)  # Same name and namespace
        assert not event_type1.is_compatible_with(event_type3)  # Different name

    def test_string_representation(self):
        """Test string representation methods."""
        event_type = ModelEventType(
            event_name="STR_EVENT",
            description="Test description",
        )

        assert str(event_type) == "STR_EVENT"
        assert event_type == "STR_EVENT"  # String equality
        assert event_type != "OTHER_EVENT"

    def test_get_event_type_value_function(self):
        """Test utility function for getting event type values."""
        event_type = ModelEventType(
            event_name="VALUE_EVENT",
            description="Test description",
        )

        # Test with ModelEventType
        assert get_event_type_value(event_type) == "VALUE_EVENT"

        # Test with string
        assert get_event_type_value("STRING_EVENT") == "STRING_EVENT"

    def test_is_event_equal_function(self):
        """Test utility function for event equality comparison."""
        event_type = ModelEventType(
            event_name="EQUAL_EVENT",
            description="Test description",
        )

        # Test ModelEventType vs string
        assert is_event_equal(event_type, "EQUAL_EVENT")
        assert is_event_equal("EQUAL_EVENT", event_type)

        # Test string vs string
        assert is_event_equal("EQUAL_EVENT", "EQUAL_EVENT")
        assert not is_event_equal("EQUAL_EVENT", "OTHER_EVENT")

        # Test ModelEventType vs ModelEventType
        other_event = ModelEventType(
            event_name="EQUAL_EVENT", description="Other description"
        )
        assert is_event_equal(event_type, other_event)

    def test_payload_schema_optional(self):
        """Test optional payload schema field."""
        event_type = ModelEventType(
            event_name="SCHEMA_EVENT",
            description="Test description",
            payload_schema={
                "type": "object",
                "properties": {"data": {"type": "string"}},
            },
        )

        assert event_type.payload_schema is not None
        assert event_type.payload_schema["type"] == "object"

    def test_deprecated_flag(self):
        """Test deprecated flag functionality."""
        event_type = ModelEventType(
            event_name="DEPRECATED_EVENT",
            description="Deprecated event",
            deprecated=True,
        )

        assert event_type.deprecated is True

    def test_model_dump_serialization(self):
        """Test ONEX-compliant serialization using model_dump."""
        event_type = ModelEventType(
            event_name="SERIALIZATION_EVENT",
            namespace="test",
            description="Serialization test",
            category="test",
            severity="info",
        )

        # Use ONEX-compliant serialization
        serialized = event_type.model_dump()

        assert serialized["event_name"] == "SERIALIZATION_EVENT"
        assert serialized["namespace"] == "test"
        assert serialized["description"] == "Serialization test"
        assert isinstance(serialized["schema_version"], dict)

    def test_model_validate_deserialization(self):
        """Test ONEX-compliant deserialization using model_validate."""
        data = {
            "event_name": "DESERIALIZATION_EVENT",
            "namespace": "test",
            "description": "Deserialization test",
            "category": "test",
            "severity": "error",
        }

        # Use ONEX-compliant deserialization
        event_type = ModelEventType.model_validate(data)

        assert event_type.event_name == "DESERIALIZATION_EVENT"
        assert event_type.namespace == "test"
        assert event_type.severity == "error"

    def test_round_trip_consistency(self):
        """Test round-trip serialization/deserialization consistency."""
        original = ModelEventType(
            event_name="ROUND_TRIP_EVENT",
            namespace="test",
            description="Round-trip test",
            category="test",
            severity="warning",
            deprecated=True,
        )

        # Serialize using ONEX patterns
        serialized = original.model_dump()

        # Deserialize using ONEX patterns
        deserialized = ModelEventType.model_validate(serialized)

        assert deserialized.event_name == original.event_name
        assert deserialized.namespace == original.namespace
        assert deserialized.description == original.description
        assert deserialized.category == original.category
        assert deserialized.severity == original.severity
        assert deserialized.deprecated == original.deprecated

    def test_pydantic_validation_patterns(self):
        """Test that all validation goes through Pydantic."""
        # Test validation with missing required field
        with pytest.raises(ValidationError):
            ModelEventType()  # Missing event_name and description

        # Test validation with wrong type
        with pytest.raises(ValidationError):
            ModelEventType(
                event_name=123,  # Should be string
                description="Test",
            )

    def test_onex_compliance_no_factory_methods(self):
        """Verify that old factory methods are removed/replaced."""
        event_type = ModelEventType(
            event_name="COMPLIANCE_TEST",
            description="ONEX compliance test",
        )

        # Verify new ONEX-compliant method exists
        assert hasattr(ModelEventType, "from_contract_data")

        # Verify it uses model_validate internally (test indirectly)
        contract_event = ModelEventType.from_contract_data(
            event_name="CONTRACT_COMPLIANCE",
            description="Contract compliance test",
        )
        assert isinstance(contract_event, ModelEventType)
        assert contract_event.event_name == "CONTRACT_COMPLIANCE"
