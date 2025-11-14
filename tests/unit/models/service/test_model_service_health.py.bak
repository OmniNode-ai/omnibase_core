"""
Unit tests for ModelServiceHealth.

Tests all aspects of the service health monitoring model including:
- Model instantiation and validation
- Field validation and type checking
- Credential masking in connection strings
- Health status analysis methods
- Connection security analysis
- Performance categorization
- Reliability scoring
- Business impact assessment
- Factory methods
- Edge cases and error conditions
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_impact_severity import EnumImpactSeverity
from omnibase_core.enums.enum_service_health_status import EnumServiceHealthStatus
from omnibase_core.enums.enum_service_type import EnumServiceType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.service.model_service_health import ModelServiceHealth


class TestModelServiceHealthInstantiation:
    """Test cases for ModelServiceHealth instantiation and basic validation."""

    def test_model_instantiation_valid_data(self):
        """Test that model can be instantiated with valid minimal data."""
        service = ModelServiceHealth(
            service_name="postgres_main",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost:5432/mydb",
        )

        assert service.service_name == "postgres_main"
        assert service.service_type == EnumServiceType.POSTGRESQL
        assert service.status == EnumServiceHealthStatus.REACHABLE
        assert service.connection_string == "postgresql://localhost:5432/mydb"
        assert service.consecutive_failures == 0

    def test_model_instantiation_all_fields(self):
        """Test model instantiation with all fields populated."""
        service = ModelServiceHealth(
            service_name="redis_cache",
            service_type=EnumServiceType.REDIS,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="redis://localhost:6379",
            error_message=None,
            error_code=None,
            last_check_time="2024-01-15T10:30:00Z",
            response_time_ms=150,
            consecutive_failures=0,
            uptime_seconds=86400,
            version=ModelSemVer(major=7, minor=0, patch=5),
            endpoint_url="https://redis.example.com",
            port=6379,
            ssl_enabled=True,
            authentication_type="password",
            dependencies=["network", "storage"],
        )

        assert service.service_name == "redis_cache"
        assert service.response_time_ms == 150
        assert service.uptime_seconds == 86400
        assert service.version.major == 7
        assert service.port == 6379
        assert service.ssl_enabled is True
        assert len(service.dependencies) == 2

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing service_name
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceHealth(
                service_type=EnumServiceType.KAFKA,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="kafka://localhost:9092",
            )
        assert "service_name" in str(exc_info.value)

        # Missing service_type
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceHealth(
                service_name="kafka_main",
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="kafka://localhost:9092",
            )
        assert "service_type" in str(exc_info.value)

        # Missing status
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceHealth(
                service_name="kafka_main",
                service_type=EnumServiceType.KAFKA,
                connection_string="kafka://localhost:9092",
            )
        assert "status" in str(exc_info.value)

        # Missing connection_string
        with pytest.raises(ValidationError) as exc_info:
            ModelServiceHealth(
                service_name="kafka_main",
                service_type=EnumServiceType.KAFKA,
                status=EnumServiceHealthStatus.REACHABLE,
            )
        assert "connection_string" in str(exc_info.value)

    def test_all_service_types(self):
        """Test instantiation with all valid service types."""
        service_types = [
            EnumServiceType.KAFKA,
            EnumServiceType.POSTGRESQL,
            EnumServiceType.MYSQL,
            EnumServiceType.REDIS,
            EnumServiceType.ELASTICSEARCH,
            EnumServiceType.MONGODB,
            EnumServiceType.REST_API,
            EnumServiceType.GRPC,
            EnumServiceType.RABBITMQ,
            EnumServiceType.CONSUL,
            EnumServiceType.VAULT,
            EnumServiceType.S3,
            EnumServiceType.CUSTOM,
        ]

        for service_type in service_types:
            service = ModelServiceHealth(
                service_name=f"test_{service_type.value}",
                service_type=service_type,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string=f"{service_type.value}://localhost",
            )
            assert service.service_type == service_type

    def test_all_health_statuses(self):
        """Test instantiation with all valid health statuses."""
        statuses = [
            EnumServiceHealthStatus.REACHABLE,
            EnumServiceHealthStatus.UNREACHABLE,
            EnumServiceHealthStatus.ERROR,
            EnumServiceHealthStatus.DEGRADED,
            EnumServiceHealthStatus.TIMEOUT,
            EnumServiceHealthStatus.AUTHENTICATING,
            EnumServiceHealthStatus.MAINTENANCE,
        ]

        for status in statuses:
            service = ModelServiceHealth(
                service_name="test_service",
                service_type=EnumServiceType.POSTGRESQL,
                status=status,
                connection_string="postgresql://localhost:5432/db",
            )
            assert service.status == status


class TestModelServiceHealthValidators:
    """Test field validators for ModelServiceHealth."""

    def test_service_name_validator_valid_names(self):
        """Test service_name validator with valid names."""
        valid_names = [
            "postgres",
            "redis_cache",
            "kafka-main",
            "mysql.primary",
            "s3Storage",
            "api_gateway-v2",
            "service123",
            "a",
            "A1",
        ]

        for name in valid_names:
            service = ModelServiceHealth(
                service_name=name,
                service_type=EnumServiceType.CUSTOM,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="custom://localhost",
            )
            assert service.service_name == name

    def test_service_name_validator_invalid_names(self):
        """Test service_name validator with invalid names."""
        # Empty or whitespace
        with pytest.raises(ModelOnexError) as exc_info:
            ModelServiceHealth(
                service_name="",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelServiceHealth(
                service_name="   ",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

        # Starting with number
        with pytest.raises(ModelOnexError) as exc_info:
            ModelServiceHealth(
                service_name="123service",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must start with letter" in str(exc_info.value)

        # Invalid characters
        invalid_names = [
            "_service",
            "-service",
            ".service",
            "service name",
            "service@host",
            "service#1",
        ]

        for name in invalid_names:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelServiceHealth(
                    service_name=name,
                    service_type=EnumServiceType.POSTGRESQL,
                    status=EnumServiceHealthStatus.REACHABLE,
                    connection_string="postgresql://localhost",
                )
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_service_name_whitespace_trimming(self):
        """Test that service_name trims whitespace."""
        service = ModelServiceHealth(
            service_name="  postgres_main  ",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )
        assert service.service_name == "postgres_main"

    def test_connection_string_validator_credential_masking(self):
        """Test connection_string validator masks credentials."""
        # Test password masking
        service = ModelServiceHealth(
            service_name="postgres",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://user:secretpass@localhost:5432/db",
        )
        assert "secretpass" not in service.connection_string
        assert "***" in service.connection_string

        # Test various credential patterns
        credential_patterns = [
            ("mysql://root:password=secret123@host", "secret123"),
            ("redis://:pwd=mypass@localhost", "mypass"),
            ("api://key=abc123xyz", "abc123xyz"),
            ("service://token=bearer_token", "bearer_token"),
        ]

        for conn_str, secret in credential_patterns:
            service = ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.CUSTOM,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string=conn_str,
            )
            # The secret should be masked
            assert (
                secret not in service.connection_string
                or "***" in service.connection_string
            )

    def test_connection_string_validator_empty_or_whitespace(self):
        """Test connection_string validator rejects empty strings."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelServiceHealth(
                service_name="postgres",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelServiceHealth(
                service_name="postgres",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="   ",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_endpoint_url_validator_valid_urls(self):
        """Test endpoint_url validator with valid URLs."""
        valid_urls = [
            "http://localhost:8080",
            "https://api.example.com",
            "https://service.local:9090/health",
            "http://192.168.1.100:3000",
            "https://db.cluster.internal",
        ]

        for url in valid_urls:
            service = ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="http://localhost",
                endpoint_url=url,
            )
            assert service.endpoint_url == url

    def test_endpoint_url_validator_invalid_urls(self):
        """Test endpoint_url validator with invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "localhost:8080",  # Missing scheme
            "://localhost",  # Missing scheme
            "http://",  # Missing netloc
        ]

        for url in invalid_urls:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelServiceHealth(
                    service_name="test",
                    service_type=EnumServiceType.REST_API,
                    status=EnumServiceHealthStatus.REACHABLE,
                    connection_string="http://localhost",
                    endpoint_url=url,
                )
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "valid URL" in str(exc_info.value)

    def test_endpoint_url_validator_none_or_empty(self):
        """Test endpoint_url validator handles None and empty strings."""
        # None should be allowed
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            endpoint_url=None,
        )
        assert service.endpoint_url is None

        # Empty string should be converted to None
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            endpoint_url="",
        )
        assert service.endpoint_url is None

    def test_last_check_time_validator_valid_timestamps(self):
        """Test last_check_time validator with valid ISO timestamps."""
        valid_timestamps = [
            "2024-01-15T10:30:00Z",
            "2024-01-15T10:30:00+00:00",
            "2024-01-15T10:30:00.123456Z",
            "2024-01-15T10:30:00",
            datetime.now().isoformat(),
        ]

        for timestamp in valid_timestamps:
            service = ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
                last_check_time=timestamp,
            )
            assert service.last_check_time == timestamp

    def test_last_check_time_validator_invalid_timestamps(self):
        """Test last_check_time validator with invalid timestamps."""
        invalid_timestamps = [
            "not-a-timestamp",
            "2024-13-01T10:30:00",  # Invalid month
            "2024-01-32T10:30:00",  # Invalid day
            "2024-01-15 10:30:00",  # Wrong format
            "01/15/2024",
        ]

        for timestamp in invalid_timestamps:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelServiceHealth(
                    service_name="test",
                    service_type=EnumServiceType.POSTGRESQL,
                    status=EnumServiceHealthStatus.REACHABLE,
                    connection_string="postgresql://localhost",
                    last_check_time=timestamp,
                )
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "valid ISO timestamp" in str(exc_info.value)

    def test_field_constraints_validation(self):
        """Test field constraints (min_length, max_length, ge, le)."""
        # response_time_ms must be >= 0
        with pytest.raises(ValidationError):
            ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
                response_time_ms=-1,
            )

        # consecutive_failures must be >= 0
        with pytest.raises(ValidationError):
            ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
                consecutive_failures=-1,
            )

        # port must be 1-65535
        with pytest.raises(ValidationError):
            ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
                port=0,
            )

        with pytest.raises(ValidationError):
            ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost",
                port=65536,
            )

        # Valid port range
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            port=5432,
        )
        assert service.port == 5432


class TestModelServiceHealthStatusMethods:
    """Test health status analysis methods."""

    def test_is_healthy(self):
        """Test is_healthy() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )
        assert service.is_healthy() is True

        # Unhealthy states
        for status in [
            EnumServiceHealthStatus.ERROR,
            EnumServiceHealthStatus.UNREACHABLE,
            EnumServiceHealthStatus.TIMEOUT,
            EnumServiceHealthStatus.DEGRADED,
        ]:
            service.status = status
            assert service.is_healthy() is False

    def test_is_unhealthy(self):
        """Test is_unhealthy() method."""
        unhealthy_statuses = [
            EnumServiceHealthStatus.ERROR,
            EnumServiceHealthStatus.UNREACHABLE,
            EnumServiceHealthStatus.TIMEOUT,
        ]

        for status in unhealthy_statuses:
            service = ModelServiceHealth(
                service_name="test",
                service_type=EnumServiceType.POSTGRESQL,
                status=status,
                connection_string="postgresql://localhost",
            )
            assert service.is_unhealthy() is True

        # Healthy state
        service.status = EnumServiceHealthStatus.REACHABLE
        assert service.is_unhealthy() is False

        # Degraded is not unhealthy
        service.status = EnumServiceHealthStatus.DEGRADED
        assert service.is_unhealthy() is False

    def test_is_degraded(self):
        """Test is_degraded() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.DEGRADED,
            connection_string="postgresql://localhost",
        )
        assert service.is_degraded() is True

        service.status = EnumServiceHealthStatus.REACHABLE
        assert service.is_degraded() is False

    def test_requires_attention_unhealthy(self):
        """Test requires_attention() for unhealthy services."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.ERROR,
            connection_string="postgresql://localhost",
        )
        assert service.requires_attention() is True

    def test_requires_attention_consecutive_failures(self):
        """Test requires_attention() for consecutive failures threshold."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            consecutive_failures=2,
        )
        assert service.requires_attention() is False

        service.consecutive_failures = 3
        assert service.requires_attention() is True

    def test_requires_attention_slow_response(self):
        """Test requires_attention() for slow response times."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            response_time_ms=29999,
        )
        assert service.requires_attention() is False

        service.response_time_ms = 30001
        assert service.requires_attention() is True

    def test_get_severity_level(self):
        """Test get_severity_level() method."""
        # Critical - ERROR status
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.ERROR,
            connection_string="postgresql://localhost",
        )
        assert service.get_severity_level() == "critical"

        # High - UNREACHABLE
        service.status = EnumServiceHealthStatus.UNREACHABLE
        assert service.get_severity_level() == "high"

        # High - TIMEOUT
        service.status = EnumServiceHealthStatus.TIMEOUT
        assert service.get_severity_level() == "high"

        # Medium - DEGRADED
        service.status = EnumServiceHealthStatus.DEGRADED
        assert service.get_severity_level() == "medium"

        # Low - requires attention but not unhealthy
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            consecutive_failures=3,
        )
        assert service.get_severity_level() == "low"

        # Info - healthy
        service.consecutive_failures = 0
        assert service.get_severity_level() == "info"


