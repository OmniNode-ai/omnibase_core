"""
Unit tests for ModelNamespaceConfig.

Tests all aspects of the namespace configuration model including:
- Model instantiation and validation
- Field validation and type checking
- Literal type validation for 'strategy' field
- Serialization/deserialization
- Edge cases and error conditions
"""

import pytest
from pydantic import ValidationError

from ..core.model_namespace_config import ModelNamespaceConfig


class TestModelNamespaceConfig:
    """Test cases for ModelNamespaceConfig."""

    def test_model_instantiation_with_defaults(self):
        """Test that model can be instantiated with default values."""
        config = ModelNamespaceConfig()

        assert config.enabled is True
        assert config.strategy == "ONEX_DEFAULT"

    def test_model_instantiation_with_all_fields(self):
        """Test model instantiation with all fields provided."""
        config = ModelNamespaceConfig(enabled=False, strategy="EXPLICIT")

        assert config.enabled is False
        assert config.strategy == "EXPLICIT"

    def test_all_valid_strategy_values(self):
        """Test model instantiation with all valid strategy literals."""
        valid_strategies = ["ONEX_DEFAULT", "EXPLICIT", "AUTO"]

        for strategy in valid_strategies:
            config = ModelNamespaceConfig(enabled=True, strategy=strategy)
            assert config.strategy == strategy

    def test_strategy_literal_validation(self):
        """Test that strategy field accepts only valid literal values."""
        # Invalid strategy values
        invalid_strategies = [
            "invalid",
            "CUSTOM",
            "onex_default",  # Case sensitive
            "explicit",  # Case sensitive
            "auto",  # Case sensitive
            "DEFAULT",
            "",
            "MANUAL",
        ]

        for invalid_strategy in invalid_strategies:
            with pytest.raises(ValidationError) as exc_info:
                ModelNamespaceConfig(strategy=invalid_strategy)
            # Should mention literal values or input validation
            error_str = str(exc_info.value).lower()
            assert (
                "literal" in error_str or "input" in error_str or "value" in error_str
            )

    def test_enabled_field_validation(self):
        """Test that enabled field accepts boolean values."""
        # Valid boolean values
        config = ModelNamespaceConfig(enabled=True)
        assert config.enabled is True

        config = ModelNamespaceConfig(enabled=False)
        assert config.enabled is False

        # Pydantic converts certain string values to boolean
        config = ModelNamespaceConfig(enabled="true")
        assert config.enabled is True

        config = ModelNamespaceConfig(enabled="false")
        assert config.enabled is False  # Pydantic recognizes "false" as False

        # Note: Empty string may not be accepted by Pydantic v2 for boolean
        # Test with explicit boolean parsing values

        config = ModelNamespaceConfig(enabled=1)
        assert config.enabled is True

        config = ModelNamespaceConfig(enabled=0)
        assert config.enabled is False

    def test_field_types_validation(self):
        """Test that field types are properly validated."""
        # Test with complex non-convertible types for enabled
        with pytest.raises(ValidationError):
            ModelNamespaceConfig(enabled={"invalid": "dict"})

        with pytest.raises(ValidationError):
            ModelNamespaceConfig(enabled=["invalid", "list"])

        # Test non-string strategy (even if it would be valid literal value)
        with pytest.raises(ValidationError):
            ModelNamespaceConfig(strategy=123)

        with pytest.raises(ValidationError):
            ModelNamespaceConfig(strategy=True)

    def test_model_serialization(self):
        """Test model serialization to dict."""
        config = ModelNamespaceConfig(enabled=False, strategy="AUTO")

        data = config.model_dump()

        expected_data = {"enabled": False, "strategy": "AUTO"}

        assert data == expected_data

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        data = {"enabled": True, "strategy": "EXPLICIT"}

        config = ModelNamespaceConfig.model_validate(data)

        assert config.enabled is True
        assert config.strategy == "EXPLICIT"

    def test_model_json_serialization(self):
        """Test JSON serialization and deserialization."""
        config = ModelNamespaceConfig(enabled=True, strategy="ONEX_DEFAULT")

        # Serialize to JSON
        json_str = config.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        config_from_json = ModelNamespaceConfig.model_validate_json(json_str)

        assert config_from_json.enabled == config.enabled
        assert config_from_json.strategy == config.strategy

    def test_model_equality(self):
        """Test model equality comparison."""
        config1 = ModelNamespaceConfig(enabled=True, strategy="AUTO")

        config2 = ModelNamespaceConfig(enabled=True, strategy="AUTO")

        config3 = ModelNamespaceConfig(enabled=False, strategy="AUTO")

        assert config1 == config2
        assert config1 != config3

    def test_default_values_behavior(self):
        """Test that default values work correctly."""
        # Test with no arguments
        config = ModelNamespaceConfig()
        assert config.enabled is True
        assert config.strategy == "ONEX_DEFAULT"

        # Test with partial arguments
        config = ModelNamespaceConfig(enabled=False)
        assert config.enabled is False
        assert config.strategy == "ONEX_DEFAULT"

        config = ModelNamespaceConfig(strategy="EXPLICIT")
        assert config.enabled is True
        assert config.strategy == "EXPLICIT"

    def test_strategy_combinations(self):
        """Test different strategy and enabled combinations."""
        combinations = [
            (True, "ONEX_DEFAULT"),
            (True, "EXPLICIT"),
            (True, "AUTO"),
            (False, "ONEX_DEFAULT"),
            (False, "EXPLICIT"),
            (False, "AUTO"),
        ]

        for enabled, strategy in combinations:
            config = ModelNamespaceConfig(enabled=enabled, strategy=strategy)
            assert config.enabled == enabled
            assert config.strategy == strategy

    def test_repr_and_str(self):
        """Test string representations of the model."""
        config = ModelNamespaceConfig(enabled=True, strategy="AUTO")

        repr_str = repr(config)
        assert "ModelNamespaceConfig" in repr_str
        assert "enabled" in repr_str
        assert "strategy" in repr_str

        str_repr = str(config)
        assert isinstance(str_repr, str)


