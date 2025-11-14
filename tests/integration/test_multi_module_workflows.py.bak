#!/usr/bin/env python3
"""
Integration tests for multi-module workflows.

Tests cross-layer integration, model-enum coordination, error handling,
and real-world usage patterns without mocking.
"""

from datetime import UTC, datetime, timezone
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_action_category import EnumActionCategory
from omnibase_core.enums.enum_artifact_type import EnumArtifactType
from omnibase_core.enums.enum_auth_type import EnumAuthType
from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.enums.enum_debug_level import EnumDebugLevel
from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_filter_type import EnumFilterType
from omnibase_core.enums.enum_parameter_type import EnumParameterType
from omnibase_core.enums.enum_service_health_status import EnumServiceHealthStatus
from omnibase_core.enums.enum_service_type import EnumServiceType
from omnibase_core.errors import EnumCoreErrorCode, OnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.service.model_service_health import ModelServiceHealth


class TestEnumModelIntegration:
    """Test integration between enums and models."""

    def test_service_health_with_enum_types(self):
        """Test ModelServiceHealth using enum types."""
        # Create service with all enum fields
        service = ModelServiceHealth(
            service_name="integrated_service",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://api.example.com",
            last_check_time=datetime.now(UTC).isoformat(),
            response_time_ms=100,
        )

        # Verify enum values
        assert isinstance(service.service_type, EnumServiceType)
        assert isinstance(service.status, EnumServiceHealthStatus)
        assert service.service_type == EnumServiceType.REST_API
        assert service.status == EnumServiceHealthStatus.REACHABLE

    def test_enum_value_conversion_in_models(self):
        """Test enum value conversion when creating models."""
        # Create service using string value (should convert to enum)
        service = ModelServiceHealth(
            service_name="test_service",
            service_type="postgresql",  # String value
            status="reachable",  # String value
            connection_string="postgresql://localhost:5432/db",
            last_check_time=datetime.now(UTC).isoformat(),
        )

        # Should convert to enum types
        assert service.service_type == EnumServiceType.POSTGRESQL
        assert service.status == EnumServiceHealthStatus.REACHABLE

    def test_enum_validation_in_models(self):
        """Test enum validation when creating models."""
        # Invalid enum value should raise error
        with pytest.raises(Exception):  # ValidationError
            ModelServiceHealth(
                service_name="test_service",
                service_type="invalid_type",
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com",
                last_check_time=datetime.now(UTC).isoformat(),
            )

    def test_multiple_enum_types_coordination(self):
        """Test coordination of multiple enum types in workflows."""
        # Simulate a workflow with multiple enum types
        workflow_data = {
            "environment": EnumEnvironment.PRODUCTION,
            "execution_status": EnumExecutionStatus.RUNNING,
            "data_classification": EnumDataClassification.CONFIDENTIAL,
            "action_category": EnumActionCategory.EXECUTION,
            "auth_type": EnumAuthType.OAUTH2,
        }

        # Verify all enums are usable together
        assert workflow_data["environment"] == EnumEnvironment.PRODUCTION
        assert workflow_data["execution_status"] == EnumExecutionStatus.RUNNING
        assert (
            workflow_data["data_classification"] == EnumDataClassification.CONFIDENTIAL
        )

        # Test enum comparisons
        assert workflow_data["environment"] != EnumEnvironment.DEVELOPMENT
        assert workflow_data["execution_status"] != EnumExecutionStatus.COMPLETED