class TestModelServiceHealthConnectionAnalysis:
    """Test connection analysis methods."""

    def test_get_connection_type_secure(self):
        """Test get_connection_type() for secure connections."""
        # SSL in connection string
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost:5432?ssl=true",
        )
        assert service.get_connection_type() == "secure"

        # TLS in connection string
        service.connection_string = "mysql://localhost:3306?tls=true"
        assert service.get_connection_type() == "secure"

        # HTTPS URL
        service.connection_string = "https://api.example.com"
        assert service.get_connection_type() == "secure"

        # ssl_enabled flag
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            ssl_enabled=True,
        )
        assert service.get_connection_type() == "secure"

    def test_get_connection_type_insecure(self):
        """Test get_connection_type() for insecure connections."""
        # HTTP URL
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="http://api.example.com",
        )
        assert service.get_connection_type() == "insecure"

        # ssl_enabled=False
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            ssl_enabled=False,
        )
        assert service.get_connection_type() == "insecure"

    def test_get_connection_type_unknown(self):
        """Test get_connection_type() for unknown connections."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.CUSTOM,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="custom://localhost",
        )
        assert service.get_connection_type() == "unknown"

    def test_is_secure_connection(self):
        """Test is_secure_connection() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost?ssl=true",
        )
        assert service.is_secure_connection() is True

        service.connection_string = "http://localhost"
        assert service.is_secure_connection() is False

    def test_get_security_recommendations_no_ssl(self):
        """Test get_security_recommendations() for non-SSL connections."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="http://localhost",
        )
        recommendations = service.get_security_recommendations()
        assert len(recommendations) > 0
        assert any("SSL/TLS" in r for r in recommendations)

    def test_get_security_recommendations_no_auth(self):
        """Test get_security_recommendations() for missing authentication."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://localhost",
            authentication_type=None,
        )
        recommendations = service.get_security_recommendations()
        assert any("authentication" in r.lower() for r in recommendations)

    def test_get_security_recommendations_weak_auth(self):
        """Test get_security_recommendations() for weak authentication."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://localhost",
            authentication_type="basic",
        )
        recommendations = service.get_security_recommendations()
        assert any("stronger authentication" in r.lower() for r in recommendations)

    def test_get_security_recommendations_credentials_in_string(self):
        """Test get_security_recommendations() for credentials in connection string."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://user:password=secret@localhost",
        )
        recommendations = service.get_security_recommendations()
        assert any(
            "credentials" in r.lower() or "masked" in r.lower() for r in recommendations
        )


