"""
Tests for ModelGenericProperties ONEX-compliant implementation.

Tests the new from_flat_dict() method and proper Pydantic validation patterns,
ensuring the factory method anti-pattern has been properly removed.
"""

import pytest

from omnibase_core.models.core.model_generic_properties import ModelGenericProperties


class TestModelGenericPropertiesONEXCompliance:
    """Test ONEX-compliant ModelGenericProperties implementation."""

    def test_direct_instantiation_with_typed_properties(self):
        """Test direct instantiation using typed property dictionaries."""
        props = ModelGenericProperties(
            string_properties={"name": "test", "type": "example"},
            numeric_properties={"count": 42, "size": 100.5},
            boolean_properties={"enabled": True, "debug": False},
            list_properties={"tags": ["a", "b", "c"]},
            nested_properties={"config": {"key": "value", "env": "test"}},
        )

        assert props.string_properties == {"name": "test", "type": "example"}
        assert props.numeric_properties == {"count": 42, "size": 100.5}
        assert props.boolean_properties == {"enabled": True, "debug": False}
        assert props.list_properties == {"tags": ["a", "b", "c"]}
        assert props.nested_properties == {"config": {"key": "value", "env": "test"}}

    def test_from_flat_dict_type_categorization(self):
        """Test from_flat_dict properly categorizes property types."""
        flat_data = {
            "name": "test",  # string
            "count": 42,  # int
            "size": 100.5,  # float
            "enabled": True,  # bool
            "debug": False,  # bool
            "tags": ["a", "b", "c"],  # list of strings
            "config": {"key": "value", "env": "test"},  # nested dict
        }

        props = ModelGenericProperties.from_flat_dict(flat_data)

        assert props.string_properties == {"name": "test"}
        assert props.numeric_properties == {"count": 42, "size": 100.5}
        assert props.boolean_properties == {"enabled": True, "debug": False}
        assert props.list_properties == {"tags": ["a", "b", "c"]}
        assert props.nested_properties == {"config": {"key": "value", "env": "test"}}

    def test_from_flat_dict_none_input(self):
        """Test from_flat_dict handles None input."""
        result = ModelGenericProperties.from_flat_dict(None)
        assert result is None

    def test_from_flat_dict_empty_dict(self):
        """Test from_flat_dict handles empty dictionary."""
        props = ModelGenericProperties.from_flat_dict({})

        assert props.string_properties == {}
        assert props.numeric_properties == {}
        assert props.boolean_properties == {}
        assert props.list_properties == {}
        assert props.nested_properties == {}

    def test_from_flat_dict_uses_pydantic_validation(self):
        """Test from_flat_dict uses Pydantic validation (not bypassing)."""
        # This should pass through Pydantic validation
        flat_data = {"name": "test", "count": 42}
        props = ModelGenericProperties.from_flat_dict(flat_data)

        # Verify it's a properly constructed Pydantic model
        assert isinstance(props, ModelGenericProperties)
        assert hasattr(props, "model_validate")
        assert hasattr(props, "model_dump")

    def test_model_validate_with_typed_data(self):
        """Test model_validate works with typed property dictionaries."""
        typed_data = {
            "string_properties": {"name": "test"},
            "numeric_properties": {"count": 42},
            "boolean_properties": {"enabled": True},
        }

        props = ModelGenericProperties.model_validate(typed_data)

        assert props.string_properties == {"name": "test"}
        assert props.numeric_properties == {"count": 42}
        assert props.boolean_properties == {"enabled": True}

    def test_to_dict_flattening(self):
        """Test to_dict properly flattens typed properties."""
        props = ModelGenericProperties(
            string_properties={"name": "test"},
            numeric_properties={"count": 42},
            boolean_properties={"enabled": True},
            list_properties={"tags": ["a", "b"]},
            nested_properties={"config": {"key": "value"}},
        )

        flat_dict = props.to_dict()

        expected = {
            "name": "test",
            "count": 42,
            "enabled": True,
            "tags": ["a", "b"],
            "config": {"key": "value"},
        }

        assert flat_dict == expected

    def test_get_method_cross_type_access(self):
        """Test get() method can access properties across all types."""
        props = ModelGenericProperties(
            string_properties={"name": "test"},
            numeric_properties={"count": 42},
            boolean_properties={"enabled": True},
            list_properties={"tags": ["a", "b"]},
            nested_properties={"config": {"key": "value"}},
        )

        assert props.get("name") == "test"
        assert props.get("count") == 42
        assert props.get("enabled") is True
        assert props.get("tags") == ["a", "b"]
        assert props.get("config") == {"key": "value"}
        assert props.get("nonexistent") is None
        assert props.get("nonexistent", "default") == "default"

    def test_round_trip_consistency(self):
        """Test round-trip conversion maintains data consistency."""
        original_flat = {
            "name": "test",
            "count": 42,
            "enabled": True,
            "tags": ["a", "b", "c"],
            "config": {"key": "value"},
        }

        # Convert to typed properties and back
        props = ModelGenericProperties.from_flat_dict(original_flat)
        result_flat = props.to_dict()

        assert result_flat == original_flat

    def test_pydantic_extra_forbid_validation(self):
        """Test that extra fields are forbidden (strict validation)."""
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            ModelGenericProperties.model_validate(
                {
                    "string_properties": {"name": "test"},
                    "invalid_field": "should_fail",  # This should be rejected
                }
            )

    def test_default_factory_constructor_usage(self):
        """Test default factory constructor still works (used in model_registry_health_report.py)."""
        # This simulates the default_factory=ModelGenericProperties usage
        props = ModelGenericProperties()

        assert props.string_properties == {}
        assert props.numeric_properties == {}
        assert props.boolean_properties == {}
        assert props.list_properties == {}
        assert props.nested_properties == {}
