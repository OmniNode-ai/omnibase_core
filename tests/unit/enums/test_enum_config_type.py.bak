"""
Unit tests for EnumConfigType.

Tests all aspects of the config type enum including:
- Enum value validation
- Category classification methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- All helper methods (is_core_config, is_infrastructure_config, etc.)
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_config_type import EnumConfigType


class TestEnumConfigType:
    """Test basic enum functionality."""

    def test_enum_values_core(self):
        """Test that all core config type enum values are present."""
        core_configs = {
            "NODE_CONFIG": "node_config",
            "FUNCTION_CONFIG": "function_config",
            "SERVICE_CONFIG": "service_config",
            "DATABASE_CONFIG": "database_config",
            "CACHE_CONFIG": "cache_config",
        }

        for name, value in core_configs.items():
            config_type = getattr(EnumConfigType, name)
            assert config_type.value == value
            assert str(config_type) == value

    def test_enum_values_infrastructure(self):
        """Test that all infrastructure config type enum values are present."""
        infra_configs = {
            "LOGGING_CONFIG": "logging_config",
            "METRICS_CONFIG": "metrics_config",
            "VALIDATION_CONFIG": "validation_config",
            "SECURITY_CONFIG": "security_config",
            "NETWORK_CONFIG": "network_config",
        }

        for name, value in infra_configs.items():
            config_type = getattr(EnumConfigType, name)
            assert config_type.value == value
            assert str(config_type) == value

    def test_enum_values_application(self):
        """Test that all application config type enum values are present."""
        app_configs = {
            "TEMPLATE_CONFIG": "template_config",
            "GENERATION_CONFIG": "generation_config",
            "DISCOVERY_CONFIG": "discovery_config",
            "RUNTIME_CONFIG": "runtime_config",
            "CLI_CONFIG": "cli_config",
        }

        for name, value in app_configs.items():
            config_type = getattr(EnumConfigType, name)
            assert config_type.value == value
            assert str(config_type) == value

    def test_enum_values_data(self):
        """Test that all data config type enum values are present."""
        data_configs = {
            "SCHEMA_CONFIG": "schema_config",
            "MODEL_CONFIG": "model_config",
            "FILTER_CONFIG": "filter_config",
            "METADATA_CONFIG": "metadata_config",
        }

        for name, value in data_configs.items():
            config_type = getattr(EnumConfigType, name)
            assert config_type.value == value
            assert str(config_type) == value

    def test_enum_values_environment(self):
        """Test that all environment config type enum values are present."""
        env_configs = {
            "DEVELOPMENT_CONFIG": "development_config",
            "TESTING_CONFIG": "testing_config",
            "PRODUCTION_CONFIG": "production_config",
            "STAGING_CONFIG": "staging_config",
        }

        for name, value in env_configs.items():
            config_type = getattr(EnumConfigType, name)
            assert config_type.value == value
            assert str(config_type) == value

    def test_enum_values_generic(self):
        """Test that all generic config type enum values are present."""
        generic_configs = {
            "GENERAL_CONFIG": "general_config",
            "CUSTOM_CONFIG": "custom_config",
            "UNKNOWN_CONFIG": "unknown_config",
        }

        for name, value in generic_configs.items():
            config_type = getattr(EnumConfigType, name)
            assert config_type.value == value
            assert str(config_type) == value

    def test_string_representation(self):
        """Test __str__ method returns correct string values."""
        assert str(EnumConfigType.NODE_CONFIG) == "node_config"
        assert str(EnumConfigType.LOGGING_CONFIG) == "logging_config"
        assert str(EnumConfigType.TEMPLATE_CONFIG) == "template_config"
        assert str(EnumConfigType.SCHEMA_CONFIG) == "schema_config"
        assert str(EnumConfigType.DEVELOPMENT_CONFIG) == "development_config"


class TestEnumConfigTypeCategoryMethods:
    """Test category classification methods."""

    def test_is_core_config(self):
        """Test is_core_config class method."""
        # Core configs should return True
        assert EnumConfigType.is_core_config(EnumConfigType.NODE_CONFIG) is True
        assert EnumConfigType.is_core_config(EnumConfigType.FUNCTION_CONFIG) is True
        assert EnumConfigType.is_core_config(EnumConfigType.SERVICE_CONFIG) is True
        assert EnumConfigType.is_core_config(EnumConfigType.DATABASE_CONFIG) is True
        assert EnumConfigType.is_core_config(EnumConfigType.CACHE_CONFIG) is True

        # Non-core configs should return False
        assert EnumConfigType.is_core_config(EnumConfigType.LOGGING_CONFIG) is False
        assert EnumConfigType.is_core_config(EnumConfigType.TEMPLATE_CONFIG) is False
        assert EnumConfigType.is_core_config(EnumConfigType.SCHEMA_CONFIG) is False
        assert EnumConfigType.is_core_config(EnumConfigType.DEVELOPMENT_CONFIG) is False

    def test_is_infrastructure_config(self):
        """Test is_infrastructure_config class method."""
        # Infrastructure configs should return True
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.LOGGING_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.METRICS_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.VALIDATION_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.SECURITY_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.NETWORK_CONFIG)
            is True
        )

        # Non-infrastructure configs should return False
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.NODE_CONFIG) is False
        )
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.TEMPLATE_CONFIG)
            is False
        )
        assert (
            EnumConfigType.is_infrastructure_config(EnumConfigType.SCHEMA_CONFIG)
            is False
        )

    def test_is_application_config(self):
        """Test is_application_config class method."""
        # Application configs should return True
        assert (
            EnumConfigType.is_application_config(EnumConfigType.TEMPLATE_CONFIG) is True
        )
        assert (
            EnumConfigType.is_application_config(EnumConfigType.GENERATION_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_application_config(EnumConfigType.DISCOVERY_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_application_config(EnumConfigType.RUNTIME_CONFIG) is True
        )
        assert EnumConfigType.is_application_config(EnumConfigType.CLI_CONFIG) is True

        # Non-application configs should return False
        assert EnumConfigType.is_application_config(EnumConfigType.NODE_CONFIG) is False
        assert (
            EnumConfigType.is_application_config(EnumConfigType.LOGGING_CONFIG) is False
        )
        assert (
            EnumConfigType.is_application_config(EnumConfigType.SCHEMA_CONFIG) is False
        )

    def test_is_data_config(self):
        """Test is_data_config class method."""
        # Data configs should return True
        assert EnumConfigType.is_data_config(EnumConfigType.SCHEMA_CONFIG) is True
        assert EnumConfigType.is_data_config(EnumConfigType.MODEL_CONFIG) is True
        assert EnumConfigType.is_data_config(EnumConfigType.FILTER_CONFIG) is True
        assert EnumConfigType.is_data_config(EnumConfigType.METADATA_CONFIG) is True

        # Non-data configs should return False
        assert EnumConfigType.is_data_config(EnumConfigType.NODE_CONFIG) is False
        assert EnumConfigType.is_data_config(EnumConfigType.LOGGING_CONFIG) is False
        assert EnumConfigType.is_data_config(EnumConfigType.TEMPLATE_CONFIG) is False

    def test_is_environment_config(self):
        """Test is_environment_config class method."""
        # Environment configs should return True
        assert (
            EnumConfigType.is_environment_config(EnumConfigType.DEVELOPMENT_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_environment_config(EnumConfigType.TESTING_CONFIG) is True
        )
        assert (
            EnumConfigType.is_environment_config(EnumConfigType.PRODUCTION_CONFIG)
            is True
        )
        assert (
            EnumConfigType.is_environment_config(EnumConfigType.STAGING_CONFIG) is True
        )

        # Non-environment configs should return False
        assert EnumConfigType.is_environment_config(EnumConfigType.NODE_CONFIG) is False
        assert (
            EnumConfigType.is_environment_config(EnumConfigType.LOGGING_CONFIG) is False
        )
        assert (
            EnumConfigType.is_environment_config(EnumConfigType.TEMPLATE_CONFIG)
            is False
        )

    def test_category_mutual_exclusivity(self):
        """Test that config types belong to only one category (or none)."""
        all_configs = list(EnumConfigType)

        for config in all_configs:
            categories = [
                EnumConfigType.is_core_config(config),
                EnumConfigType.is_infrastructure_config(config),
                EnumConfigType.is_application_config(config),
                EnumConfigType.is_data_config(config),
                EnumConfigType.is_environment_config(config),
            ]

            # Generic configs may not belong to any category
            if config in [
                EnumConfigType.GENERAL_CONFIG,
                EnumConfigType.CUSTOM_CONFIG,
                EnumConfigType.UNKNOWN_CONFIG,
            ]:
                assert (
                    sum(categories) == 0
                ), f"{config} should not belong to any category"
            else:
                # All other configs should belong to exactly one category
                assert (
                    sum(categories) == 1
                ), f"{config} should belong to exactly one category, found {sum(categories)}"


class TestEnumConfigTypeIntegration:
    """Test integration with other systems."""

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumConfigType.NODE_CONFIG == EnumConfigType.NODE_CONFIG
        assert EnumConfigType.LOGGING_CONFIG != EnumConfigType.METRICS_CONFIG
        assert EnumConfigType.TEMPLATE_CONFIG == EnumConfigType.TEMPLATE_CONFIG

    def test_enum_membership(self):
        """Test enum membership checking."""
        assert EnumConfigType.NODE_CONFIG in EnumConfigType
        assert EnumConfigType.LOGGING_CONFIG in EnumConfigType
        assert EnumConfigType.DEVELOPMENT_CONFIG in EnumConfigType

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        config_types = list(EnumConfigType)
        # Should have all 26 config types
        assert len(config_types) == 26

        # Verify all expected configs are present
        config_values = [ct.value for ct in config_types]
        assert "node_config" in config_values
        assert "logging_config" in config_values
        assert "template_config" in config_values

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        config = EnumConfigType.NODE_CONFIG
        json_str = json.dumps(config, default=str)
        assert json_str == '"node_config"'

        # Test in dictionary
        data = {"config_type": EnumConfigType.LOGGING_CONFIG}
        json_str = json.dumps(data, default=str)
        assert '"config_type": "logging_config"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class ConfigModel(BaseModel):
            config_type: EnumConfigType

        # Test valid enum assignment
        config = ConfigModel(config_type=EnumConfigType.DATABASE_CONFIG)
        assert config.config_type == EnumConfigType.DATABASE_CONFIG

        # Test string assignment (should work due to str inheritance)
        config = ConfigModel(config_type="security_config")
        assert config.config_type == EnumConfigType.SECURITY_CONFIG

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            ConfigModel(config_type="invalid_config_type")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class ConfigModel(BaseModel):
            config_type: EnumConfigType

        config = ConfigModel(config_type=EnumConfigType.METRICS_CONFIG)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"config_type": "metrics_config"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"config_type":"metrics_config"}'


class TestEnumConfigTypeEdgeCases:
    """Test edge cases and error conditions."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""
        assert EnumConfigType.NODE_CONFIG.value == "node_config"
        assert EnumConfigType.NODE_CONFIG.value != "NODE_CONFIG"
        assert EnumConfigType.NODE_CONFIG.value != "Node_Config"

    def test_invalid_enum_creation(self):
        """Test that invalid enum values cannot be created."""
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumConfigType("invalid_config")

    def test_unique_decorator_enforcement(self):
        """Test that @unique decorator prevents duplicate values."""
        # Get all enum values
        values = [ct.value for ct in EnumConfigType]

        # All values should be unique (no duplicates)
        assert len(values) == len(set(values))

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable
        data = {"config_type": EnumConfigType.PRODUCTION_CONFIG.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "config_type: production_config" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["config_type"] == "production_config"

        # Test that the enum value equals the string
        assert EnumConfigType.PRODUCTION_CONFIG == "production_config"


class TestEnumConfigTypeComprehensiveScenarios:
    """Test comprehensive real-world scenarios."""

    def test_config_routing_by_category(self):
        """Test routing configs based on their category."""
        # Simulate routing different config types
        core_configs = [
            ct for ct in EnumConfigType if EnumConfigType.is_core_config(ct)
        ]
        assert len(core_configs) == 5
        assert EnumConfigType.NODE_CONFIG in core_configs
        assert EnumConfigType.DATABASE_CONFIG in core_configs

        infra_configs = [
            ct for ct in EnumConfigType if EnumConfigType.is_infrastructure_config(ct)
        ]
        assert len(infra_configs) == 5
        assert EnumConfigType.LOGGING_CONFIG in infra_configs
        assert EnumConfigType.SECURITY_CONFIG in infra_configs

    def test_environment_specific_configs(self):
        """Test environment-specific configuration handling."""
        dev_config = EnumConfigType.DEVELOPMENT_CONFIG
        prod_config = EnumConfigType.PRODUCTION_CONFIG

        assert EnumConfigType.is_environment_config(dev_config) is True
        assert EnumConfigType.is_environment_config(prod_config) is True

        # Different environments should have different values
        assert dev_config != prod_config
        assert str(dev_config) == "development_config"
        assert str(prod_config) == "production_config"

    def test_config_type_classification_coverage(self):
        """Test that all non-generic configs are classified."""
        all_configs = list(EnumConfigType)
        generic_configs = [
            EnumConfigType.GENERAL_CONFIG,
            EnumConfigType.CUSTOM_CONFIG,
            EnumConfigType.UNKNOWN_CONFIG,
        ]

        classified_configs = [
            ct
            for ct in all_configs
            if (
                EnumConfigType.is_core_config(ct)
                or EnumConfigType.is_infrastructure_config(ct)
                or EnumConfigType.is_application_config(ct)
                or EnumConfigType.is_data_config(ct)
                or EnumConfigType.is_environment_config(ct)
            )
        ]

        # All configs except generic ones should be classified
        expected_classified = len(all_configs) - len(generic_configs)
        assert len(classified_configs) == expected_classified


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