class TestModelServiceHealthPerformanceAnalysis:
    """Test performance analysis methods."""

    def test_get_performance_category(self):
        """Test get_performance_category() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        # Unknown - no response time
        assert service.get_performance_category() == "unknown"

        # Excellent - < 100ms
        service.response_time_ms = 50
        assert service.get_performance_category() == "excellent"

        # Good - < 500ms
        service.response_time_ms = 300
        assert service.get_performance_category() == "good"

        # Acceptable - < 2000ms
        service.response_time_ms = 1500
        assert service.get_performance_category() == "acceptable"

        # Slow - < 10000ms
        service.response_time_ms = 5000
        assert service.get_performance_category() == "slow"

        # Very slow - >= 10000ms
        service.response_time_ms = 15000
        assert service.get_performance_category() == "very_slow"

    def test_is_performance_concerning(self):
        """Test is_performance_concerning() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            response_time_ms=300,
        )
        assert service.is_performance_concerning() is False

        service.response_time_ms = 5000  # slow
        assert service.is_performance_concerning() is True

        service.response_time_ms = 15000  # very_slow
        assert service.is_performance_concerning() is True

    def test_get_response_time_human(self):
        """Test get_response_time_human() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        # No response time
        assert service.get_response_time_human() == "unknown"

        # Milliseconds
        service.response_time_ms = 150
        assert service.get_response_time_human() == "150ms"

        # Seconds
        service.response_time_ms = 1500
        assert service.get_response_time_human() == "1.50s"

        service.response_time_ms = 5432
        assert service.get_response_time_human() == "5.43s"

    def test_get_uptime_human(self):
        """Test get_uptime_human() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        # No uptime
        assert service.get_uptime_human() == "unknown"

        # Seconds
        service.uptime_seconds = 45
        assert service.get_uptime_human() == "45s"

        # Minutes
        service.uptime_seconds = 300  # 5 minutes
        assert service.get_uptime_human() == "5m"

        # Hours
        service.uptime_seconds = 7200  # 2 hours
        assert service.get_uptime_human() == "2h"

        # Days
        service.uptime_seconds = 172800  # 2 days
        assert service.get_uptime_human() == "2d"


