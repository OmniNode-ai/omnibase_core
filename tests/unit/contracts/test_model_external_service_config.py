# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelExternalServiceConfig.

Validates external service configuration model with connection config types,
service-specific configuration management, and health check support.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_retry_config import ModelRetryConfig
from omnibase_core.models.services import ModelExternalServiceConfig


@pytest.mark.unit
class TestModelExternalServiceConfigBasic:
    """Test basic external service configuration functionality."""

    def test_minimal_required_configuration(self):
        """Test configuration with only required fields."""
        config = ModelExternalServiceConfig(service_type="rest_api")

        assert config.service_type == "rest_api"
        assert config.service_name == "unnamed_service"
        assert config.health_check_enabled is True
        assert config.health_check_timeout == 5
        assert config.required is True
        assert config.retry_config is None
        assert config.connection_config is not None

    def test_default_configuration_values(self):
        """Test default values for external service configuration."""
        config = ModelExternalServiceConfig(service_type="graphql")

        # Verify all defaults
        assert config.service_name == "unnamed_service"
        assert config.health_check_enabled is True
        assert config.health_check_timeout == 5
        assert config.required is True
        assert config.retry_config is None
        assert config.tags == {}

    def test_custom_configuration(self):
        """Test custom external service configuration."""
        retry_config = ModelRetryConfig.create_standard()
        config = ModelExternalServiceConfig(
            service_name="my_service",
            service_type="rest_api",
            health_check_enabled=False,
            health_check_timeout=10,
            required=False,
            retry_config=retry_config,
            tags={"env": "production", "tier": "critical"},
        )

        assert config.service_name == "my_service"
        assert config.service_type == "rest_api"
        assert config.health_check_enabled is False
        assert config.health_check_timeout == 10
        assert config.required is False
        assert config.retry_config == retry_config
        assert config.tags == {"env": "production", "tier": "critical"}

    def test_various_service_types(self):
        """Test different service type values."""
        service_types = [
            "rest_api",
            "graphql",
            "grpc",
            "message_queue",
            "websocket",
            "database",
        ]

        for service_type in service_types:
            config = ModelExternalServiceConfig(service_type=service_type)
            assert config.service_type == service_type


@pytest.mark.unit
class TestModelExternalServiceConfigConnectionTypes:
    """Test connection config type handling and validation."""

    def test_all_authentication_methods(self):
        """Test all available authentication methods through connection config."""
        # Test REST API with bearer token
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "bearer_token": "test_token",
            },
        )
        assert config.connection_config.get_authentication_type() == "bearer_token"

        # Test REST API with API key
        config_api_key = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "api_key": "test_key",
            },
        )
        assert config_api_key.connection_config.get_authentication_type() == "api_key"

        # Test REST API with no auth
        config_no_auth = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
            },
        )
        assert config_no_auth.connection_config.get_authentication_type() == "none"

    def test_rest_api_connection_config(self):
        """Test REST API connection configuration."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "bearer_token": "token",
                "timeout_seconds": 60,
                "max_retries": 5,
            },
        )

        # Duck typing - check for REST API attributes
        assert hasattr(config.connection_config, "base_url")
        assert config.connection_config.base_url == "https://api.example.com"
        assert config.connection_config.timeout_seconds == 60
        assert config.connection_config.max_retries == 5

    def test_database_connection_config(self):
        """Test database connection configuration."""
        config = ModelExternalServiceConfig(
            service_type="database",
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "user",
                "password": "pass",
            },
        )

        # Duck typing - check for database attributes
        assert hasattr(config.connection_config, "host")
        assert config.connection_config.host == "localhost"
        assert config.connection_config.port == 5432
        assert config.connection_config.database == "testdb"

    def test_generic_connection_config(self):
        """Test generic connection configuration."""
        config = ModelExternalServiceConfig(
            service_type="custom_service",
        )

        # Generic config is used when no specific config is provided
        assert config.connection_config is not None

    def test_auto_conversion_database_config(self):
        """Test automatic conversion to database config based on service type."""
        config = ModelExternalServiceConfig(
            service_type="database",
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "user",
                "password": "pass",
            },
        )

        # Verify database config was created
        assert hasattr(config.connection_config, "host")
        assert config.connection_config.host == "localhost"

    def test_auto_conversion_rest_api_config(self):
        """Test automatic conversion to REST API config based on service type."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "timeout_seconds": 30,
            },
        )

        # Verify REST API config was created
        assert hasattr(config.connection_config, "base_url")
        assert config.connection_config.base_url == "https://api.example.com"

    def test_auth_type_by_string_value_accepted(self):
        """Test that authentication type is determined by connection config."""
        # REST API with bearer token (string value)
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "bearer_token": "test_token",
            },
        )

        assert config.connection_config.get_authentication_type() == "bearer_token"
        assert config.connection_config.has_authentication()

    def test_auth_type_case_sensitivity(self):
        """Test authentication configuration with REST API."""
        # Test with API key
        config_api_key = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "api_key": "test_key",
            },
        )
        assert config_api_key.connection_config.get_authentication_type() == "api_key"

        # Test with bearer token
        config_bearer = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "bearer_token": "test_token",
            },
        )
        assert (
            config_bearer.connection_config.get_authentication_type() == "bearer_token"
        )


