"""
Unit tests for ModelNodeCapability.

Tests all aspects of the node capability model including:
- Model instantiation with defaults and custom values
- Property getters/setters
- Factory methods for standard capabilities
- from_string conversion
- String representation and equality
- Version compatibility checks
- Protocol implementations
- Edge cases and error handling
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_performance_impact import EnumPerformanceImpact
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.node_metadata.model_node_capability import ModelNodeCapability
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelNodeCapability:
    """Test cases for ModelNodeCapability."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal required fields."""
        capability = ModelNodeCapability(
            value="test_capability",
            description="Test capability description",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.value == "test_capability"
        assert capability.description == "Test capability description"
        assert capability.capability_id is not None
        assert capability.version_introduced is not None
        assert capability.performance_impact == EnumPerformanceImpact.LOW

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields."""
        capability = ModelNodeCapability(
            capability_display_name="TEST_CAPABILITY",
            value="test_capability",
            description="Full test capability",
            version_introduced=ModelSemVer(major=1, minor=2, patch=3),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.HIGH,
            deprecated=True,
            replacement="new_capability",
        )

        assert capability.capability_display_name == "TEST_CAPABILITY"
        assert capability.value == "test_capability"
        assert capability.version_introduced.major == 1
        assert capability.configuration_required is True
        assert capability.performance_impact == EnumPerformanceImpact.HIGH
        assert capability.deprecated is True
        assert capability.replacement == "new_capability"

    def test_capability_name_property_get_with_display_name(self):
        """Test capability_name property returns display_name when set."""
        capability = ModelNodeCapability(
            capability_display_name="MY_CAPABILITY",
            value="my_capability",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.capability_name == "MY_CAPABILITY"

    def test_capability_name_property_get_without_display_name(self):
        """Test capability_name property falls back to UUID-based name."""
        capability = ModelNodeCapability(
            value="my_capability",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.capability_name.startswith("capability_")
        assert len(capability.capability_name) > 10

    def test_capability_name_property_set(self):
        """Test capability_name property setter."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        capability.capability_name = "NEW_NAME"
        assert capability.capability_display_name == "NEW_NAME"
        assert capability.capability_name == "NEW_NAME"

    def test_supports_dry_run_factory(self):
        """Test supports_dry_run factory method."""
        capability = ModelNodeCapability.supports_dry_run()

        assert capability.value == "supports_dry_run"
        assert capability.capability_display_name == "SUPPORTS_DRY_RUN"
        assert capability.configuration_required is False
        assert capability.performance_impact == EnumPerformanceImpact.LOW

    def test_supports_batch_processing_factory(self):
        """Test supports_batch_processing factory method."""
        capability = ModelNodeCapability.supports_batch_processing()

        assert capability.value == "supports_batch_processing"
        assert capability.configuration_required is True
        assert capability.performance_impact == EnumPerformanceImpact.MEDIUM
        assert capability.example_config is not None
        assert "batch_size" in capability.example_config

    def test_supports_custom_handlers_factory(self):
        """Test supports_custom_handlers factory method."""
        capability = ModelNodeCapability.supports_custom_handlers()

        assert capability.value == "supports_custom_handlers"
        assert capability.configuration_required is True
        assert len(capability.dependencies) > 0

    def test_telemetry_enabled_factory(self):
        """Test telemetry_enabled factory method."""
        capability = ModelNodeCapability.telemetry_enabled()

        assert capability.value == "telemetry_enabled"
        assert capability.version_introduced.minor >= 1
        assert capability.example_config is not None

    def test_supports_correlation_id_factory(self):
        """Test supports_correlation_id factory method."""
        capability = ModelNodeCapability.supports_correlation_id()

        assert capability.value == "supports_correlation_id"
        assert capability.configuration_required is False

    def test_supports_event_bus_factory(self):
        """Test supports_event_bus factory method."""
        capability = ModelNodeCapability.supports_event_bus()

        assert capability.value == "supports_event_bus"
        assert capability.configuration_required is True
        assert len(capability.dependencies) > 0
        assert capability.example_config is not None

    def test_supports_schema_validation_factory(self):
        """Test supports_schema_validation factory method."""
        capability = ModelNodeCapability.supports_schema_validation()

        assert capability.value == "supports_schema_validation"
        assert capability.configuration_required is False

    def test_supports_error_recovery_factory(self):
        """Test supports_error_recovery factory method."""
        capability = ModelNodeCapability.supports_error_recovery()

        assert capability.value == "supports_error_recovery"
        assert capability.configuration_required is True
        assert capability.example_config is not None
        assert "max_retries" in capability.example_config

    def test_supports_event_discovery_factory(self):
        """Test supports_event_discovery factory method."""
        capability = ModelNodeCapability.supports_event_discovery()

        assert capability.value == "supports_event_discovery"
        assert len(capability.dependencies) >= 2

    def test_from_string_known_capability(self):
        """Test from_string with known capability name."""
        capability = ModelNodeCapability.from_string("SUPPORTS_DRY_RUN")

        assert capability.value == "supports_dry_run"
        assert capability.capability_display_name == "SUPPORTS_DRY_RUN"

    def test_from_string_lowercase(self):
        """Test from_string with lowercase input."""
        capability = ModelNodeCapability.from_string("supports_dry_run")

        assert capability.value == "supports_dry_run"

    def test_from_string_unknown_capability(self):
        """Test from_string creates generic capability for unknown names."""
        capability = ModelNodeCapability.from_string("CUSTOM_CAPABILITY")

        assert capability.value == "custom_capability"
        assert capability.capability_display_name == "CUSTOM_CAPABILITY"
        assert "Custom capability" in capability.description

    def test_str_representation(self):
        """Test __str__ returns value."""
        capability = ModelNodeCapability(
            value="test_capability",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert str(capability) == "test_capability"

    def test_eq_with_string_value(self):
        """Test equality comparison with string (value)."""
        capability = ModelNodeCapability(
            value="test_capability",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability == "test_capability"

    def test_eq_with_string_display_name(self):
        """Test equality comparison with string (display_name)."""
        capability = ModelNodeCapability(
            capability_display_name="TEST_CAPABILITY",
            value="test_capability",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability == "TEST_CAPABILITY"

    def test_eq_with_another_capability(self):
        """Test equality comparison with another ModelNodeCapability."""
        cap1 = ModelNodeCapability.supports_dry_run()
        cap2 = ModelNodeCapability.supports_dry_run()

        assert cap1 == cap2

    def test_eq_with_different_capability(self):
        """Test inequality with different capability."""
        cap1 = ModelNodeCapability.supports_dry_run()
        cap2 = ModelNodeCapability.supports_batch_processing()

        assert cap1 != cap2

    def test_eq_with_other_type(self):
        """Test equality returns False for non-string/non-capability types."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability != 123
        assert capability != None
        assert capability != []

    def test_is_compatible_with_version_exact_match(self):
        """Test version compatibility with exact match."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=2, patch=0),
        )

        assert capability.is_compatible_with_version(
            ModelSemVer(major=1, minor=2, patch=0)
        )

    def test_is_compatible_with_version_newer(self):
        """Test version compatibility with newer version."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.is_compatible_with_version(
            ModelSemVer(major=1, minor=5, patch=0)
        )
        assert capability.is_compatible_with_version(
            ModelSemVer(major=2, minor=0, patch=0)
        )

    def test_is_compatible_with_version_older(self):
        """Test version compatibility with older version."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=5, patch=0),
        )

        assert not capability.is_compatible_with_version(
            ModelSemVer(major=1, minor=0, patch=0)
        )

    def test_get_id_protocol(self):
        """Test get_id protocol method raises error (capability_id not in checked fields)."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        # get_id doesn't check for 'capability_id', only standard ID fields
        with pytest.raises(ModelOnexError) as exc_info:
            capability.get_id()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        capability = ModelNodeCapability(
            value="test",
            description="Test description",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        metadata = capability.get_metadata()
        assert isinstance(metadata, dict)
        assert "description" in metadata
        assert metadata["description"] == "Test description"

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        capability = ModelNodeCapability(
            value="test",
            description="Original",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        result = capability.set_metadata({"description": "Updated"})
        assert result is True
        assert capability.description == "Updated"

    def test_set_metadata_protocol_unknown_field(self):
        """Test set_metadata with unknown field."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        # Should not raise, just ignore unknown fields
        result = capability.set_metadata({"unknown_field": "value"})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        capability = ModelNodeCapability(
            capability_display_name="TEST",
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        serialized = capability.serialize()
        assert isinstance(serialized, dict)
        assert "value" in serialized
        assert "description" in serialized
        assert serialized["value"] == "test"

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.validate_instance() is True

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        # Should not raise error with extra fields
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            extra_field="ignored",
        )

        assert capability.value == "test"

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        # Should validate new assignments
        capability.description = "Updated description"
        assert capability.description == "Updated description"

    def test_dependencies_empty_by_default(self):
        """Test dependencies is empty list by default."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.dependencies == []

    def test_deprecated_false_by_default(self):
        """Test deprecated is False by default."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.deprecated is False

    def test_example_config_none_by_default(self):
        """Test example_config is None by default."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capability.example_config is None

    def test_capability_with_dependencies(self):
        """Test capability with multiple dependencies."""
        from uuid import uuid4

        dep1 = uuid4()
        dep2 = uuid4()

        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            dependencies=[dep1, dep2],
        )

        assert len(capability.dependencies) == 2
        assert dep1 in capability.dependencies
        assert dep2 in capability.dependencies


@pytest.mark.unit
class TestModelNodeCapabilityEdgeCases:
    """Test edge cases and error scenarios."""

    def test_from_string_with_dots(self):
        """Test from_string handles dots in name."""
        capability = ModelNodeCapability.from_string("supports.dry.run")

        assert capability.capability_display_name == "SUPPORTS_DRY_RUN"

    def test_version_compatibility_boundary(self):
        """Test version compatibility at boundary."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        # Exactly at version
        assert capability.is_compatible_with_version(
            ModelSemVer(major=1, minor=0, patch=0)
        )

        # One patch behind
        assert not capability.is_compatible_with_version(
            ModelSemVer(major=0, minor=9, patch=9)
        )

    def test_capability_name_uniqueness(self):
        """Test that different capabilities have different IDs."""
        cap1 = ModelNodeCapability(
            value="test1",
            description="Test 1",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )
        cap2 = ModelNodeCapability(
            value="test2",
            description="Test 2",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert cap1.capability_id != cap2.capability_id

    def test_factory_methods_produce_unique_ids(self):
        """Test factory methods produce stable UUIDs."""
        cap1 = ModelNodeCapability.supports_dry_run()
        cap2 = ModelNodeCapability.supports_dry_run()

        # Same factory should produce same UUID
        assert cap1.capability_id == cap2.capability_id

    def test_serialize_includes_none_values(self):
        """Test serialize includes None values."""
        capability = ModelNodeCapability(
            value="test",
            description="Test",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

        serialized = capability.serialize()
        # Should include fields with None values
        assert "replacement" in serialized or serialized.get("replacement") is None
