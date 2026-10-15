# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelServiceRegistryStatus."""

from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.enums import (
    EnumHealthStatus,
    EnumInjectionScope,
    EnumServiceLifecycle,
)
from omnibase_core.models.container.model_registry_status import (
    ModelServiceRegistryStatus,
)


@pytest.fixture
def sample_status():
    """Create sample registry status."""
    return ModelServiceRegistryStatus(
        registry_id=uuid4(),
        status="success",
        message="Registry operational",
    )


@pytest.mark.unit
@pytest.mark.filterwarnings("error::UserWarning")
class TestModelServiceRegistryStatus:
    """Tests for ModelServiceRegistryStatus model."""

    def test_initialization_with_defaults(self):
        """Test status initialization with default values."""
        reg_id = uuid4()
        status = ModelServiceRegistryStatus(
            registry_id=reg_id,
            status="success",
            message="Test registry",
        )

        assert status.registry_id == reg_id
        assert status.status == "success"
        assert status.message == "Test registry"
        assert status.total_registrations == 0
        assert status.active_instances == 0
        assert status.failed_registrations == 0
        assert status.circular_dependencies == 0
        assert status.lifecycle_distribution == {}
        assert status.scope_distribution == {}
        assert status.health_summary == {}
        assert status.memory_usage_bytes is None
        assert status.average_resolution_time_ms is None
        assert isinstance(status.last_updated, datetime)

    def test_initialization_with_all_fields(self):
        """Test status initialization with all fields."""
        reg_id = uuid4()
        last_updated = datetime.now()

        status = ModelServiceRegistryStatus(
            registry_id=reg_id,
            status="success",
            message="Fully configured registry",
            total_registrations=10,
            active_instances=5,
            failed_registrations=1,
            circular_dependencies=0,
            lifecycle_distribution={
                EnumServiceLifecycle.SINGLETON: 5,
                EnumServiceLifecycle.TRANSIENT: 5,
            },
            scope_distribution={
                EnumInjectionScope.GLOBAL: 7,
                EnumInjectionScope.REQUEST: 3,
            },
            health_summary={EnumHealthStatus.HEALTHY: 9, EnumHealthStatus.DEGRADED: 1},
            memory_usage_bytes=1024000,
            average_resolution_time_ms=2.5,
            last_updated=last_updated,
        )

        assert status.total_registrations == 10
        assert status.active_instances == 5
        assert status.failed_registrations == 1
        assert status.lifecycle_distribution == {
            EnumServiceLifecycle.SINGLETON: 5,
            EnumServiceLifecycle.TRANSIENT: 5,
        }
        assert status.scope_distribution == {
            EnumInjectionScope.GLOBAL: 7,
            EnumInjectionScope.REQUEST: 3,
        }
        assert status.health_summary == {
            EnumHealthStatus.HEALTHY: 9,
            EnumHealthStatus.DEGRADED: 1,
        }
        assert status.memory_usage_bytes == 1024000
        assert status.average_resolution_time_ms == 2.5
        assert status.last_updated == last_updated

    def test_is_healthy_when_all_good(self, sample_status):
        """Test is_healthy returns True when all conditions met."""
        sample_status.status = "success"
        sample_status.circular_dependencies = 0
        sample_status.failed_registrations = 0

        assert sample_status.is_healthy() is True

    def test_is_healthy_when_status_not_success(self, sample_status):
        """Test is_healthy returns False when status is not success."""
        sample_status.status = "error"
        assert sample_status.is_healthy() is False

        sample_status.status = "pending"
        assert sample_status.is_healthy() is False

    def test_is_healthy_with_circular_dependencies(self, sample_status):
        """Test is_healthy returns False with circular dependencies."""
        sample_status.circular_dependencies = 2
        assert sample_status.is_healthy() is False

    def test_is_healthy_with_failed_registrations(self, sample_status):
        """Test is_healthy returns False with failed registrations."""
        sample_status.failed_registrations = 3
        assert sample_status.is_healthy() is False

    def test_is_healthy_combined_issues(self, sample_status):
        """Test is_healthy with multiple issues."""
        sample_status.status = "error"
        sample_status.circular_dependencies = 1
        sample_status.failed_registrations = 2
        assert sample_status.is_healthy() is False

    def test_get_health_percentage_empty_registry(self, sample_status):
        """Test health percentage for empty registry."""
        sample_status.total_registrations = 0
        sample_status.health_summary = {}

        assert sample_status.get_health_percentage() == 100.0

    def test_get_health_percentage_all_healthy(self, sample_status):
        """Test health percentage when all services healthy."""
        sample_status.total_registrations = 10
        sample_status.health_summary = {EnumHealthStatus.HEALTHY: 10}

        assert sample_status.get_health_percentage() == 100.0

    def test_get_health_percentage_partial_healthy(self, sample_status):
        """Test health percentage with partial health."""
        sample_status.total_registrations = 10
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 7,
            EnumHealthStatus.DEGRADED: 2,
            EnumHealthStatus.UNHEALTHY: 1,
        }

        assert sample_status.get_health_percentage() == 70.0

    def test_get_health_percentage_no_healthy(self, sample_status):
        """Test health percentage with no healthy services."""
        sample_status.total_registrations = 5
        sample_status.health_summary = {
            EnumHealthStatus.UNHEALTHY: 3,
            EnumHealthStatus.DEGRADED: 2,
        }

        assert sample_status.get_health_percentage() == 0.0

    def test_get_health_percentage_half_healthy(self, sample_status):
        """Test health percentage at 50%."""
        sample_status.total_registrations = 20
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 10,
            EnumHealthStatus.UNHEALTHY: 10,
        }

        assert sample_status.get_health_percentage() == 50.0

    def test_lifecycle_distribution_tracking(self, sample_status):
        """Test lifecycle distribution tracking."""
        sample_status.lifecycle_distribution = {
            EnumServiceLifecycle.SINGLETON: 15,
            EnumServiceLifecycle.TRANSIENT: 10,
            EnumServiceLifecycle.SCOPED: 5,
            EnumServiceLifecycle.POOLED: 2,
        }

        assert (
            sample_status.lifecycle_distribution[EnumServiceLifecycle.SINGLETON] == 15
        )
        assert (
            sample_status.lifecycle_distribution[EnumServiceLifecycle.TRANSIENT] == 10
        )
        assert sample_status.lifecycle_distribution[EnumServiceLifecycle.SCOPED] == 5
        assert sample_status.lifecycle_distribution[EnumServiceLifecycle.POOLED] == 2

    def test_scope_distribution_tracking(self, sample_status):
        """Test scope distribution tracking."""
        sample_status.scope_distribution = {
            EnumInjectionScope.GLOBAL: 20,
            EnumInjectionScope.REQUEST: 8,
            EnumInjectionScope.SESSION: 4,
        }

        assert sample_status.scope_distribution[EnumInjectionScope.GLOBAL] == 20
        assert sample_status.scope_distribution[EnumInjectionScope.REQUEST] == 8
        assert sample_status.scope_distribution[EnumInjectionScope.SESSION] == 4

    def test_health_summary_tracking(self, sample_status):
        """Test health summary tracking."""
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 25,
            EnumHealthStatus.DEGRADED: 3,
            EnumHealthStatus.UNHEALTHY: 2,
            EnumHealthStatus.UNKNOWN: 1,
        }

        assert sample_status.health_summary[EnumHealthStatus.HEALTHY] == 25
        assert sample_status.health_summary[EnumHealthStatus.DEGRADED] == 3
        assert sample_status.health_summary[EnumHealthStatus.UNHEALTHY] == 2
        assert sample_status.health_summary[EnumHealthStatus.UNKNOWN] == 1

    def test_performance_metrics(self, sample_status):
        """Test performance metrics tracking."""
        sample_status.average_resolution_time_ms = 1.5
        sample_status.memory_usage_bytes = 2048000

        assert sample_status.average_resolution_time_ms == 1.5
        assert sample_status.memory_usage_bytes == 2048000

    def test_status_types(self):
        """Test different status types."""
        reg_id = uuid4()
        for status_type in ["success", "failed", "in_progress", "cancelled", "pending"]:
            status = ModelServiceRegistryStatus(
                registry_id=reg_id,
                status=status_type,  # type: ignore[arg-type]
                message=f"Status: {status_type}",
            )
            assert status.status == status_type

    def test_serialization_deserialization(self, sample_status):
        """Test model can be serialized and deserialized."""
        sample_status.total_registrations = 15
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 10,
            EnumHealthStatus.DEGRADED: 5,
        }

        # Serialize to dict
        data = sample_status.model_dump()

        # Deserialize from dict
        restored = ModelServiceRegistryStatus(**data)

        assert restored.registry_id == sample_status.registry_id
        assert restored.status == sample_status.status
        assert restored.total_registrations == sample_status.total_registrations
        assert restored.health_summary == sample_status.health_summary

    def test_registry_growth_scenario(self, sample_status):
        """Test registry status during growth."""
        # Empty registry
        assert sample_status.total_registrations == 0
        assert sample_status.is_healthy()

        # Services registered
        sample_status.total_registrations = 10
        sample_status.active_instances = 10
        sample_status.health_summary = {EnumHealthStatus.HEALTHY: 10}
        assert sample_status.is_healthy()
        assert sample_status.get_health_percentage() == 100.0

        # Growth continues
        sample_status.total_registrations = 25
        sample_status.active_instances = 30
        sample_status.health_summary = {EnumHealthStatus.HEALTHY: 25}
        assert sample_status.is_healthy()
        assert sample_status.get_health_percentage() == 100.0

    def test_registry_degradation_scenario(self, sample_status):
        """Test registry status during degradation."""
        # Healthy initial state
        sample_status.total_registrations = 20
        sample_status.health_summary = {EnumHealthStatus.HEALTHY: 20}
        assert sample_status.is_healthy()
        assert sample_status.get_health_percentage() == 100.0

        # Some services degrade
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 15,
            EnumHealthStatus.DEGRADED: 5,
        }
        assert sample_status.is_healthy()
        assert sample_status.get_health_percentage() == 75.0

        # Registration fails
        sample_status.failed_registrations = 2
        assert not sample_status.is_healthy()

        # Circular dependency detected
        sample_status.circular_dependencies = 1
        assert not sample_status.is_healthy()

    def test_registry_recovery_scenario(self, sample_status):
        """Test registry status during recovery."""
        # Degraded state
        sample_status.status = "error"
        sample_status.total_registrations = 10
        sample_status.failed_registrations = 3
        sample_status.circular_dependencies = 1
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 5,
            EnumHealthStatus.UNHEALTHY: 5,
        }
        assert not sample_status.is_healthy()
        assert sample_status.get_health_percentage() == 50.0

        # Issues resolved
        sample_status.failed_registrations = 0
        sample_status.circular_dependencies = 0
        assert not sample_status.is_healthy()  # Still error status

        # Status recovered
        sample_status.status = "success"
        assert sample_status.is_healthy()

        # Health improved
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 9,
            EnumHealthStatus.DEGRADED: 1,
        }
        assert sample_status.is_healthy()
        assert sample_status.get_health_percentage() == 90.0

    def test_comprehensive_status_report(self, sample_status):
        """Test comprehensive status with all fields populated."""
        sample_status.total_registrations = 50
        sample_status.active_instances = 75
        sample_status.failed_registrations = 0
        sample_status.circular_dependencies = 0
        sample_status.lifecycle_distribution = {
            EnumServiceLifecycle.SINGLETON: 20,
            EnumServiceLifecycle.TRANSIENT: 15,
            EnumServiceLifecycle.SCOPED: 10,
            EnumServiceLifecycle.POOLED: 5,
        }
        sample_status.scope_distribution = {
            EnumInjectionScope.GLOBAL: 30,
            EnumInjectionScope.REQUEST: 15,
            EnumInjectionScope.SESSION: 5,
        }
        sample_status.health_summary = {
            EnumHealthStatus.HEALTHY: 45,
            EnumHealthStatus.DEGRADED: 3,
            EnumHealthStatus.UNHEALTHY: 2,
        }
        sample_status.memory_usage_bytes = 5242880  # 5MB
        sample_status.average_resolution_time_ms = 3.2

        # Validate comprehensive status
        assert sample_status.is_healthy()
        assert sample_status.get_health_percentage() == 90.0
        assert sum(sample_status.lifecycle_distribution.values()) == 50
        assert sum(sample_status.scope_distribution.values()) == 50
        assert sum(sample_status.health_summary.values()) == 50
