"""
Tests for ModelExternalServiceConfig.

Validates external service configuration model including authentication methods,
rate limiting, connection pooling, and enum-based field validation.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_auth_type import EnumAuthType
from omnibase_core.models.service.model_external_service_config import (
    ModelExternalServiceConfig,
)


class TestModelExternalServiceConfigBasic:
    """Test basic external service configuration functionality."""

    def test_minimal_required_configuration(self):
        """Test configuration with only required fields."""
        config = ModelExternalServiceConfig(service_type="rest_api")

        assert config.service_type == "rest_api"
        assert config.endpoint_url is None
        assert config.authentication_method == EnumAuthType.NONE
        assert config.rate_limit_enabled is True
        assert config.rate_limit_requests_per_minute == 60
        assert config.connection_pooling_enabled is True
        assert config.max_connections == 10
        assert config.timeout_seconds == 30

    def test_default_configuration_values(self):
        """Test default values for external service configuration."""
        config = ModelExternalServiceConfig(service_type="graphql")

        # Verify all defaults
        assert config.authentication_method == EnumAuthType.NONE
        assert config.rate_limit_enabled is True
        assert config.rate_limit_requests_per_minute == 60
        assert config.connection_pooling_enabled is True
        assert config.max_connections == 10
        assert config.timeout_seconds == 30

    def test_custom_configuration(self):
        """Test custom external service configuration."""
        config = ModelExternalServiceConfig(
            service_type="grpc",
            endpoint_url="https://api.example.com/v1",
            authentication_method=EnumAuthType.BEARER,
            rate_limit_enabled=False,
            rate_limit_requests_per_minute=120,
            connection_pooling_enabled=False,
            max_connections=20,
            timeout_seconds=60,
        )

        assert config.service_type == "grpc"
        assert config.endpoint_url == "https://api.example.com/v1"
        assert config.authentication_method == EnumAuthType.BEARER
        assert config.rate_limit_enabled is False
        assert config.rate_limit_requests_per_minute == 120
        assert config.connection_pooling_enabled is False
        assert config.max_connections == 20
        assert config.timeout_seconds == 60

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


class TestModelExternalServiceConfigEnumAuthType:
    """Test EnumAuthType enum validation and all auth type values."""

    def test_all_authentication_methods(self):
        """Test all available authentication methods from EnumAuthType."""
        auth_methods = [
            EnumAuthType.NONE,
            EnumAuthType.BASIC,
            EnumAuthType.BEARER,
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
            EnumAuthType.API_KEY,
            EnumAuthType.MTLS,
            EnumAuthType.DIGEST,
            EnumAuthType.CUSTOM,
        ]

        for auth_method in auth_methods:
            config = ModelExternalServiceConfig(
                service_type="rest_api",
                authentication_method=auth_method,
            )
            assert config.authentication_method == auth_method
            # Verify enum is preserved, not converted to string
            assert isinstance(config.authentication_method, EnumAuthType)

    def test_auth_type_enum_preserved_not_converted(self):
        """Test that EnumAuthType is preserved as enum, not converted to string."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            authentication_method=EnumAuthType.BEARER,
        )

        # Should be EnumAuthType enum, not string
        assert isinstance(config.authentication_method, EnumAuthType)
        assert config.authentication_method == EnumAuthType.BEARER
        assert config.authentication_method.value == "bearer"

    def test_invalid_enum_string_value_rejected(self):
        """Test that invalid string values for auth type are rejected."""
        # Invalid string should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ModelExternalServiceConfig(
                service_type="rest_api",
                authentication_method="invalid_auth_type",
            )

        error = exc_info.value
        assert "authentication_method" in str(error)

    def test_invalid_enum_numeric_value_rejected(self):
        """Test that numeric values for auth type are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExternalServiceConfig(
                service_type="rest_api",
                authentication_method=123,
            )

        error = exc_info.value
        assert "authentication_method" in str(error)

    def test_omit_enum_field_uses_default(self):
        """Test that omitting auth type uses the default."""
        # When field is not provided, default should be used
        config = ModelExternalServiceConfig(service_type="rest_api")

        # Should use default, which is EnumAuthType.NONE
        assert config.authentication_method == EnumAuthType.NONE

    def test_auth_type_by_string_value_accepted(self):
        """Test that valid enum string values are accepted and converted."""
        # Pydantic should convert valid string to enum
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            authentication_method="bearer",
        )

        assert config.authentication_method == EnumAuthType.BEARER
        assert isinstance(config.authentication_method, EnumAuthType)

    def test_auth_type_case_sensitivity(self):
        """Test enum validation case sensitivity."""
        # Lowercase should work (enum values are lowercase)
        config_lower = ModelExternalServiceConfig(
            service_type="rest_api",
            authentication_method="oauth2",
        )
        assert config_lower.authentication_method == EnumAuthType.OAUTH2

        # Uppercase should fail (not a valid enum value)
        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                authentication_method="OAUTH2",
            )

    def test_auth_type_enum_helper_methods(self):
        """Test EnumAuthType helper methods with config."""
        config_bearer = ModelExternalServiceConfig(
            service_type="rest_api",
            authentication_method=EnumAuthType.BEARER,
        )

        # Test helper methods
        assert EnumAuthType.requires_credentials(config_bearer.authentication_method)
        assert EnumAuthType.is_token_based(config_bearer.authentication_method)
        assert not EnumAuthType.is_certificate_based(
            config_bearer.authentication_method
        )

        config_mtls = ModelExternalServiceConfig(
            service_type="rest_api",
            authentication_method=EnumAuthType.MTLS,
        )
        assert EnumAuthType.is_certificate_based(config_mtls.authentication_method)


class TestModelExternalServiceConfigFieldValidation:
    """Test field validation rules and constraints."""

    def test_service_type_required(self):
        """Test service_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExternalServiceConfig()

        error = exc_info.value
        assert "service_type" in str(error)
        assert "Field required" in str(error)

    def test_service_type_min_length(self):
        """Test service_type must have at least 1 character."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelExternalServiceConfig(service_type="")

        error = exc_info.value
        assert "service_type" in str(error)

        # Valid single character
        config = ModelExternalServiceConfig(service_type="x")
        assert config.service_type == "x"

    def test_rate_limit_requests_per_minute_minimum(self):
        """Test rate_limit_requests_per_minute must be at least 1."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            rate_limit_requests_per_minute=1,
        )
        assert config.rate_limit_requests_per_minute == 1

        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                rate_limit_requests_per_minute=0,
            )

        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                rate_limit_requests_per_minute=-1,
            )

    def test_max_connections_minimum(self):
        """Test max_connections must be at least 1."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            max_connections=1,
        )
        assert config.max_connections == 1

        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                max_connections=0,
            )

        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                max_connections=-1,
            )

    def test_timeout_seconds_minimum(self):
        """Test timeout_seconds must be at least 1."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            timeout_seconds=1,
        )
        assert config.timeout_seconds == 1

        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                timeout_seconds=0,
            )

        with pytest.raises(ValidationError):
            ModelExternalServiceConfig(
                service_type="rest_api",
                timeout_seconds=-1,
            )

    def test_endpoint_url_optional(self):
        """Test endpoint_url is optional and can be None."""
        config_no_url = ModelExternalServiceConfig(service_type="rest_api")
        assert config_no_url.endpoint_url is None

        config_with_url = ModelExternalServiceConfig(
            service_type="rest_api",
            endpoint_url="https://api.example.com",
        )
        assert config_with_url.endpoint_url == "https://api.example.com"