class TestErrorHandlingIntegration:
    """Test error handling across multiple modules."""

    def test_onex_error_with_service_failure(self):
        """Test OnexError integration with service failures."""
        # Create error service
        service = ModelServiceHealth.create_error(
            service_name="failing_service",
            service_type="rest_api",
            connection_string="https://api.example.com",
            error_message="Connection timeout",
            error_code="TIMEOUT_ERROR",
        )

        # Verify error properties are captured
        assert service.status == EnumServiceHealthStatus.ERROR
        assert service.error_message == "Connection timeout"
        assert service.error_code == "TIMEOUT_ERROR"

    def test_validation_error_propagation(self):
        """Test validation error propagation across models."""
        # Test invalid service name
        with pytest.raises(OnexError) as exc_info:
            ModelServiceHealth(
                service_name="",  # Invalid empty name
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com",
                last_check_time=datetime.now(UTC).isoformat(),
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "service_name" in str(exc_info.value)

    def test_chained_error_handling(self):
        """Test error handling chain across multiple operations."""
        errors_encountered = []

        # Simulate multiple operations with error handling
        try:
            # Operation 1: Invalid service creation
            ModelServiceHealth(
                service_name="123invalid",  # Starts with number
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com",
                last_check_time=datetime.now(UTC).isoformat(),
            )
        except OnexError as e:
            errors_encountered.append(("service_creation", e.error_code))

        try:
            # Operation 2: Invalid connection string
            ModelServiceHealth(
                service_name="test_service",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="",  # Empty connection string
                last_check_time=datetime.now(UTC).isoformat(),
            )
        except OnexError as e:
            errors_encountered.append(("connection_string", e.error_code))

        # Verify both errors were caught
        assert len(errors_encountered) == 2
        assert all(
            code == EnumCoreErrorCode.VALIDATION_ERROR for _, code in errors_encountered
        )


class TestSemVerIntegration:
    """Test SemVer integration with service models."""

    def test_service_with_version_tracking(self):
        """Test service health tracking with semantic versioning."""
        # Create service with version
        version = ModelSemVer(major=1, minor=2, patch=3)
        service = ModelServiceHealth(
            service_name="versioned_service",
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://api.example.com",
            version=version,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        # Verify version is tracked
        assert service.version is not None
        assert service.version.major == 1
        assert service.version.minor == 2
        assert service.version.patch == 3

    def test_version_comparison_in_service_management(self):
        """Test version comparisons in service management scenarios."""
        # Create services with different versions
        v1_0_0 = ModelSemVer(major=1, minor=0, patch=0)
        v1_2_3 = ModelSemVer(major=1, minor=2, patch=3)
        v2_0_0 = ModelSemVer(major=2, minor=0, patch=0)

        services = [
            ModelServiceHealth(
                service_name="api_v1",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com/v1",
                version=v1_0_0,
                last_check_time=datetime.now(UTC).isoformat(),
            ),
            ModelServiceHealth(
                service_name="api_v1_2_3",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com/v1.2.3",
                version=v1_2_3,
                last_check_time=datetime.now(UTC).isoformat(),
            ),
            ModelServiceHealth(
                service_name="api_v2",
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com/v2",
                version=v2_0_0,
                last_check_time=datetime.now(UTC).isoformat(),
            ),
        ]

        # Verify versions
        assert services[0].version < services[1].version
        assert services[1].version < services[2].version
        assert services[0].version < services[2].version


class TestDataFlowIntegration:
    """Test data flow across multiple modules."""

    def test_service_health_data_flow(self):
        """Test data flow through service health monitoring."""
        # Step 1: Service registration
        service_name = "data_flow_service"
        service_type = EnumServiceType.REST_API

        # Step 2: Initial health check
        health_1 = ModelServiceHealth.create_healthy(
            service_name=service_name,
            service_type=service_type.value,
            connection_string="https://api.example.com",
            response_time_ms=50,
        )

        # Step 3: Analyze health
        reliability_1 = health_1.calculate_reliability_score()
        performance_1 = health_1.get_performance_category()

        # Step 4: Service degrades
        health_2 = ModelServiceHealth(
            service_name=service_name,
            service_type=service_type,
            status=EnumServiceHealthStatus.DEGRADED,
            connection_string="https://api.example.com",
            response_time_ms=5000,
            consecutive_failures=3,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        # Step 5: Compare metrics
        reliability_2 = health_2.calculate_reliability_score()
        performance_2 = health_2.get_performance_category()

        # Verify data flow shows degradation
        assert reliability_1 > reliability_2
        assert performance_1 in ["excellent", "good"]
        assert performance_2 in ["slow", "very_slow"]

    def test_enum_based_workflow_routing(self):
        """Test workflow routing based on enum values."""
        # Define workflow steps based on enums
        workflow_steps = []

        # Step 1: Environment setup
        environment = EnumEnvironment.PRODUCTION
        workflow_steps.append(("environment", environment))

        # Step 2: Authentication
        auth_type = EnumAuthType.OAUTH2
        workflow_steps.append(("auth", auth_type))

        # Step 3: Data classification
        classification = EnumDataClassification.CONFIDENTIAL
        workflow_steps.append(("classification", classification))

        # Step 4: Action determination
        action = EnumActionCategory.EXECUTION
        workflow_steps.append(("action", action))

        # Verify workflow progression
        assert len(workflow_steps) == 4
        assert workflow_steps[0][1] == EnumEnvironment.PRODUCTION
        assert workflow_steps[1][1] == EnumAuthType.OAUTH2
        assert workflow_steps[2][1] == EnumDataClassification.CONFIDENTIAL
        assert workflow_steps[3][1] == EnumActionCategory.EXECUTION


class TestConcurrentOperations:
    """Test concurrent operations across modules."""

    def test_multiple_service_health_checks(self):
        """Test concurrent health checks for multiple services."""
        services = []

        # Create multiple services
        service_configs = [
            ("postgres", "postgresql", 50, EnumServiceHealthStatus.REACHABLE),
            ("redis", "redis", 20, EnumServiceHealthStatus.REACHABLE),
            ("api_gateway", "rest_api", 100, EnumServiceHealthStatus.REACHABLE),
            ("message_queue", "rabbitmq", 1500, EnumServiceHealthStatus.DEGRADED),
            ("backup_db", "postgresql", 30000, EnumServiceHealthStatus.TIMEOUT),
        ]

        for name, svc_type, response_time, status in service_configs:
            service = ModelServiceHealth(
                service_name=name,
                service_type=EnumServiceType(svc_type),
                status=status,
                connection_string=f"https://{name}.example.com",
                response_time_ms=response_time,
                last_check_time=datetime.now(UTC).isoformat(),
            )
            services.append(service)

        # Analyze all services
        healthy_count = sum(1 for s in services if s.is_healthy())
        unhealthy_count = sum(1 for s in services if s.is_unhealthy())
        degraded_count = sum(1 for s in services if s.is_degraded())

        # Verify counts
        assert healthy_count == 3  # postgres, redis, api_gateway
        assert unhealthy_count == 1  # backup_db
        assert degraded_count == 1  # message_queue

        # Calculate aggregate reliability
        total_reliability = sum(s.calculate_reliability_score() for s in services)
        avg_reliability = total_reliability / len(services)

        assert 0.0 <= avg_reliability <= 1.0

    def test_batch_service_operations(self):
        """Test batch operations on multiple services."""
        # Batch create services
        service_names = [f"service_{i}" for i in range(10)]
        services = []

        for name in service_names:
            service = ModelServiceHealth.create_healthy(
                service_name=name,
                service_type="rest_api",
                connection_string=f"https://{name}.example.com",
                response_time_ms=50 + (hash(name) % 200),
            )
            services.append(service)

        # Batch analyze performance
        performance_categories = [s.get_performance_category() for s in services]
        excellent_count = sum(1 for cat in performance_categories if cat == "excellent")
        good_count = sum(1 for cat in performance_categories if cat == "good")

        # Most should be excellent or good
        assert excellent_count + good_count >= 8


class TestComplexWorkflows:
    """Test complex multi-step workflows."""

    def test_service_deployment_workflow(self):
        """Test complete service deployment workflow."""
        # Step 1: Pre-deployment validation
        environment = EnumEnvironment.STAGING
        assert environment == EnumEnvironment.STAGING

        # Step 2: Service initialization
        service_name = "new_deployment"
        version = ModelSemVer(major=1, minor=0, patch=0)

        # Step 3: Initial health check (service starting)
        health_check = ModelServiceHealth(
            service_name=service_name,
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.DEGRADED,
            connection_string="https://api.staging.example.com",
            response_time_ms=3000,
            version=version,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert health_check.is_degraded()

        # Step 4: Service stabilizes
        stable_check = ModelServiceHealth(
            service_name=service_name,
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://api.staging.example.com",
            response_time_ms=100,
            version=version,
            consecutive_failures=0,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert stable_check.is_healthy()
        assert stable_check.calculate_reliability_score() == 1.0

        # Step 5: Promote to production
        environment = EnumEnvironment.PRODUCTION
        production_check = ModelServiceHealth(
            service_name=service_name,
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string="https://api.prod.example.com",
            response_time_ms=80,
            version=version,
            last_check_time=datetime.now(UTC).isoformat(),
        )

        assert environment == EnumEnvironment.PRODUCTION
        assert production_check.is_healthy()

    def test_disaster_recovery_workflow(self):
        """Test disaster recovery workflow."""
        # Step 1: Primary service fails
        primary = ModelServiceHealth.create_error(
            service_name="primary_db",
            service_type="postgresql",
            connection_string="postgresql://primary.db:5432/main",
            error_message="Database connection lost",
            error_code="CONNECTION_LOST",
        )

        assert primary.is_unhealthy()
        assert primary.requires_attention()

        # Step 2: Assess business impact
        impact = primary.get_business_impact()
        from omnibase_core.models.core.model_business_impact import EnumImpactSeverity

        assert impact.severity == EnumImpactSeverity.CRITICAL

        # Step 3: Failover to secondary
        secondary = ModelServiceHealth.create_healthy(
            service_name="secondary_db",
            service_type="postgresql",
            connection_string="postgresql://secondary.db:5432/main",
            response_time_ms=100,
        )

        assert secondary.is_healthy()

        # Step 4: Verify recovery
        assert not secondary.requires_attention()
        assert secondary.calculate_reliability_score() == 1.0

    def test_load_balancing_workflow(self):
        """Test load balancing across multiple services."""
        # Create pool of services
        service_pool = []

        for i in range(5):
            # Vary response times
            response_time = 50 + (i * 200)
            status = (
                EnumServiceHealthStatus.REACHABLE
                if response_time < 500
                else EnumServiceHealthStatus.DEGRADED
            )

            service = ModelServiceHealth(
                service_name=f"server_{i}",
                service_type=EnumServiceType.REST_API,
                status=status,
                connection_string=f"https://server{i}.example.com",
                response_time_ms=response_time,
                last_check_time=datetime.now(UTC).isoformat(),
            )
            service_pool.append(service)

        # Select fastest healthy services
        healthy_services = [s for s in service_pool if s.is_healthy()]
        sorted_by_performance = sorted(
            healthy_services, key=lambda s: s.response_time_ms or 9999
        )

        # Verify selection
        assert len(sorted_by_performance) >= 2
        assert all(s.is_healthy() for s in sorted_by_performance)

        # Verify ordering (fastest first)
        for i in range(len(sorted_by_performance) - 1):
            assert (
                sorted_by_performance[i].response_time_ms
                <= sorted_by_performance[i + 1].response_time_ms
            )


class TestStateTransitions:
    """Test state transitions across modules."""

    def test_service_state_lifecycle(self):
        """Test complete service state lifecycle."""
        service_name = "lifecycle_service"

        # State 1: Unknown (initial)
        states = []
        states.append(("unknown", EnumServiceHealthStatus.UNREACHABLE))

        # State 2: Healthy
        healthy = ModelServiceHealth.create_healthy(
            service_name=service_name,
            service_type="rest_api",
            connection_string="https://api.example.com",
            response_time_ms=100,
        )
        states.append(("healthy", healthy.status))

        # State 3: Degraded
        degraded = ModelServiceHealth(
            service_name=service_name,
            service_type=EnumServiceType.REST_API,
            status=EnumServiceHealthStatus.DEGRADED,
            connection_string="https://api.example.com",
            response_time_ms=2000,
            consecutive_failures=2,
            last_check_time=datetime.now(UTC).isoformat(),
        )
        states.append(("degraded", degraded.status))

        # State 4: Error
        error = ModelServiceHealth.create_error(
            service_name=service_name,
            service_type="rest_api",
            connection_string="https://api.example.com",
            error_message="Service unavailable",
        )
        states.append(("error", error.status))

        # State 5: Recovered
        recovered = ModelServiceHealth.create_healthy(
            service_name=service_name,
            service_type="rest_api",
            connection_string="https://api.example.com",
            response_time_ms=80,
        )
        states.append(("recovered", recovered.status))

        # Verify state progression
        assert len(states) == 5
        assert states[0][1] == EnumServiceHealthStatus.UNREACHABLE
        assert states[1][1] == EnumServiceHealthStatus.REACHABLE
        assert states[2][1] == EnumServiceHealthStatus.DEGRADED
        assert states[3][1] == EnumServiceHealthStatus.ERROR
        assert states[4][1] == EnumServiceHealthStatus.REACHABLE

    def test_execution_status_workflow(self):
        """Test execution status transitions."""
        # Simulate workflow execution states
        execution_states = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.COMPLETED,
        ]

        # Verify state progression
        assert execution_states[0] == EnumExecutionStatus.PENDING
        assert execution_states[1] == EnumExecutionStatus.RUNNING
        assert execution_states[2] == EnumExecutionStatus.COMPLETED

        # Test failed workflow
        failed_states = [
            EnumExecutionStatus.PENDING,
            EnumExecutionStatus.RUNNING,
            EnumExecutionStatus.FAILED,
        ]

        assert failed_states[2] == EnumExecutionStatus.FAILED
        assert failed_states[2] != EnumExecutionStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
