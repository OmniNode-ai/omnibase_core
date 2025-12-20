"""
Unit tests for EnumEnvironment.

Tests all aspects of the environment enum including:
- Enum value validation
- Environment classification methods
- Configuration helper methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- Environment-specific logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_environment import EnumEnvironment


@pytest.mark.unit
class TestEnumEnvironment:
    """Test cases for EnumEnvironment."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            # Standard environments
            "DEVELOPMENT": "development",
            "TESTING": "testing",
            "STAGING": "staging",
            "PRODUCTION": "production",
            # Additional environments
            "LOCAL": "local",
            "INTEGRATION": "integration",
            "PREVIEW": "preview",
            "SANDBOX": "sandbox",
        }

        for name, value in expected_values.items():
            environment = getattr(EnumEnvironment, name)
            assert environment.value == value
            assert str(environment) == value

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumEnvironment.DEVELOPMENT) == "development"
        assert str(EnumEnvironment.PRODUCTION) == "production"
        assert str(EnumEnvironment.TESTING) == "testing"
        assert str(EnumEnvironment.STAGING) == "staging"

    def test_is_production_like(self):
        """Test the is_production_like class method."""
        # Production-like environments
        production_like = [
            EnumEnvironment.PRODUCTION,
            EnumEnvironment.STAGING,
        ]

        for env in production_like:
            assert EnumEnvironment.is_production_like(env) is True

        # Non-production-like environments
        non_production_like = [
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.TESTING,
            EnumEnvironment.LOCAL,
            EnumEnvironment.INTEGRATION,
            EnumEnvironment.PREVIEW,
            EnumEnvironment.SANDBOX,
        ]

        for env in non_production_like:
            assert EnumEnvironment.is_production_like(env) is False

    def test_is_development_like(self):
        """Test the is_development_like class method."""
        # Development-like environments
        development_like = [
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.LOCAL,
            EnumEnvironment.SANDBOX,
        ]

        for env in development_like:
            assert EnumEnvironment.is_development_like(env) is True

        # Non-development-like environments
        non_development_like = [
            EnumEnvironment.TESTING,
            EnumEnvironment.INTEGRATION,
            EnumEnvironment.STAGING,
            EnumEnvironment.PREVIEW,
            EnumEnvironment.PRODUCTION,
        ]

        for env in non_development_like:
            assert EnumEnvironment.is_development_like(env) is False

    def test_allows_debugging(self):
        """Test the allows_debugging class method."""
        # Environments that allow debugging
        debugging_allowed = [
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.LOCAL,
            EnumEnvironment.TESTING,
            EnumEnvironment.SANDBOX,
        ]

        for env in debugging_allowed:
            assert EnumEnvironment.allows_debugging(env) is True

        # Environments that don't allow debugging
        debugging_not_allowed = [
            EnumEnvironment.INTEGRATION,
            EnumEnvironment.STAGING,
            EnumEnvironment.PREVIEW,
            EnumEnvironment.PRODUCTION,
        ]

        for env in debugging_not_allowed:
            assert EnumEnvironment.allows_debugging(env) is False

    def test_requires_security_hardening(self):
        """Test the requires_security_hardening class method."""
        # Environments that require security hardening
        hardening_required = [
            EnumEnvironment.PRODUCTION,
            EnumEnvironment.STAGING,
        ]

        for env in hardening_required:
            assert EnumEnvironment.requires_security_hardening(env) is True

        # Environments that don't require security hardening
        hardening_not_required = [
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.LOCAL,
            EnumEnvironment.TESTING,
            EnumEnvironment.INTEGRATION,
            EnumEnvironment.PREVIEW,
            EnumEnvironment.SANDBOX,
        ]

        for env in hardening_not_required:
            assert EnumEnvironment.requires_security_hardening(env) is False

    def test_get_log_level(self):
        """Test the get_log_level class method."""
        expected_log_levels = {
            EnumEnvironment.DEVELOPMENT: "DEBUG",
            EnumEnvironment.LOCAL: "DEBUG",
            EnumEnvironment.SANDBOX: "DEBUG",
            EnumEnvironment.TESTING: "INFO",
            EnumEnvironment.INTEGRATION: "INFO",
            EnumEnvironment.STAGING: "WARN",
            EnumEnvironment.PREVIEW: "WARN",
            EnumEnvironment.PRODUCTION: "error",  # Note: lowercase 'error' as per source
        }

        for env, expected_level in expected_log_levels.items():
            assert EnumEnvironment.get_log_level(env) == expected_level

    def test_get_default_environment(self):
        """Test the get_default_environment class method."""
        default_env = EnumEnvironment.get_default_environment()
        assert default_env == EnumEnvironment.DEVELOPMENT

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumEnvironment.PRODUCTION == EnumEnvironment.PRODUCTION
        assert EnumEnvironment.DEVELOPMENT != EnumEnvironment.PRODUCTION
        assert EnumEnvironment.STAGING == EnumEnvironment.STAGING

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_environments = [
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.TESTING,
            EnumEnvironment.STAGING,
            EnumEnvironment.PRODUCTION,
            EnumEnvironment.LOCAL,
            EnumEnvironment.INTEGRATION,
            EnumEnvironment.PREVIEW,
            EnumEnvironment.SANDBOX,
        ]

        for env in all_environments:
            assert env in EnumEnvironment

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        environments = list(EnumEnvironment)
        assert len(environments) == 8

        env_values = [env.value for env in environments]
        expected_values = [
            "development",
            "testing",
            "staging",
            "production",
            "local",
            "integration",
            "preview",
            "sandbox",
        ]

        assert set(env_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        env = EnumEnvironment.PRODUCTION
        json_str = json.dumps(env, default=str)
        assert json_str == '"production"'

        # Test in dictionary
        data = {"environment": EnumEnvironment.STAGING}
        json_str = json.dumps(data, default=str)
        assert '"environment": "staging"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class EnumEnvironmentConfig(BaseModel):
            environment: EnumEnvironment

        # Test valid enum assignment
        config = EnumEnvironmentConfig(environment=EnumEnvironment.PRODUCTION)
        assert config.environment == EnumEnvironment.PRODUCTION

        # Test string assignment (should work due to str inheritance)
        config = EnumEnvironmentConfig(environment="staging")
        assert config.environment == EnumEnvironment.STAGING

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            EnumEnvironmentConfig(environment="invalid_environment")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class EnumEnvironmentConfig(BaseModel):
            environment: EnumEnvironment

        config = EnumEnvironmentConfig(environment=EnumEnvironment.DEVELOPMENT)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"environment": "development"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"environment":"development"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity
        assert EnumEnvironment.PRODUCTION.value == "production"
        assert EnumEnvironment.PRODUCTION.value != "PRODUCTION"
        assert EnumEnvironment.PRODUCTION.value != "Production"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumEnvironment("invalid_environment")

    def test_environment_classification_consistency(self):
        """Test that environment classifications are logically consistent."""
        # Production-like environments should require security hardening
        for env in EnumEnvironment:
            if EnumEnvironment.is_production_like(env):
                assert EnumEnvironment.requires_security_hardening(env) is True

        # Development-like environments should allow debugging
        for env in EnumEnvironment:
            if EnumEnvironment.is_development_like(env):
                assert EnumEnvironment.allows_debugging(env) is True

        # Production environments shouldn't allow debugging
        for env in EnumEnvironment:
            if EnumEnvironment.requires_security_hardening(env):
                assert EnumEnvironment.allows_debugging(env) is False

    def test_comprehensive_environment_scenarios(self):
        """Test comprehensive environment-based scenarios."""
        # Test development workflow scenario
        dev_env = EnumEnvironment.DEVELOPMENT
        assert EnumEnvironment.is_development_like(dev_env) is True
        assert EnumEnvironment.allows_debugging(dev_env) is True
        assert EnumEnvironment.requires_security_hardening(dev_env) is False
        assert EnumEnvironment.get_log_level(dev_env) == "DEBUG"

        # Test production scenario
        prod_env = EnumEnvironment.PRODUCTION
        assert EnumEnvironment.is_production_like(prod_env) is True
        assert EnumEnvironment.allows_debugging(prod_env) is False
        assert EnumEnvironment.requires_security_hardening(prod_env) is True
        assert EnumEnvironment.get_log_level(prod_env) == "error"

        # Test staging scenario (production-like but with different log level)
        staging_env = EnumEnvironment.STAGING
        assert EnumEnvironment.is_production_like(staging_env) is True
        assert EnumEnvironment.allows_debugging(staging_env) is False
        assert EnumEnvironment.requires_security_hardening(staging_env) is True
        assert EnumEnvironment.get_log_level(staging_env) == "WARN"

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable (as string values)
        data = {"environment": str(EnumEnvironment.INTEGRATION)}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "environment: integration" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["environment"] == "integration"

    def test_environment_ordering_consistency(self):
        """Test that environments follow expected progression."""
        # Standard development lifecycle progression
        lifecycle_order = [
            EnumEnvironment.LOCAL,
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.TESTING,
            EnumEnvironment.STAGING,
            EnumEnvironment.PRODUCTION,
        ]

        # Verify general progression: development -> testing -> staging -> production
        # Local and Development should allow debugging
        debug_environments = [EnumEnvironment.LOCAL, EnumEnvironment.DEVELOPMENT]
        for env in debug_environments:
            assert EnumEnvironment.allows_debugging(env) is True
            assert EnumEnvironment.is_development_like(env) is True

        # Production-like environments should require security hardening
        prod_environments = [EnumEnvironment.STAGING, EnumEnvironment.PRODUCTION]
        for env in prod_environments:
            assert EnumEnvironment.requires_security_hardening(env) is True
            assert EnumEnvironment.is_production_like(env) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