class TestModelExternalServiceConfigRateLimiting:
    """Test rate limiting configuration."""

    def test_rate_limiting_enabled(self):
        """Test rate limiting enabled configuration."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            rate_limit_enabled=True,
            rate_limit_requests_per_minute=100,
        )

        assert config.rate_limit_enabled is True
        assert config.rate_limit_requests_per_minute == 100

    def test_rate_limiting_disabled(self):
        """Test rate limiting disabled configuration."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            rate_limit_enabled=False,
        )

        assert config.rate_limit_enabled is False
        # Rate limit value should still have default
        assert config.rate_limit_requests_per_minute == 60

    def test_high_rate_limit(self):
        """Test configuration with high rate limit."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            rate_limit_requests_per_minute=10000,
        )

        assert config.rate_limit_requests_per_minute == 10000


class TestModelExternalServiceConfigConnectionPooling:
    """Test connection pooling configuration."""

    def test_connection_pooling_enabled(self):
        """Test connection pooling enabled configuration."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_pooling_enabled=True,
            max_connections=50,
        )

        assert config.connection_pooling_enabled is True
        assert config.max_connections == 50

    def test_connection_pooling_disabled(self):
        """Test connection pooling disabled configuration."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            connection_pooling_enabled=False,
        )

        assert config.connection_pooling_enabled is False
        # Max connections should still have default
        assert config.max_connections == 10

    def test_large_connection_pool(self):
        """Test configuration with large connection pool."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            max_connections=1000,
        )

        assert config.max_connections == 1000