class TestModelNamespaceConfigEdgeCases:
    """Test edge cases and error conditions for ModelNamespaceConfig."""

    def test_none_values(self):
        """Test behavior with None values."""
        # enabled=None should raise ValidationError or be converted
        with pytest.raises(ValidationError):
            ModelNamespaceConfig(enabled=None)

        # strategy=None should raise ValidationError
        with pytest.raises(ValidationError):
            ModelNamespaceConfig(strategy=None)

    def test_empty_and_whitespace_strategy(self):
        """Test behavior with empty and whitespace strategy values."""
        # Empty string should be invalid
        with pytest.raises(ValidationError):
            ModelNamespaceConfig(strategy="")

        # Whitespace should be invalid
        with pytest.raises(ValidationError):
            ModelNamespaceConfig(strategy=" ")

        with pytest.raises(ValidationError):
            ModelNamespaceConfig(strategy="  ONEX_DEFAULT  ")

    def test_unicode_strategy_values(self):
        """Test that unicode characters in strategy are rejected."""
        unicode_strategies = ["ONEX_DÉFAULT", "ÉXPLICIT", "ÃUTO", "🚀_DEFAULT"]

        for strategy in unicode_strategies:
            with pytest.raises(ValidationError):
                ModelNamespaceConfig(strategy=strategy)

    def test_case_sensitivity_strategy(self):
        """Test that strategy values are case-sensitive."""
        case_variations = [
            "onex_default",
            "Onex_Default",
            "ONEX_default",
            "onex_DEFAULT",
            "Explicit",
            "EXPLICIT",
            "explicit",
            "Auto",
            "AUTO",
            "auto",
        ]

        # Only exact case should work, test some invalid cases
        invalid_cases = ["onex_default", "Onex_Default", "explicit", "auto"]

        for strategy in invalid_cases:
            with pytest.raises(ValidationError):
                ModelNamespaceConfig(strategy=strategy)

    def test_boolean_edge_cases(self):
        """Test edge cases for boolean enabled field."""
        # Test various values that Pydantic v2 accepts for booleans
        truthy_values = [1, "1", "true", "True", "yes", "on"]
        falsy_values = [0, "false", "False", "no", "off"]

        for value in truthy_values:
            config = ModelNamespaceConfig(enabled=value)
            assert config.enabled is True

        for value in falsy_values:
            config = ModelNamespaceConfig(enabled=value)
            assert config.enabled is False

        # Test values that should raise ValidationError (including empty string in v2)
        invalid_values = [[1], {"a": 1}, [], {}, ""]
        for value in invalid_values:
            with pytest.raises(ValidationError):
                ModelNamespaceConfig(enabled=value)

    def test_serialization_round_trip(self):
        """Test that serialization and deserialization preserves data."""
        original_configs = [
            ModelNamespaceConfig(),
            ModelNamespaceConfig(enabled=False),
            ModelNamespaceConfig(strategy="EXPLICIT"),
            ModelNamespaceConfig(enabled=False, strategy="AUTO"),
        ]

        for original in original_configs:
            # Test dict round-trip
            data = original.model_dump()
            restored = ModelNamespaceConfig.model_validate(data)
            assert restored == original

            # Test JSON round-trip
            json_str = original.model_dump_json()
            restored_from_json = ModelNamespaceConfig.model_validate_json(json_str)
            assert restored_from_json == original

    def test_partial_updates(self):
        """Test updating model with partial data."""
        config = ModelNamespaceConfig()

        # Test updating only enabled
        updated_data = {"enabled": False}
        updated_config = config.model_copy(update=updated_data)
        assert updated_config.enabled is False
        assert updated_config.strategy == "ONEX_DEFAULT"  # Should keep original

        # Test updating only strategy
        updated_data = {"strategy": "AUTO"}
        updated_config = config.model_copy(update=updated_data)
        assert updated_config.enabled is True  # Should keep original
        assert updated_config.strategy == "AUTO"

    def test_immutability_behavior(self):
        """Test that model behaves as expected regarding mutability."""
        config = ModelNamespaceConfig(enabled=True, strategy="AUTO")

        # Test that we can't directly modify fields (if model is set up for immutability)
        # Note: Pydantic models are mutable by default, but we test current behavior
        original_enabled = config.enabled
        original_strategy = config.strategy

        # Direct assignment should work (models are mutable by default)
        config.enabled = False
        assert config.enabled is False

        config.strategy = "EXPLICIT"
        assert config.strategy == "EXPLICIT"

    def test_validation_error_messages(self):
        """Test that validation errors provide useful messages."""
        # Test invalid strategy
        with pytest.raises(ValidationError) as exc_info:
            ModelNamespaceConfig(strategy="INVALID")

        error_message = str(exc_info.value)
        assert "strategy" in error_message.lower()

        # Test invalid enabled type that can't be converted
        with pytest.raises(ValidationError) as exc_info:
            ModelNamespaceConfig(enabled=object())

        error_message = str(exc_info.value)
        assert "enabled" in error_message.lower()

    def test_configuration_scenarios(self):
        """Test realistic configuration scenarios."""
        # Default ONEX configuration
        default_config = ModelNamespaceConfig()
        assert default_config.enabled is True
        assert default_config.strategy == "ONEX_DEFAULT"

        # Disabled namespace handling
        disabled_config = ModelNamespaceConfig(enabled=False)
        assert disabled_config.enabled is False
        # Strategy still matters even when disabled
        assert disabled_config.strategy == "ONEX_DEFAULT"

        # Explicit namespace management
        explicit_config = ModelNamespaceConfig(enabled=True, strategy="EXPLICIT")
        assert explicit_config.enabled is True
        assert explicit_config.strategy == "EXPLICIT"

        # Auto namespace detection
        auto_config = ModelNamespaceConfig(enabled=True, strategy="AUTO")
        assert auto_config.enabled is True
        assert auto_config.strategy == "AUTO"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
