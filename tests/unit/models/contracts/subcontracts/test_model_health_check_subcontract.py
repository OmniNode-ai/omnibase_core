"""
Unit tests for ModelHealthCheckSubcontract.

Tests health check subcontract including component health, node health,
dependency health, and health check configuration validation.
"""

from datetime import UTC, datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.models.contracts.subcontracts.model_health_check_subcontract import (
    ModelComponentHealth,
    ModelComponentHealthCollection,
    ModelDependencyHealth,
    ModelHealthCheckSubcontract,
    ModelNodeHealthStatus,
)
from omnibase_core.models.contracts.subcontracts.model_health_check_subcontract_result import (
    ModelHealthCheckSubcontractResult,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestModelComponentHealth:
    """Test suite for ModelComponentHealth."""

    def test_valid_component_health_creation(self):
        """Test creating a valid component health status."""
        now = datetime.now(UTC)
        component = ModelComponentHealth(
            component_name="database_connection",
            status=EnumNodeHealthStatus.HEALTHY,
            message="Database connection is healthy",
            last_check=now,
            check_duration_ms=150,
            details={"connection_pool": "5/10", "latency_ms": "25"},
        )

        assert component.component_name == "database_connection"
        assert component.status == EnumNodeHealthStatus.HEALTHY
        assert component.message == "Database connection is healthy"
        assert component.last_check == now
        assert component.check_duration_ms == 150
        assert component.details["connection_pool"] == "5/10"

    def test_component_health_minimal_fields(self):
        """Test component health with minimal required fields."""
        now = datetime.now(UTC)
        component = ModelComponentHealth(
            component_name="cache",
            status=EnumNodeHealthStatus.DEGRADED,
            message="Cache is degraded",
            last_check=now,
        )

        assert component.component_name == "cache"
        assert component.status == EnumNodeHealthStatus.DEGRADED
        assert component.check_duration_ms is None
        assert component.details == {}

    def test_component_health_negative_duration_validation(self):
        """Test validation of negative check duration."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError):
            ModelComponentHealth(
                component_name="test",
                status=EnumNodeHealthStatus.HEALTHY,
                message="Test",
                last_check=now,
                check_duration_ms=-1,  # Invalid negative duration
            )

    def test_component_health_enum_preservation(self):
        """Test that enum values are preserved, not converted to strings."""
        now = datetime.now(UTC)
        component = ModelComponentHealth(
            component_name="test",
            status=EnumNodeHealthStatus.CRITICAL,
            message="Critical status",
            last_check=now,
        )

        assert isinstance(component.status, EnumNodeHealthStatus)
        assert component.status == EnumNodeHealthStatus.CRITICAL


class TestModelNodeHealthStatus:
    """Test suite for ModelNodeHealthStatus."""

    def test_valid_node_health_status_creation(self):
        """Test creating a valid node health status."""
        now = datetime.now(UTC)
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        node_health = ModelNodeHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message="Node is healthy",
            timestamp=now,
            check_duration_ms=500,
            node_type="EFFECT",
            node_id=test_uuid,
        )

        assert node_health.status == EnumNodeHealthStatus.HEALTHY
        assert node_health.message == "Node is healthy"
        assert node_health.timestamp == now
        assert node_health.check_duration_ms == 500
        assert node_health.node_type == "EFFECT"
        assert node_health.node_id == test_uuid

    def test_node_health_status_without_node_id(self):
        """Test node health status without optional node_id."""
        now = datetime.now(UTC)
        node_health = ModelNodeHealthStatus(
            status=EnumNodeHealthStatus.UNHEALTHY,
            message="Node is unhealthy",
            timestamp=now,
            check_duration_ms=750,
            node_type="COMPUTE",
        )

        assert node_health.node_id is None
        assert node_health.node_type == "COMPUTE"

    def test_node_health_status_negative_duration_validation(self):
        """Test validation of negative check duration."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError):
            ModelNodeHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Test",
                timestamp=now,
                check_duration_ms=-100,  # Invalid
                node_type="REDUCER",
            )