@pytest.mark.unit
class TestModelExternalServiceConfigFieldValidation:
    """Test field validation rules and constraints."""

    def test_service_type_required(self):
        """Test service_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExternalServiceConfig()

        error = exc_info.value
        assert "service_type" in str(error)
        assert "Field required" in str(error)

    def test_service_name_pattern(self):
        """Test service_name pattern validation."""
        # Valid names
        valid_names = ["my_service", "my-service", "MyService123"]
        for name in valid_names:
            config = ModelExternalServiceConfig(
                service_name=name,
                service_type="rest_api",
            )
            assert config.service_name == name

        # Invalid names
        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_name="my service",  # Space not allowed
                service_type="rest_api",
            )

    def test_service_type_pattern(self):
        """Test service_type pattern validation."""
        # Valid types
        valid_types = ["rest_api", "rest-api", "RestAPI123"]
        for service_type in valid_types:
            config = ModelExternalServiceConfig(service_type=service_type)
            assert config.service_type == service_type

        # Invalid types
        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(service_type="rest api")  # Space not allowed

    def test_health_check_timeout_range(self):
        """Test health_check_timeout must be between 1 and 300."""
        # Valid values
        config_min = ModelExternalServiceConfig(
            service_type="rest_api",
            health_check_timeout=1,
        )
        assert config_min.health_check_timeout == 1

        config_max = ModelExternalServiceConfig(
            service_type="rest_api",
            health_check_timeout=300,
        )
        assert config_max.health_check_timeout == 300

        # Invalid values
        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                health_check_timeout=0,
            )

        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                health_check_timeout=301,
            )


@pytest.mark.unit
class TestModelExternalServiceConfigHealthChecks:
    """Test health check configuration."""

    def test_health_check_enabled(self):
        """Test health check enabled configuration."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            health_check_enabled=True,
            health_check_timeout=10,
        )

        assert config.health_check_enabled is True
        assert config.health_check_timeout == 10

    def test_health_check_disabled(self):
        """Test health check disabled configuration."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            health_check_enabled=False,
        )

        assert config.health_check_enabled is False
        # Timeout should still have default
        assert config.health_check_timeout == 5


@pytest.mark.unit
class TestModelExternalServiceConfigRetryConfig:
    """Test retry configuration."""

    def test_retry_config_provided(self):
        """Test configuration with retry config."""
        retry_config = ModelRetryConfig.create_standard()
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            retry_config=retry_config,
        )

        assert config.retry_config is not None
        assert config.retry_config.max_attempts == retry_config.max_attempts

    def test_retry_config_optional(self):
        """Test that retry config is optional."""
        config = ModelExternalServiceConfig(service_type="rest_api")

        assert config.retry_config is None


@pytest.mark.unit
class TestModelExternalServiceConfigSerialization:
    """Test external service configuration serialization."""

    def test_model_dump(self):
        """Test serialization to dictionary."""
        config = ModelExternalServiceConfig(
            service_name="test_service",
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "timeout_seconds": 60,
            },
        )

        data = config.model_dump()

        assert data["service_name"] == "test_service"
        assert data["service_type"] == "rest_api"
        assert "connection_config" in data

    def test_model_dump_json(self):
        """Test JSON serialization."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
        )

        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "service_type" in json_str

    def test_round_trip_serialization(self):
        """Test serialization and deserialization."""
        original = ModelExternalServiceConfig(
            service_name="my_service",
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "bearer_token": "token",
                "timeout_seconds": 45,
            },
            health_check_enabled=False,
            health_check_timeout=10,
            required=False,
            tags={"env": "prod"},
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelExternalServiceConfig.model_validate(data)

        assert restored.service_name == original.service_name
        assert restored.service_type == original.service_type
        assert restored.health_check_enabled == original.health_check_enabled
        assert restored.health_check_timeout == original.health_check_timeout
        assert restored.required == original.required
        assert restored.tags == original.tags


