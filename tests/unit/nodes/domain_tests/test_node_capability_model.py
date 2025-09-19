"""
Test Node Capability Model functionality.

Validates that the ModelNodeCapability works correctly with all
its factory methods, validation, and metadata features.
"""

import pytest
from typing import Dict, List

from omnibase_core.models.nodes import ModelNodeCapability


class TestNodeCapabilityModel:
    """Test ModelNodeCapability functionality."""

    def test_basic_capability_creation(self):
        """Test basic capability creation and properties."""
        capability = ModelNodeCapability(
            name="TEST_CAPABILITY",
            value="test_capability",
            description="Test capability for testing",
            version_introduced="1.0.0",
        )

        assert capability.name == "TEST_CAPABILITY"
        assert capability.value == "test_capability"
        assert capability.description == "Test capability for testing"
        assert capability.version_introduced == "1.0.0"
        assert not capability.deprecated
        assert capability.performance_impact == "low"

    def test_supports_dry_run_factory(self):
        """Test SUPPORTS_DRY_RUN factory method."""
        capability = ModelNodeCapability.SUPPORTS_DRY_RUN()

        assert capability.name == "SUPPORTS_DRY_RUN"
        assert capability.value == "supports_dry_run"
        assert "simulate execution" in capability.description
        assert not capability.configuration_required
        assert capability.performance_impact == "low"
        assert not capability.deprecated

    def test_supports_batch_processing_factory(self):
        """Test SUPPORTS_BATCH_PROCESSING factory method."""
        capability = ModelNodeCapability.SUPPORTS_BATCH_PROCESSING()

        assert capability.name == "SUPPORTS_BATCH_PROCESSING"
        assert capability.value == "supports_batch_processing"
        assert "batch" in capability.description.lower()
        assert capability.configuration_required
        assert capability.performance_impact == "medium"
        assert capability.example_config is not None
        assert "batch_size" in capability.example_config

    def test_supports_custom_handlers_factory(self):
        """Test SUPPORTS_CUSTOM_HANDLERS factory method."""
        capability = ModelNodeCapability.SUPPORTS_CUSTOM_HANDLERS()

        assert capability.name == "SUPPORTS_CUSTOM_HANDLERS"
        assert capability.value == "supports_custom_handlers"
        assert capability.configuration_required
        assert "SUPPORTS_SCHEMA_VALIDATION" in capability.dependencies

    def test_telemetry_enabled_factory(self):
        """Test TELEMETRY_ENABLED factory method."""
        capability = ModelNodeCapability.TELEMETRY_ENABLED()

        assert capability.name == "TELEMETRY_ENABLED"
        assert capability.value == "telemetry_enabled"
        assert capability.version_introduced == "1.1.0"
        assert capability.configuration_required
        assert capability.example_config is not None

    def test_supports_correlation_id_factory(self):
        """Test SUPPORTS_CORRELATION_ID factory method."""
        capability = ModelNodeCapability.SUPPORTS_CORRELATION_ID()

        assert capability.name == "SUPPORTS_CORRELATION_ID"
        assert capability.value == "supports_correlation_id"
        assert not capability.configuration_required
        assert capability.performance_impact == "low"

    def test_supports_event_bus_factory(self):
        """Test SUPPORTS_EVENT_BUS factory method."""
        capability = ModelNodeCapability.SUPPORTS_EVENT_BUS()

        assert capability.name == "SUPPORTS_EVENT_BUS"
        assert capability.value == "supports_event_bus"
        assert capability.configuration_required
        assert capability.performance_impact == "medium"
        assert "SUPPORTS_CORRELATION_ID" in capability.dependencies
        assert capability.example_config is not None

    def test_supports_schema_validation_factory(self):
        """Test SUPPORTS_SCHEMA_VALIDATION factory method."""
        capability = ModelNodeCapability.SUPPORTS_SCHEMA_VALIDATION()

        assert capability.name == "SUPPORTS_SCHEMA_VALIDATION"
        assert capability.value == "supports_schema_validation"
        assert not capability.configuration_required
        assert capability.performance_impact == "low"

    def test_supports_error_recovery_factory(self):
        """Test SUPPORTS_ERROR_RECOVERY factory method."""
        capability = ModelNodeCapability.SUPPORTS_ERROR_RECOVERY()

        assert capability.name == "SUPPORTS_ERROR_RECOVERY"
        assert capability.value == "supports_error_recovery"
        assert capability.version_introduced == "1.1.0"
        assert capability.configuration_required
        assert capability.performance_impact == "medium"
        assert capability.example_config is not None
        assert "max_retries" in capability.example_config

    def test_supports_event_discovery_factory(self):
        """Test SUPPORTS_EVENT_DISCOVERY factory method."""
        capability = ModelNodeCapability.SUPPORTS_EVENT_DISCOVERY()

        assert capability.name == "SUPPORTS_EVENT_DISCOVERY"
        assert capability.value == "supports_event_discovery"
        assert capability.version_introduced == "1.2.0"
        assert not capability.configuration_required
        assert len(capability.dependencies) == 2
        assert "SUPPORTS_EVENT_BUS" in capability.dependencies
        assert "SUPPORTS_SCHEMA_VALIDATION" in capability.dependencies

    def test_from_string_known_capabilities(self):
        """Test from_string with known capabilities."""
        test_cases = [
            ("SUPPORTS_DRY_RUN", "SUPPORTS_DRY_RUN"),
            ("supports_dry_run", "SUPPORTS_DRY_RUN"),
            ("SUPPORTS_BATCH_PROCESSING", "SUPPORTS_BATCH_PROCESSING"),
            ("TELEMETRY_ENABLED", "TELEMETRY_ENABLED"),
        ]

        for input_str, expected_name in test_cases:
            capability = ModelNodeCapability.from_string(input_str)
            assert capability.name == expected_name

    def test_from_string_unknown_capability(self):
        """Test from_string with unknown capability."""
        capability = ModelNodeCapability.from_string("UNKNOWN_CAPABILITY")

        assert capability.name == "UNKNOWN_CAPABILITY"
        assert capability.value == "unknown_capability"
        assert "Custom capability" in capability.description
        assert capability.version_introduced == "1.0.0"

    def test_string_representation(self):
        """Test string representation."""
        capability = ModelNodeCapability.SUPPORTS_DRY_RUN()
        assert str(capability) == "supports_dry_run"

    def test_equality_comparison(self):
        """Test equality comparison."""
        capability = ModelNodeCapability.SUPPORTS_DRY_RUN()

        # Test equality with string
        assert capability == "supports_dry_run"
        assert capability == "SUPPORTS_DRY_RUN"

        # Test equality with another capability
        other_capability = ModelNodeCapability.SUPPORTS_DRY_RUN()
        assert capability == other_capability

        # Test inequality
        different_capability = ModelNodeCapability.SUPPORTS_BATCH_PROCESSING()
        assert capability != different_capability
        assert capability != "different_capability"

    def test_version_compatibility(self):
        """Test version compatibility checking."""
        # Test capability introduced in 1.1.0
        capability = ModelNodeCapability.TELEMETRY_ENABLED()

        # Should be compatible with same or later versions
        assert capability.is_compatible_with_version("1.1.0")
        assert capability.is_compatible_with_version("1.2.0")
        assert capability.is_compatible_with_version("2.0.0")

        # Should not be compatible with earlier versions
        assert not capability.is_compatible_with_version("1.0.0")

    def test_performance_impact_validation(self):
        """Test performance impact validation."""
        valid_impacts = ["low", "medium", "high"]

        for impact in valid_impacts:
            capability = ModelNodeCapability(
                name="TEST_CAPABILITY",
                value="test_capability",
                description="Test",
                performance_impact=impact,
            )
            assert capability.performance_impact == impact

        # Test invalid impact should fail validation
        with pytest.raises(Exception):
            ModelNodeCapability(
                name="TEST_CAPABILITY",
                value="test_capability",
                description="Test",
                performance_impact="invalid",
            )

    def test_name_pattern_validation(self):
        """Test name pattern validation."""
        # Valid names
        valid_names = [
            "SUPPORTS_DRY_RUN",
            "TELEMETRY_ENABLED",
            "A_VALID_NAME",
            "X123_TEST",
        ]

        for name in valid_names:
            capability = ModelNodeCapability(
                name=name,
                value="test",
                description="Test",
            )
            assert capability.name == name

        # Invalid names should fail validation
        invalid_names = [
            "invalid_name",  # lowercase
            "123_INVALID",   # starts with number
            "INVALID-NAME",  # contains hyphen
            "",              # empty
        ]

        for name in invalid_names:
            with pytest.raises(Exception):
                ModelNodeCapability(
                    name=name,
                    value="test",
                    description="Test",
                )

    def test_dependencies_management(self):
        """Test dependency management."""
        capability = ModelNodeCapability(
            name="TEST_CAPABILITY",
            value="test_capability",
            description="Test capability with dependencies",
            dependencies=["DEP1", "DEP2"],
        )

        assert len(capability.dependencies) == 2
        assert "DEP1" in capability.dependencies
        assert "DEP2" in capability.dependencies

        # Test empty dependencies
        simple_capability = ModelNodeCapability(
            name="SIMPLE_CAPABILITY",
            value="simple_capability",
            description="Simple capability",
        )
        assert len(simple_capability.dependencies) == 0

    def test_deprecation_handling(self):
        """Test deprecation handling."""
        deprecated_capability = ModelNodeCapability(
            name="OLD_CAPABILITY",
            value="old_capability",
            description="Deprecated capability",
            deprecated=True,
            replacement="NEW_CAPABILITY",
        )

        assert deprecated_capability.deprecated
        assert deprecated_capability.replacement == "NEW_CAPABILITY"

    def test_example_config_validation(self):
        """Test example configuration validation."""
        capability = ModelNodeCapability(
            name="CONFIG_CAPABILITY",
            value="config_capability",
            description="Capability with config",
            configuration_required=True,
            example_config={"key1": "value1", "key2": 42},
        )

        assert capability.configuration_required
        assert capability.example_config is not None
        assert capability.example_config["key1"] == "value1"
        assert capability.example_config["key2"] == 42

    def test_model_serialization(self):
        """Test model serialization and deserialization."""
        original = ModelNodeCapability.SUPPORTS_BATCH_PROCESSING()

        # Serialize
        serialized = original.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["name"] == "SUPPORTS_BATCH_PROCESSING"

        # Deserialize
        restored = ModelNodeCapability.model_validate(serialized)
        assert restored.name == original.name
        assert restored.value == original.value
        assert restored.description == original.description

    @pytest.mark.parametrize("factory_method", [
        "SUPPORTS_DRY_RUN",
        "SUPPORTS_BATCH_PROCESSING",
        "SUPPORTS_CUSTOM_HANDLERS",
        "TELEMETRY_ENABLED",
        "SUPPORTS_CORRELATION_ID",
        "SUPPORTS_EVENT_BUS",
        "SUPPORTS_SCHEMA_VALIDATION",
        "SUPPORTS_ERROR_RECOVERY",
        "SUPPORTS_EVENT_DISCOVERY",
    ])
    def test_all_factory_methods(self, factory_method):
        """Test all factory methods work correctly."""
        capability = getattr(ModelNodeCapability, factory_method)()

        # Basic validation
        assert capability.name == factory_method
        assert capability.value is not None
        assert capability.description is not None
        assert capability.version_introduced is not None

        # Performance impact should be valid
        assert capability.performance_impact in ["low", "medium", "high"]

        # Dependencies should be a list
        assert isinstance(capability.dependencies, list)

    def test_capability_consistency(self):
        """Test consistency across capabilities."""
        all_capabilities = [
            ModelNodeCapability.SUPPORTS_DRY_RUN(),
            ModelNodeCapability.SUPPORTS_BATCH_PROCESSING(),
            ModelNodeCapability.SUPPORTS_CUSTOM_HANDLERS(),
            ModelNodeCapability.TELEMETRY_ENABLED(),
            ModelNodeCapability.SUPPORTS_CORRELATION_ID(),
            ModelNodeCapability.SUPPORTS_EVENT_BUS(),
            ModelNodeCapability.SUPPORTS_SCHEMA_VALIDATION(),
            ModelNodeCapability.SUPPORTS_ERROR_RECOVERY(),
            ModelNodeCapability.SUPPORTS_EVENT_DISCOVERY(),
        ]

        # Check uniqueness
        names = [cap.name for cap in all_capabilities]
        assert len(names) == len(set(names)), "Duplicate capability names found"

        values = [cap.value for cap in all_capabilities]
        assert len(values) == len(set(values)), "Duplicate capability values found"

        # Check consistency
        for capability in all_capabilities:
            # Name should be uppercase, value lowercase
            assert capability.name.isupper()
            assert capability.value.islower()

            # Name and value should be related
            expected_value = capability.name.lower()
            assert capability.value == expected_value

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test with minimal required fields
        minimal = ModelNodeCapability(
            name="MINIMAL",
            value="minimal",
            description="Minimal capability",
        )
        assert minimal.name == "MINIMAL"

        # Test with all fields
        maximal = ModelNodeCapability(
            name="MAXIMAL",
            value="maximal",
            description="Maximal capability",
            version_introduced="2.0.0",
            dependencies=["DEP1", "DEP2"],
            configuration_required=True,
            performance_impact="high",
            deprecated=True,
            replacement="NEW_MAXIMAL",
            example_config={"complex": {"nested": {"config": True}}},
        )
        assert maximal.deprecated
        assert maximal.example_config["complex"]["nested"]["config"]