class TestModelExternalServiceConfigSerialization:
    """Test external service configuration serialization."""

    def test_model_dump(self):
        """Test serialization to dictionary."""
        config = ModelExternalServiceConfig(
            service_type="graphql",
            endpoint_url="https://graphql.example.com",
            authentication_method=EnumAuthType.JWT,
            rate_limit_requests_per_minute=200,
        )

        data = config.model_dump()

        assert data["service_type"] == "graphql"
        assert data["endpoint_url"] == "https://graphql.example.com"
        assert data["authentication_method"] == EnumAuthType.JWT
        assert data["rate_limit_requests_per_minute"] == 200

    def test_model_dump_json(self):
        """Test JSON serialization."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            authentication_method=EnumAuthType.OAUTH2,
        )

        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "service_type" in json_str
        assert "authentication_method" in json_str

    def test_round_trip_serialization(self):
        """Test serialization and deserialization."""
        original = ModelExternalServiceConfig(
            service_type="grpc",
            endpoint_url="grpc://service.example.com:50051",
            authentication_method=EnumAuthType.MTLS,
            rate_limit_enabled=False,
            rate_limit_requests_per_minute=500,
            connection_pooling_enabled=True,
            max_connections=25,
            timeout_seconds=45,
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelExternalServiceConfig.model_validate(data)

        assert restored.service_type == original.service_type
        assert restored.endpoint_url == original.endpoint_url
        assert restored.authentication_method == original.authentication_method
        assert restored.rate_limit_enabled == original.rate_limit_enabled
        assert (
            restored.rate_limit_requests_per_minute
            == original.rate_limit_requests_per_minute
        )
        assert (
            restored.connection_pooling_enabled == original.connection_pooling_enabled
        )
        assert restored.max_connections == original.max_connections
        assert restored.timeout_seconds == original.timeout_seconds


class TestModelExternalServiceConfigModelConfig:
    """Test model configuration settings."""

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            unknown_field="should_be_ignored",
            another_extra="also_ignored",
        )

        assert config.service_type == "rest_api"
        assert not hasattr(config, "unknown_field")
        assert not hasattr(config, "another_extra")

    def test_enum_values_not_converted(self):
        """Test that enum values are preserved."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            authentication_method=EnumAuthType.API_KEY,
        )

        # Enum should be preserved, not converted to string
        assert isinstance(config.authentication_method, EnumAuthType)
        assert config.authentication_method == EnumAuthType.API_KEY

    def test_validate_assignment(self):
        """Test that assignment validation is enabled."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            max_connections=10,
        )
        assert config.max_connections == 10

        # Should validate on assignment
        config.max_connections = 20
        assert config.max_connections == 20

        # Invalid assignment should fail
        with pytest.raises(ValidationError):
            config.max_connections = 0

        # Invalid enum assignment should fail
        with pytest.raises(ValidationError):
            config.authentication_method = "invalid_auth"


class TestModelExternalServiceConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_valid_configuration(self):
        """Test configuration with minimum valid values."""
        config = ModelExternalServiceConfig(
            service_type="x",
            rate_limit_requests_per_minute=1,
            max_connections=1,
            timeout_seconds=1,
        )

        assert config.service_type == "x"
        assert config.rate_limit_requests_per_minute == 1
        assert config.max_connections == 1
        assert config.timeout_seconds == 1

    def test_maximum_realistic_values(self):
        """Test configuration with high but realistic values."""
        config = ModelExternalServiceConfig(
            service_type="high_performance_api",
            rate_limit_requests_per_minute=100000,
            max_connections=10000,
            timeout_seconds=300,
        )

        assert config.rate_limit_requests_per_minute == 100000
        assert config.max_connections == 10000
        assert config.timeout_seconds == 300

    def test_all_features_disabled(self):
        """Test configuration with optional features disabled."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            rate_limit_enabled=False,
            connection_pooling_enabled=False,
        )

        assert config.rate_limit_enabled is False
        assert config.connection_pooling_enabled is False

    def test_all_features_enabled_custom_values(self):
        """Test configuration with all features enabled and custom values."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            endpoint_url="https://api.example.com/v2",
            authentication_method=EnumAuthType.BEARER,
            rate_limit_enabled=True,
            rate_limit_requests_per_minute=1000,
            connection_pooling_enabled=True,
            max_connections=100,
            timeout_seconds=120,
        )

        assert config.rate_limit_enabled is True
        assert config.connection_pooling_enabled is True
        assert config.rate_limit_requests_per_minute == 1000
        assert config.max_connections == 100
        assert config.timeout_seconds == 120

    def test_service_type_with_special_characters(self):
        """Test service_type with special characters."""
        special_types = [
            "rest-api",
            "rest_api",
            "REST-API-V2",
            "service.type.v1",
            "service/type/v1",
        ]

        for service_type in special_types:
            config = ModelExternalServiceConfig(service_type=service_type)
            assert config.service_type == service_type

    def test_various_url_formats(self):
        """Test different endpoint URL formats."""
        urls = [
            "https://api.example.com",
            "http://localhost:8080",
            "grpc://service.example.com:50051",
            "ws://websocket.example.com",
            "https://api.example.com/v1/endpoint?param=value",
        ]

        for url in urls:
            config = ModelExternalServiceConfig(
                service_type="rest_api",
                endpoint_url=url,
            )
            assert config.endpoint_url == url


class TestModelExternalServiceConfigIntegration:
    """Test integration scenarios and realistic use cases."""

    def test_rest_api_with_bearer_auth_configuration(self):
        """Test typical REST API with Bearer authentication."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            endpoint_url="https://api.example.com/v1",
            authentication_method=EnumAuthType.BEARER,
            rate_limit_enabled=True,
            rate_limit_requests_per_minute=100,
            connection_pooling_enabled=True,
            max_connections=20,
            timeout_seconds=30,
        )

        assert config.service_type == "rest_api"
        assert config.authentication_method == EnumAuthType.BEARER
        assert EnumAuthType.is_token_based(config.authentication_method)

    def test_graphql_with_jwt_configuration(self):
        """Test typical GraphQL with JWT authentication."""
        config = ModelExternalServiceConfig(
            service_type="graphql",
            endpoint_url="https://graphql.example.com/query",
            authentication_method=EnumAuthType.JWT,
            rate_limit_enabled=True,
            rate_limit_requests_per_minute=50,
            timeout_seconds=60,
        )

        assert config.service_type == "graphql"
        assert config.authentication_method == EnumAuthType.JWT
        assert EnumAuthType.supports_refresh(config.authentication_method)

    def test_grpc_with_mtls_configuration(self):
        """Test typical gRPC with mTLS authentication."""
        config = ModelExternalServiceConfig(
            service_type="grpc",
            endpoint_url="grpc://secure.example.com:50051",
            authentication_method=EnumAuthType.MTLS,
            rate_limit_enabled=False,
            connection_pooling_enabled=True,
            max_connections=50,
            timeout_seconds=90,
        )

        assert config.service_type == "grpc"
        assert config.authentication_method == EnumAuthType.MTLS
        assert EnumAuthType.is_certificate_based(config.authentication_method)

    def test_public_api_with_no_auth(self):
        """Test public API with no authentication."""
        config = ModelExternalServiceConfig(
            service_type="rest_api",
            endpoint_url="https://public-api.example.com",
            authentication_method=EnumAuthType.NONE,
            rate_limit_enabled=True,
            rate_limit_requests_per_minute=300,
        )

        assert config.authentication_method == EnumAuthType.NONE
        assert not EnumAuthType.requires_credentials(config.authentication_method)