@pytest.mark.unit
class TestModelExternalServiceConfigMethods:
    """Test model methods."""

    def test_get_connection_string_safe_rest_api(self):
        """Test safe connection string for REST API."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
                "bearer_token": "token",
            },
        )

        conn_str = config.get_connection_string_safe()
        assert conn_str == "api://api.example.com"

    def test_get_connection_string_safe_database(self):
        """Test safe connection string for database."""
        config = ModelExternalServiceConfig(
            service_type="database",
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "user",
                "password": "pass",
            },
        )

        conn_str = config.get_connection_string_safe()
        assert conn_str == "db://localhost:5432/testdb"

    def test_apply_environment_overrides(self):
        """Test applying environment overrides."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com",
            },
        )

        # This should return a new config or the same config if no overrides
        updated = config.apply_environment_overrides()
        assert isinstance(updated, ModelExternalServiceConfig)


@pytest.mark.unit
class TestModelExternalServiceConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_features_disabled(self):
        """Test configuration with optional features disabled."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            health_check_enabled=False,
            required=False,
        )

        assert config.health_check_enabled is False
        assert config.required is False

    def test_all_features_enabled_custom_values(self):
        """Test configuration with all features enabled and custom values."""
        retry_config = ModelRetryConfig.create_standard()
        config = ModelExternalServiceConfig(
            service_name="full_service",
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com/v2",
                "bearer_token": "token",
                "timeout_seconds": 120,
                "max_retries": 5,
            },
            health_check_enabled=True,
            health_check_timeout=15,
            required=True,
            retry_config=retry_config,
            tags={"env": "production", "team": "platform"},
        )

        assert config.health_check_enabled is True
        assert config.required is True
        assert config.health_check_timeout == 15
        assert config.retry_config is not None
        assert len(config.tags) == 2


@pytest.mark.unit
class TestModelExternalServiceConfigFactoryMethods:
    """Test factory methods for creating configurations."""

    def test_create_database_service(self):
        """Test creating database service configuration."""
        config = ModelExternalServiceConfig.create_database_service(
            service_name="postgres_db",
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="test_password_not_real",
            required=True,
        )

        assert config.service_name == "postgres_db"
        assert config.service_type == "database"
        # Check database attributes
        assert hasattr(config.connection_config, "host")
        assert config.connection_config.host == "localhost"
        assert config.connection_config.port == 5432
        assert config.connection_config.database == "testdb"
        assert config.health_check_enabled is True
        assert config.retry_config is not None


@pytest.mark.unit
class TestModelExternalServiceConfigIntegration:
    """Test integration scenarios and realistic use cases."""

    def test_rest_api_with_bearer_auth_configuration(self):
        """Test typical REST API with Bearer authentication."""
        config = ModelExternalServiceConfig(
            service_name="external_api",
            service_type="rest_api",
            connection_config={
                "base_url": "https://api.example.com/v1",
                "bearer_token": "bearer_token",
                "timeout_seconds": 30,
            },
            health_check_enabled=True,
            health_check_timeout=5,
        )

        assert config.service_type == "rest_api"
        assert config.connection_config.get_authentication_type() == "bearer_token"
        assert config.connection_config.has_authentication()

    def test_database_with_connection_pooling(self):
        """Test database configuration."""
        retry_config = ModelRetryConfig.create_standard()
        config = ModelExternalServiceConfig(
            service_name="primary_db",
            service_type="database",
            connection_config={
                "host": "db.example.com",
                "port": 5432,
                "database": "production",
                "username": "app_user",
                "password": "secret",
                "connection_timeout": 30,
            },
            health_check_enabled=True,
            retry_config=retry_config,
            required=True,
        )

        assert config.service_type == "database"
        assert config.connection_config.host == "db.example.com"
        assert config.required is True

    def test_public_api_with_no_auth(self):
        """Test public API with no authentication."""
        config = ModelExternalServiceConfig(
            service_name="public_service",
            service_type="rest_api",
            connection_config={
                "base_url": "https://public-api.example.com",
                "timeout_seconds": 30,
            },
        )

        assert config.connection_config.get_authentication_type() == "none"
        assert not config.connection_config.has_authentication()