class TestModelComponentHealthCollection:
    """Test suite for ModelComponentHealthCollection."""

    def test_valid_health_collection_creation(self):
        """Test creating a valid health collection."""
        now = datetime.now(UTC)
        components = [
            ModelComponentHealth(
                component_name="db",
                status=EnumNodeHealthStatus.HEALTHY,
                message="Healthy",
                last_check=now,
            ),
            ModelComponentHealth(
                component_name="cache",
                status=EnumNodeHealthStatus.DEGRADED,
                message="Degraded",
                last_check=now,
            ),
        ]

        collection = ModelComponentHealthCollection(
            components=components,
            healthy_count=1,
            degraded_count=1,
            unhealthy_count=0,
            total_components=2,
        )

        assert len(collection.components) == 2
        assert collection.healthy_count == 1
        assert collection.degraded_count == 1
        assert collection.unhealthy_count == 0
        assert collection.total_components == 2

    def test_health_collection_defaults(self):
        """Test health collection defaults."""
        collection = ModelComponentHealthCollection()

        assert collection.components == []
        assert collection.healthy_count == 0
        assert collection.degraded_count == 0
        assert collection.unhealthy_count == 0
        assert collection.total_components == 0

    def test_health_collection_negative_counts_validation(self):
        """Test validation of negative counts."""
        with pytest.raises(ValidationError):
            ModelComponentHealthCollection(healthy_count=-1)

        with pytest.raises(ValidationError):
            ModelComponentHealthCollection(degraded_count=-1)

        with pytest.raises(ValidationError):
            ModelComponentHealthCollection(unhealthy_count=-1)

        with pytest.raises(ValidationError):
            ModelComponentHealthCollection(total_components=-1)


