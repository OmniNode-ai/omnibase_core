#!/usr/bin/env python3
"""
Integration tests for service orchestration and coordination.

Tests real-world scenarios with actual service instances, no mocking.
Validates service health monitoring, lifecycle management, and multi-service coordination.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_service_health_status import EnumServiceHealthStatus
from omnibase_core.enums.enum_service_type import EnumServiceType
from omnibase_core.errors import EnumCoreErrorCode, OnexError
from omnibase_core.models.container.model_service import ModelService
from omnibase_core.models.service.model_service_health import ModelServiceHealth


class TestServiceHealthLifecycle:
    """Test complete service health monitoring lifecycle."""

    def test_healthy_service_creation_and_analysis(self):
        """Test creating and analyzing a healthy service."""
        # Create healthy service
        service = ModelServiceHealth.create_healthy(
            service_name="postgres_db",
            service_type="postgresql",
            connection_string="postgresql://***:***@localhost:5432/mydb",
            response_time_ms=50,
        )

        # Verify basic properties
        assert service.service_name == "postgres_db"
        assert service.service_type == EnumServiceType.POSTGRESQL
        assert service.status == EnumServiceHealthStatus.REACHABLE
        assert service.response_time_ms == 50
        assert service.consecutive_failures == 0

        # Verify health checks
        assert service.is_healthy()
        assert not service.is_unhealthy()
        assert not service.is_degraded()
        assert not service.requires_attention()

        # Verify performance analysis
        assert service.get_performance_category() == "excellent"
        assert not service.is_performance_concerning()
        assert service.get_response_time_human() == "50ms"

        # Verify reliability
        reliability = service.calculate_reliability_score()
        assert reliability == 1.0
        assert service.get_availability_category() == "highly_available"

    def test_error_service_creation_and_analysis(self):
        """Test creating and analyzing an error service."""
        # Create error service
        service = ModelServiceHealth.create_error(
            service_name="redis_cache",
            service_type="redis",
            connection_string="redis://***:***@localhost:6379",
            error_message="Connection refused",
            error_code="ECONNREFUSED",
        )

        # Verify error properties
        assert service.status == EnumServiceHealthStatus.ERROR
        assert service.error_message == "Connection refused"
        assert service.error_code == "ECONNREFUSED"
        assert service.consecutive_failures == 1

        # Verify health checks
        assert not service.is_healthy()
        assert service.is_unhealthy()
        assert service.requires_attention()

        # Verify severity
        assert service.get_severity_level() == "critical"

        # Verify reliability score drops
        reliability = service.calculate_reliability_score()
        assert reliability == 0.0

    def test_timeout_service_creation_and_analysis(self):
        """Test creating and analyzing a timeout service."""
        # Create timeout service
        service = ModelServiceHealth.create_timeout(
            service_name="external_api",
            service_type="rest_api",
            connection_string="https://api.example.com",
            timeout_ms=5000,
        )

        # Verify timeout properties
        assert service.status == EnumServiceHealthStatus.TIMEOUT
        assert "timeout after 5000ms" in service.error_message.lower()
        assert service.response_time_ms == 5000

        # Verify health checks
        assert not service.is_healthy()
        assert service.is_unhealthy()
        assert service.requires_attention()

        # Verify performance category
        assert service.get_performance_category() == "slow"

        # Verify reliability penalty
        reliability = service.calculate_reliability_score()
        assert 0.0 <= reliability < 0.5

    def test_service_degradation_scenario(self):
        """Test service degradation with increasing failures."""
        # Start with healthy service
        services = []
        for failures in range(6):
            service = ModelServiceHealth(
                service_name="unstable_service",
                service_type=EnumServiceType.REST_API,
                status=(
                    EnumServiceHealthStatus.REACHABLE
                    if failures == 0
                    else EnumServiceHealthStatus.DEGRADED
                ),
                connection_string="https://unstable.example.com",
                consecutive_failures=failures,
                last_check_time=datetime.now(UTC).isoformat(),
                response_time_ms=100 + (failures * 500),
            )
            services.append(service)

        # Verify degradation progression
        assert services[0].is_healthy()
        assert services[0].get_availability_category() == "highly_available"

        assert services[1].is_degraded()
        assert services[1].get_availability_category() == "available"

        assert services[2].is_degraded()
        assert services[2].get_availability_category() == "unstable"

        assert services[5].is_degraded()
        assert services[5].get_availability_category() == "unavailable"

        # Verify reliability degrades
        reliabilities = [s.calculate_reliability_score() for s in services]
        for i in range(len(reliabilities) - 1):
            assert reliabilities[i] >= reliabilities[i + 1]


class TestServiceSecurityAnalysis:
    """Test service security analysis features."""

    def test_secure_connection_analysis(self):
        """Test detection of secure connections."""
        # HTTPS connection
        service_https = ModelServiceHealth(
            service_name="secure_api",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://secure.example.com",
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert service_https.get_connection_type() == "secure"
        assert service_https.is_secure_connection()

        # HTTP connection
        service_http = ModelServiceHealth(
            service_name="insecure_api",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="http://insecure.example.com",
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert service_http.get_connection_type() == "insecure"
        assert not service_http.is_secure_connection()

        # SSL flag
        service_ssl = ModelServiceHealth(
            service_name="db_with_ssl",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://localhost:5432/db",
            ssl_enabled=True,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert service_ssl.is_secure_connection()

    def test_security_recommendations(self):
        """Test security recommendation generation."""
        # Insecure service without auth
        service = ModelServiceHealth(
            service_name="insecure_service",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="http://api.example.com",
            authentication_type=None,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        recommendations = service.get_security_recommendations()

        # Should recommend SSL and authentication
        assert any("SSL/TLS" in rec for rec in recommendations)
        assert any("authentication" in rec.lower() for rec in recommendations)

    def test_credential_masking_detection(self):
        """Test detection of masked credentials."""
        service = ModelServiceHealth(
            service_name="db_service",
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="postgresql://***:***@localhost:5432/db",
            last_check_time=datetime.now(UTC).isoformat(),
        )

        recommendations = service.get_security_recommendations()

        # Should recommend using secret management
        assert any(
            "secret management" in rec.lower() or "environment variables" in rec.lower()
            for rec in recommendations
        )


class TestServicePerformanceAnalysis:
    """Test service performance analysis features."""

    def test_performance_category_classification(self):
        """Test performance categorization based on response time."""
        test_cases = [
            (50, "excellent"),
            (200, "good"),
            (800, "acceptable"),
            (5000, "slow"),
            (15000, "very_slow"),
        ]

        for response_time, expected_category in test_cases:
            service = ModelServiceHealth(
                service_name=f"service_{response_time}ms",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com",
                response_time_ms=response_time,
                last_check_time=datetime.now(UTC).isoformat(),
            )

            assert service.get_performance_category() == expected_category

    def test_performance_concerning_threshold(self):
        """Test performance concern detection."""
        # Fast service - not concerning
        fast_service = ModelServiceHealth(
            service_name="fast_service",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://fast.example.com",
            response_time_ms=500,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert not fast_service.is_performance_concerning()

        # Slow service - concerning
        slow_service = ModelServiceHealth(
            service_name="slow_service",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://slow.example.com",
            response_time_ms=8000,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert slow_service.is_performance_concerning()

    def test_human_readable_metrics(self):
        """Test human-readable metric formatting."""
        service = ModelServiceHealth(
            service_name="test_service",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://api.example.com",
            response_time_ms=1500,
            uptime_seconds=86400 * 5 + 3600 * 2,  # 5 days, 2 hours
            last_check_time=datetime.now(UTC).isoformat(),
        )

        # Test response time formatting
        assert service.get_response_time_human() == "1.50s"

        # Test uptime formatting
        assert service.get_uptime_human() == "5d"


class TestServiceBusinessImpact:
    """Test business impact assessment features."""

    def test_business_impact_critical_service(self):
        """Test business impact for critical service failure."""
        service = ModelServiceHealth.create_error(
            service_name="payment_gateway",
            service_type="custom",
            connection_string="https://payments.example.com",
            error_message="Service unavailable",
        )

        # Get business impact
        impact = service.get_business_impact()

        # Should be critical impact
        from omnibase_core.models.core.model_business_impact import EnumImpactSeverity

        assert impact.severity == EnumImpactSeverity.CRITICAL
        assert "payment_gateway" in impact.affected_services
        assert impact.sla_violated is True

    def test_business_impact_healthy_service(self):
        """Test business impact for healthy service."""
        service = ModelServiceHealth.create_healthy(
            service_name="logging_service",
            service_type="custom",
            connection_string="http://logs.example.com",
            response_time_ms=100,
        )

        impact = service.get_business_impact()

        from omnibase_core.models.core.model_business_impact import EnumImpactSeverity

        assert impact.severity == EnumImpactSeverity.MINIMAL
        assert impact.sla_violated is False
        assert impact.confidence_score == 1.0


class TestServiceModelIntegration:
    """Test integration between ModelService and ModelServiceHealth."""

    def test_service_creation_with_metadata(self):
        """Test ModelService creation with metadata."""
        service_id = uuid4()
        service = ModelService(
            service_id=service_id,
            service_name="test_service",
            service_type="rest_api",
            protocol_name="ProtocolHTTP",
            metadata={"version": "1.0.0", "region": "us-west-2"},
            health_status="healthy",
        )

        # Verify all properties
        assert isinstance(service.service_id, UUID)
        assert service.service_id == service_id
        assert service.service_name == "test_service"
        assert service.service_type == "rest_api"
        assert service.protocol_name == "ProtocolHTTP"
        assert service.metadata["version"] == "1.0.0"
        assert service.health_status == "healthy"

    def test_service_immutability(self):
        """Test that ModelService is frozen/immutable."""
        service = ModelService(
            service_id=uuid4(),
            service_name="test_service",
            service_type="rest_api",
            health_status="healthy",
        )

        # Should not be able to modify frozen model
        with pytest.raises(Exception):  # ValidationError or AttributeError
            service.health_status = "unhealthy"

    def test_service_and_health_coordination(self):
        """Test coordinated use of ModelService and ModelServiceHealth."""
        # Create service instance
        service_id = uuid4()
        service = ModelService(
            service_id=service_id,
            service_name="coordinated_service",
            service_type="postgresql",
            health_status="unknown",
        )

        # Check initial health
        health_check = ModelServiceHealth.create_healthy(
            service_name=service.service_name,
            service_type=service.service_type,
            connection_string="postgresql://localhost:5432/db",
            response_time_ms=75,
        )

        # Verify coordination
        assert service.service_name == health_check.service_name
        assert service.service_type == health_check.service_type.value
        assert health_check.is_healthy()

        # Create new service with updated health
        updated_service = ModelService(
            service_id=service.service_id,
            service_name=service.service_name,
            service_type=service.service_type,
            health_status="healthy",
        )

        assert updated_service.health_status == "healthy"


class TestServiceValidationIntegration:
    """Test service validation across models."""

    def test_service_name_validation(self):
        """Test service name validation rules."""
        # Valid names
        valid_names = [
            "postgres_db",
            "redis-cache",
            "api.gateway",
            "Service123",
        ]

        for name in valid_names:
            service = ModelServiceHealth(
                service_name=name,
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="postgresql://localhost:5432/db",
                last_check_time=datetime.now(UTC).isoformat(),
            )
            assert service.service_name == name

        # Invalid names
        invalid_names = [
            "",  # Empty
            "   ",  # Whitespace
            "123service",  # Starts with number
            "service@test",  # Invalid character
        ]

        for name in invalid_names:
            with pytest.raises(OnexError) as exc_info:
                ModelServiceHealth(
                    service_name=name,
                    service_type=EnumServiceType.POSTGRESQL,
                    status=EnumServiceHealthStatus.REACHABLE,
                    connection_string="postgresql://localhost:5432/db",
                    last_check_time=datetime.now(UTC).isoformat(),
                )
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_connection_string_validation_and_masking(self):
        """Test connection string validation and credential masking."""
        # Test various credential patterns that should be masked
        test_cases = [
            (
                "postgresql://user:password@localhost:5432/db",
                "postgresql://***:***@localhost:5432/db",
            ),
            (
                "mongodb://admin:secret123@mongo:27017/db",
                "mongodb://***:***@mongo:27017/db",
            ),
            (
                "redis://localhost:6379?password=secret",
                "redis://localhost:6379?password=***",
            ),
        ]

        for input_conn, expected_masked in test_cases:
            service = ModelServiceHealth(
                service_name="test_service",
                service_type=EnumServiceType.POSTGRESQL,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string=input_conn,
                last_check_time=datetime.now(UTC).isoformat(),
            )

            # Verify credentials are masked
            assert service.connection_string == expected_masked
            assert "***" in service.connection_string

    def test_endpoint_url_validation(self):
        """Test endpoint URL validation."""
        # Valid URLs
        valid_urls = [
            "https://api.example.com",
            "http://localhost:8080",
            "https://api.example.com:443/v1",
        ]

        for url in valid_urls:
            service = ModelServiceHealth(
                service_name="test_service",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com",
                endpoint_url=url,
                last_check_time=datetime.now(UTC).isoformat(),
            )
            assert service.endpoint_url == url

        # Invalid URLs
        invalid_urls = [
            "not-a-url",
            "missing-scheme.com",
            "//no-scheme",
        ]

        for url in invalid_urls:
            with pytest.raises(OnexError) as exc_info:
                ModelServiceHealth(
                    service_name="test_service",
                    service_type=EnumServiceType.REST_API,
                    status=EnumServiceHealthStatus.REACHABLE,
                    connection_string="https://api.example.com",
                    endpoint_url=url,
                    last_check_time=datetime.now(UTC).isoformat(),
                )
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_port_range_validation(self):
        """Test port number validation."""
        # Valid ports
        valid_ports = [80, 443, 8080, 3000, 65535]

        for port in valid_ports:
            service = ModelServiceHealth(
                service_name="test_service",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com",
                port=port,
                last_check_time=datetime.now(UTC).isoformat(),
            )
            assert service.port == port

        # Invalid ports
        invalid_ports = [0, -1, 65536, 100000]

        for port in invalid_ports:
            with pytest.raises(Exception):  # ValidationError
                ModelServiceHealth(
                    service_name="test_service",
                    service_type=EnumServiceType.REST_API,
                    status=EnumServiceHealthStatus.REACHABLE,
                    connection_string="https://api.example.com",
                    port=port,
                    last_check_time=datetime.now(UTC).isoformat(),
                )


class TestEndToEndServiceWorkflow:
    """Test complete end-to-end service monitoring workflow."""

    def test_service_monitoring_workflow(self):
        """Test complete service monitoring workflow from creation to analysis."""
        # Step 1: Initialize service
        service_id = uuid4()
        service = ModelService(
            service_id=service_id,
            service_name="production_db",
            service_type="postgresql",
            protocol_name="ProtocolPostgreSQL",
            health_status="unknown",
        )

        # Step 2: First health check - healthy
        health_check_1 = ModelServiceHealth.create_healthy(
            service_name=service.service_name,
            service_type=service.service_type,
            connection_string="postgresql://***:***@db.prod:5432/maindb",
            response_time_ms=45,
        )

        assert health_check_1.is_healthy()
        assert health_check_1.calculate_reliability_score() == 1.0

        # Step 3: Service starts degrading
        health_check_2 = ModelServiceHealth(
            service_name=service.service_name,
            service_type=EnumServiceType.POSTGRESQL,
            status=EnumServiceHealthStatus.DEGRADED,
            connection_string="postgresql://***:***@db.prod:5432/maindb",
            response_time_ms=1500,
            consecutive_failures=3,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert health_check_2.is_degraded()
        assert health_check_2.requires_attention()
        reliability_2 = health_check_2.calculate_reliability_score()
        assert reliability_2 < 1.0  # Degraded service has lower reliability

        # Step 4: Service fails
        health_check_3 = ModelServiceHealth.create_error(
            service_name=service.service_name,
            service_type=service.service_type,
            connection_string="postgresql://***:***@db.prod:5432/maindb",
            error_message="Connection pool exhausted",
            error_code="ERR_POOL_EXHAUSTED",
        )

        assert health_check_3.is_unhealthy()
        assert health_check_3.requires_attention()
        assert health_check_3.get_severity_level() == "critical"
        assert health_check_3.calculate_reliability_score() == 0.0

        # Step 5: Assess business impact
        impact = health_check_3.get_business_impact()
        from omnibase_core.models.core.model_business_impact import EnumImpactSeverity

        assert impact.severity == EnumImpactSeverity.CRITICAL
        assert impact.sla_violated is True

        # Step 6: Service recovers
        health_check_4 = ModelServiceHealth.create_healthy(
            service_name=service.service_name,
            service_type=service.service_type,
            connection_string="postgresql://***:***@db.prod:5432/maindb",
            response_time_ms=60,
        )

        assert health_check_4.is_healthy()
        assert health_check_4.calculate_reliability_score() == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