class TestModelServiceHealthReliabilityAnalysis:
    """Test reliability analysis methods."""

    def test_calculate_reliability_score_healthy(self):
        """Test calculate_reliability_score() for healthy service."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            consecutive_failures=0,
            response_time_ms=100,
        )
        score = service.calculate_reliability_score()
        assert score == 1.0

    def test_calculate_reliability_score_consecutive_failures(self):
        """Test calculate_reliability_score() with consecutive failures."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            consecutive_failures=3,
        )
        score = service.calculate_reliability_score()
        # Score should be reduced by 0.3 (3 * 0.1)
        assert score == pytest.approx(0.7, rel=0.01)

    def test_calculate_reliability_score_poor_performance(self):
        """Test calculate_reliability_score() with poor performance."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            response_time_ms=15000,  # very_slow
        )
        score = service.calculate_reliability_score()
        # Score should be reduced by 30% for poor performance
        assert score == pytest.approx(0.7, rel=0.01)

    def test_calculate_reliability_score_error_status(self):
        """Test calculate_reliability_score() for ERROR status."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.ERROR,
            connection_string="postgresql://localhost",
        )
        score = service.calculate_reliability_score()
        assert score == 0.0

    def test_calculate_reliability_score_timeout_status(self):
        """Test calculate_reliability_score() for TIMEOUT status."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.TIMEOUT,
            connection_string="postgresql://localhost",
        )
        score = service.calculate_reliability_score()
        # Base score 0.0 for unhealthy, then multiply by 0.3
        assert score == 0.0

    def test_calculate_reliability_score_degraded_status(self):
        """Test calculate_reliability_score() for DEGRADED status."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.DEGRADED,
            connection_string="postgresql://localhost",
        )
        score = service.calculate_reliability_score()
        # Base score 0.0, then multiply by 0.5
        assert score == 0.0

    def test_get_availability_category(self):
        """Test get_availability_category() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        # No failures - highly available
        service.consecutive_failures = 0
        assert service.get_availability_category() == "highly_available"

        # 1 failure - available
        service.consecutive_failures = 1
        assert service.get_availability_category() == "available"

        # 3 failures - unstable
        service.consecutive_failures = 3
        assert service.get_availability_category() == "unstable"

        # 5+ failures - unavailable
        service.consecutive_failures = 5
        assert service.get_availability_category() == "unavailable"


class TestModelServiceHealthBusinessIntelligence:
    """Test business intelligence methods."""

    def test_get_business_impact_unhealthy(self):
        """Test get_business_impact() for unhealthy service."""
        service = ModelServiceHealth(
            service_name="critical_db",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.ERROR,
            connection_string="postgresql://localhost",
            consecutive_failures=3,
        )
        impact = service.get_business_impact()
        assert impact.severity == EnumImpactSeverity.CRITICAL
        assert "critical_db" in impact.affected_services
        assert impact.sla_violated is True
        assert impact.downtime_minutes == 15.0  # 3 failures * 5 minutes

    def test_get_business_impact_degraded(self):
        """Test get_business_impact() for degraded service."""
        service = ModelServiceHealth(
            service_name="cache",
            service_type=EnumServiceType.REDIS,
            status=EnumServiceHealthStatus.DEGRADED,
            connection_string="redis://localhost",
        )
        impact = service.get_business_impact()
        assert impact.severity == EnumImpactSeverity.HIGH
        assert impact.sla_violated is False

    def test_get_business_impact_requires_attention(self):
        """Test get_business_impact() for service requiring attention."""
        service = ModelServiceHealth(
            service_name="api",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://api.example.com",
            consecutive_failures=3,
        )
        impact = service.get_business_impact()
        assert impact.severity == EnumImpactSeverity.MEDIUM

    def test_get_business_impact_healthy(self):
        """Test get_business_impact() for healthy service."""
        service = ModelServiceHealth(
            service_name="db",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )
        impact = service.get_business_impact()
        assert impact.severity == EnumImpactSeverity.MINIMAL
        assert impact.sla_violated is False

    def test_assess_performance_impact(self):
        """Test _assess_performance_impact() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        # Unhealthy - high negative
        service.status = EnumServiceHealthStatus.ERROR
        assert service._assess_performance_impact() == "high_negative"

        # Poor performance - medium negative
        service.status = EnumServiceHealthStatus.REACHABLE
        service.response_time_ms = 15000
        assert service._assess_performance_impact() == "medium_negative"

        # Good performance - positive
        service.response_time_ms = 50
        assert service._assess_performance_impact() == "positive"

        # Acceptable performance - neutral
        service.response_time_ms = 1500
        assert service._assess_performance_impact() == "neutral"

    def test_assess_security_risk(self):
        """Test _assess_security_risk() method."""
        # High risk - no SSL
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="http://localhost",
        )
        assert service._assess_security_risk() == "high"

        # Medium risk - basic auth
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://localhost",
            authentication_type="basic",
        )
        assert service._assess_security_risk() == "medium"

        # Medium risk - no auth
        service.authentication_type = None
        assert service._assess_security_risk() == "medium"

        # Low risk - secure with strong auth
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://localhost",
            ssl_enabled=True,
            authentication_type="oauth2",
        )
        assert service._assess_security_risk() == "low"

    def test_estimate_operational_cost(self):
        """Test _estimate_operational_cost() method."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        # High cost - many failures
        service.consecutive_failures = 5
        assert service._estimate_operational_cost() == "high"

        # Medium cost - slow response
        service.consecutive_failures = 0
        service.response_time_ms = 35000
        assert service._estimate_operational_cost() == "medium"

        # Low cost - degraded
        service.response_time_ms = 100
        service.status = EnumServiceHealthStatus.DEGRADED
        assert service._estimate_operational_cost() == "low"

        # Minimal cost - healthy
        service.status = EnumServiceHealthStatus.REACHABLE
        assert service._estimate_operational_cost() == "minimal"


class TestModelServiceHealthFactoryMethods:
    """Test factory methods."""

    @patch("omnibase_core.models.service.model_service_health.datetime")
    def test_create_healthy(self, mock_datetime):
        """Test create_healthy() factory method."""
        mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00"

        service = ModelServiceHealth.create_healthy(
            service_name="postgres_main",
            service_type="postgresql",
            connection_string="postgresql://localhost:5432/db",
            response_time_ms=150,
        )

        assert service.service_name == "postgres_main"
        assert service.service_type == EnumServiceType.POSTGRESQL
        assert service.status == EnumServiceHealthStatus.REACHABLE
        assert service.connection_string == "postgresql://localhost:5432/db"
        assert service.response_time_ms == 150
        assert service.consecutive_failures == 0
        assert service.last_check_time == "2024-01-15T10:30:00"

    @patch("omnibase_core.models.service.model_service_health.datetime")
    def test_create_error(self, mock_datetime):
        """Test create_error() factory method."""
        mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00"

        service = ModelServiceHealth.create_error(
            service_name="postgres_main",
            service_type="postgresql",
            connection_string="postgresql://localhost:5432/db",
            error_message="Connection refused",
            error_code="CONN_REFUSED",
        )

        assert service.service_name == "postgres_main"
        assert service.service_type == EnumServiceType.POSTGRESQL
        assert service.status == EnumServiceHealthStatus.ERROR
        assert service.error_message == "Connection refused"
        assert service.error_code == "CONN_REFUSED"
        assert service.consecutive_failures == 1
        assert service.last_check_time == "2024-01-15T10:30:00"

    @patch("omnibase_core.models.service.model_service_health.datetime")
    def test_create_timeout(self, mock_datetime):
        """Test create_timeout() factory method."""
        mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00"

        service = ModelServiceHealth.create_timeout(
            service_name="slow_api",
            service_type="rest_api",
            connection_string="https://api.example.com",
            timeout_ms=30000,
        )

        assert service.service_name == "slow_api"
        assert service.service_type == EnumServiceType.REST_API
        assert service.status == EnumServiceHealthStatus.TIMEOUT
        assert "timeout after 30000ms" in service.error_message.lower()
        assert service.response_time_ms == 30000
        assert service.consecutive_failures == 1
        assert service.last_check_time == "2024-01-15T10:30:00"


class TestModelServiceHealthEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_values_for_optional_fields(self):
        """Test that None values are properly handled for optional fields."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            error_message=None,
            error_code=None,
            last_check_time=None,
            response_time_ms=None,
            uptime_seconds=None,
            version=None,
            endpoint_url=None,
            port=None,
            ssl_enabled=None,
            authentication_type=None,
            dependencies=None,
        )

        assert service.error_message is None
        assert service.error_code is None
        assert service.response_time_ms is None

    def test_extreme_response_times(self):
        """Test handling of extreme response times."""
        # Very fast
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.REDIS,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="redis://localhost",
            response_time_ms=1,
        )
        assert service.get_performance_category() == "excellent"

        # Very slow
        service.response_time_ms = 999999
        assert service.get_performance_category() == "very_slow"

    def test_extreme_consecutive_failures(self):
        """Test handling of extreme consecutive failure counts."""
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            consecutive_failures=100,
        )
        assert service.requires_attention() is True
        score = service.calculate_reliability_score()
        assert score == 0.0  # Should be capped at 0.0

    def test_extreme_uptime(self):
        """Test handling of extreme uptime values."""
        # Very short uptime
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
            uptime_seconds=1,
        )
        assert service.get_uptime_human() == "1s"

        # Very long uptime (1 year)
        service.uptime_seconds = 31536000
        assert "d" in service.get_uptime_human()

    def test_max_length_constraints(self):
        """Test maximum length constraints on fields."""
        # service_name max_length=100
        long_name = "a" * 100
        service = ModelServiceHealth(
            service_name=long_name,
            service_type=EnumServiceType.CUSTOM,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="custom://localhost",
        )
        assert len(service.service_name) == 100

        # Over max length should fail
        with pytest.raises(ValidationError):
            ModelServiceHealth(
                service_name="a" * 101,
                service_type=EnumServiceType.CUSTOM,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="custom://localhost",
            )

    def test_serialization_deserialization(self):
        """Test model serialization and deserialization."""
        original = ModelServiceHealth(
            service_name="postgres",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost:5432/db",
            response_time_ms=150,
            consecutive_failures=0,
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["service_name"] == "postgres"
        assert data["response_time_ms"] == 150

        # Deserialize from dict
        restored = ModelServiceHealth.model_validate(data)
        assert restored.service_name == original.service_name
        assert restored.service_type == original.service_type
        assert restored.status == original.status

    def test_json_serialization_deserialization(self):
        """Test JSON serialization and deserialization."""
        original = ModelServiceHealth(
            service_name="redis",
            service_type=EnumServiceType.REDIS,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="redis://localhost:6379",
            response_time_ms=50,
        )

        # Serialize to JSON
        json_str = original.model_dump_json()
        assert isinstance(json_str, str)
        assert "redis" in json_str

        # Deserialize from JSON
        restored = ModelServiceHealth.model_validate_json(json_str)
        assert restored.service_name == original.service_name
        assert restored.response_time_ms == original.response_time_ms

    def test_model_equality(self):
        """Test model equality comparison."""
        service1 = ModelServiceHealth(
            service_name="postgres",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        service2 = ModelServiceHealth(
            service_name="postgres",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )

        service3 = ModelServiceHealth(
            service_name="mysql",
            service_type=EnumServiceType.MYSQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="mysql://localhost",
        )

        # Due to consecutive_failures default, these should be equal
        assert service1 == service2
        assert service1 != service3

    def test_dependencies_field(self):
        """Test dependencies field handling."""
        # Default empty list
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost",
        )
        assert service.dependencies == []

        # With dependencies
        service = ModelServiceHealth(
            service_name="test",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://api.example.com",
            dependencies=["database", "cache", "auth_service"],
        )
        assert len(service.dependencies) == 3
        assert "cache" in service.dependencies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