class TestModelDependencyHealth:
    """Test suite for ModelDependencyHealth."""

    def test_valid_dependency_health_creation(self):
        """Test creating a valid dependency health status."""
        now = datetime.now(UTC)
        dependency = ModelDependencyHealth(
            dependency_name="postgresql",
            dependency_type="database",
            status=EnumNodeHealthStatus.HEALTHY,
            endpoint="postgresql://localhost:5432/mydb",
            last_check=now,
            response_time_ms=50,
            error_message=None,
        )

        assert dependency.dependency_name == "postgresql"
        assert dependency.dependency_type == "database"
        assert dependency.status == EnumNodeHealthStatus.HEALTHY
        assert dependency.endpoint == "postgresql://localhost:5432/mydb"
        assert dependency.response_time_ms == 50
        assert dependency.error_message is None

    def test_dependency_health_unhealthy_with_error(self):
        """Test dependency health with unhealthy status and error message."""
        now = datetime.now(UTC)
        dependency = ModelDependencyHealth(
            dependency_name="redis",
            dependency_type="cache",
            status=EnumNodeHealthStatus.UNHEALTHY,
            endpoint="redis://localhost:6379",
            last_check=now,
            response_time_ms=None,
            error_message="Connection timeout after 5000ms",
        )

        assert dependency.status == EnumNodeHealthStatus.UNHEALTHY
        assert dependency.error_message == "Connection timeout after 5000ms"
        assert dependency.response_time_ms is None

    def test_dependency_health_minimal_fields(self):
        """Test dependency health with minimal required fields."""
        now = datetime.now(UTC)
        dependency = ModelDependencyHealth(
            dependency_name="external_api",
            dependency_type="service",
            status=EnumNodeHealthStatus.DEGRADED,
            last_check=now,
        )

        assert dependency.endpoint is None
        assert dependency.response_time_ms is None
        assert dependency.error_message is None

    def test_dependency_health_negative_response_time_validation(self):
        """Test validation of negative response time."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError):
            ModelDependencyHealth(
                dependency_name="test",
                dependency_type="service",
                status=EnumNodeHealthStatus.HEALTHY,
                last_check=now,
                response_time_ms=-50,  # Invalid
            )


class TestModelHealthCheckSubcontractResult:
    """Test suite for ModelHealthCheckSubcontractResult."""

    def test_valid_health_check_result_creation(self):
        """Test creating a valid health check result."""
        now = datetime.now(UTC)

        node_health = ModelNodeHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message="All systems operational",
            timestamp=now,
            check_duration_ms=300,
            node_type="ORCHESTRATOR",
        )

        component_health = [
            ModelComponentHealth(
                component_name="worker",
                status=EnumNodeHealthStatus.HEALTHY,
                message="Worker healthy",
                last_check=now,
            )
        ]

        dependency_health = [
            ModelDependencyHealth(
                dependency_name="postgres",
                dependency_type="database",
                status=EnumNodeHealthStatus.HEALTHY,
                last_check=now,
            )
        ]

        result = ModelHealthCheckSubcontractResult(
            node_health=node_health,
            component_health=component_health,
            dependency_health=dependency_health,
            health_score=0.95,
            recommendations=["Consider scaling up workers"],
        )

        assert result.node_health.status == EnumNodeHealthStatus.HEALTHY
        assert len(result.component_health) == 1
        assert len(result.dependency_health) == 1
        assert result.health_score == 0.95
        assert len(result.recommendations) == 1

    def test_health_check_result_minimal_dependencies(self):
        """Test health check result with minimal dependencies."""
        now = datetime.now(UTC)

        node_health = ModelNodeHealthStatus(
            status=EnumNodeHealthStatus.DEGRADED,
            message="Performance degraded",
            timestamp=now,
            check_duration_ms=500,
            node_type="COMPUTE",
        )

        result = ModelHealthCheckSubcontractResult(
            node_health=node_health,
            health_score=0.75,
        )

        assert result.dependency_health == []
        assert result.recommendations == []
        assert result.health_score == 0.75

    def test_health_score_validation_range(self):
        """Test health score validation within 0.0-1.0 range."""
        now = datetime.now(UTC)

        node_health = ModelNodeHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message="Healthy",
            timestamp=now,
            check_duration_ms=100,
            node_type="EFFECT",
        )

        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            result = ModelHealthCheckSubcontractResult(
                node_health=node_health,
                health_score=score,
            )
            assert result.health_score == score

        # Invalid scores
        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontractResult(
                node_health=node_health,
                health_score=-0.1,  # Too low
            )

        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontractResult(
                node_health=node_health,
                health_score=1.1,  # Too high
            )


class TestModelHealthCheckSubcontract:
    """Test suite for ModelHealthCheckSubcontract."""

    def test_interface_version_present(self):
        """Test that INTERFACE_VERSION ClassVar is present and correct."""
        assert hasattr(ModelHealthCheckSubcontract, "INTERFACE_VERSION")
        assert isinstance(ModelHealthCheckSubcontract.INTERFACE_VERSION, ModelSemVer)
        assert (
            ModelSemVer(major=1, minor=0, patch=0)
            == ModelHealthCheckSubcontract.INTERFACE_VERSION
        )

    def test_minimal_valid_subcontract(self):
        """Test creating subcontract with defaults."""
        subcontract = ModelHealthCheckSubcontract()

        assert subcontract.subcontract_name == "health_check_subcontract"
        assert isinstance(subcontract.subcontract_version, ModelSemVer)
        assert subcontract.subcontract_version == ModelSemVer(major=1, minor=0, patch=0)
        assert subcontract.applicable_node_types == [
            "COMPUTE",
            "EFFECT",
            "REDUCER",
            "ORCHESTRATOR",
        ]
        assert subcontract.check_interval_ms == 30000
        assert subcontract.failure_threshold == 3
        assert subcontract.recovery_threshold == 2
        assert subcontract.timeout_ms == 5000
        assert subcontract.include_dependency_checks is True
        assert subcontract.include_component_checks is True
        assert subcontract.enable_health_score_calculation is True

    def test_full_subcontract_creation(self):
        """Test creating subcontract with all fields specified."""
        custom_version = ModelSemVer(major=2, minor=1, patch=0)

        subcontract = ModelHealthCheckSubcontract(
            subcontract_name="custom_health_check",
            subcontract_version=custom_version,
            applicable_node_types=["EFFECT", "REDUCER"],
            check_interval_ms=60000,
            failure_threshold=5,
            recovery_threshold=3,
            timeout_ms=10000,
            include_dependency_checks=False,
            include_component_checks=True,
            enable_health_score_calculation=False,
        )

        assert subcontract.subcontract_name == "custom_health_check"
        assert subcontract.subcontract_version == custom_version
        assert subcontract.applicable_node_types == ["EFFECT", "REDUCER"]
        assert subcontract.check_interval_ms == 60000
        assert subcontract.failure_threshold == 5
        assert subcontract.recovery_threshold == 3
        assert subcontract.timeout_ms == 10000
        assert subcontract.include_dependency_checks is False
        assert subcontract.enable_health_score_calculation is False

    def test_check_interval_validation(self):
        """Test check_interval_ms validation constraints."""
        # Valid values (5000 <= x <= 300000)
        for interval in [5000, 30000, 150000, 300000]:
            subcontract = ModelHealthCheckSubcontract(check_interval_ms=interval)
            assert subcontract.check_interval_ms == interval

        # Invalid values
        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(check_interval_ms=4999)  # Too low

        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(check_interval_ms=300001)  # Too high

    def test_failure_threshold_validation(self):
        """Test failure_threshold validation constraints."""
        # Valid values (1 <= x <= 10)
        for threshold in [1, 3, 7, 10]:
            subcontract = ModelHealthCheckSubcontract(failure_threshold=threshold)
            assert subcontract.failure_threshold == threshold

        # Invalid values
        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(failure_threshold=0)  # Too low

        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(failure_threshold=11)  # Too high

    def test_recovery_threshold_validation(self):
        """Test recovery_threshold validation constraints."""
        # Valid values (1 <= x <= 10)
        for threshold in [1, 2, 5, 10]:
            subcontract = ModelHealthCheckSubcontract(recovery_threshold=threshold)
            assert subcontract.recovery_threshold == threshold

        # Invalid values
        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(recovery_threshold=0)  # Too low

        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(recovery_threshold=11)  # Too high

    def test_timeout_validation(self):
        """Test timeout_ms validation constraints."""
        # Valid values (1000 <= x <= 30000)
        for timeout in [1000, 5000, 15000, 30000]:
            subcontract = ModelHealthCheckSubcontract(timeout_ms=timeout)
            assert subcontract.timeout_ms == timeout

        # Invalid values
        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(timeout_ms=999)  # Too low

        with pytest.raises(ValidationError):
            ModelHealthCheckSubcontract(timeout_ms=30001)  # Too high

    def test_subcontract_version_is_modelsemver(self):
        """Test that subcontract_version is ModelSemVer, not string."""
        subcontract = ModelHealthCheckSubcontract()

        assert isinstance(subcontract.subcontract_version, ModelSemVer)
        assert not isinstance(subcontract.subcontract_version, str)

        # Test version string representation
        assert str(subcontract.subcontract_version) == "1.0.0"

    def test_model_config_settings(self):
        """Test that model_config is properly configured."""
        subcontract = ModelHealthCheckSubcontract()

        # Model should ignore extra fields
        assert subcontract.model_config.get("extra") == "ignore"

        # Model should preserve enum values
        assert subcontract.model_config.get("use_enum_values") is False

        # Model should validate on assignment
        assert subcontract.model_config.get("validate_assignment") is True

    def test_applicable_node_types_can_be_customized(self):
        """Test that applicable_node_types can be customized."""
        subcontract = ModelHealthCheckSubcontract(
            applicable_node_types=["COMPUTE", "EFFECT"]
        )

        assert len(subcontract.applicable_node_types) == 2
        assert "COMPUTE" in subcontract.applicable_node_types
        assert "EFFECT" in subcontract.applicable_node_types
        assert "REDUCER" not in subcontract.applicable_node_types

    def test_serialization_deserialization(self):
        """Test that subcontract can be serialized and deserialized."""
        original = ModelHealthCheckSubcontract(
            check_interval_ms=45000,
            failure_threshold=4,
            recovery_threshold=3,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = ModelHealthCheckSubcontract(**data)

        assert restored.check_interval_ms == original.check_interval_ms
        assert restored.failure_threshold == original.failure_threshold
        assert restored.recovery_threshold == original.recovery_threshold
        assert restored.subcontract_version == original.subcontract_version

    def test_version_comparison(self):
        """Test ModelSemVer version comparison in subcontract."""
        v1 = ModelHealthCheckSubcontract(
            subcontract_version=ModelSemVer(major=1, minor=0, patch=0)
        )
        v2 = ModelHealthCheckSubcontract(
            subcontract_version=ModelSemVer(major=2, minor=0, patch=0)
        )

        assert v1.subcontract_version < v2.subcontract_version
        assert v2.subcontract_version > v1.subcontract_version

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored due to model_config."""
        # Should not raise validation error with extra fields
        subcontract = ModelHealthCheckSubcontract(
            extra_field="should be ignored",
            another_field=123,
        )

        # Extra fields should not be accessible
        assert not hasattr(subcontract, "extra_field")
        assert not hasattr(subcontract, "another_field")
