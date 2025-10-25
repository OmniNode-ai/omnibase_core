"""Tests for ModelServiceRegistration."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.container.model_service_metadata import ModelServiceMetadata
from omnibase_core.models.container.model_service_registration import (
    ModelServiceRegistration,
)


@pytest.fixture
def sample_metadata():
    """Create sample service metadata."""
    return ModelServiceMetadata(
        service_id=uuid4(),
        service_name="test_service",
        service_interface="TestProtocol",
        service_implementation="TestImpl",
        description="Test service",
        tags=["test"],
    )


@pytest.fixture
def sample_registration(sample_metadata):
    """Create sample service registration."""
    return ModelServiceRegistration(
        registration_id=uuid4(),
        service_metadata=sample_metadata,
        lifecycle="singleton",
        scope="global",
    )


class TestModelServiceRegistration:
    """Tests for ModelServiceRegistration model."""

    def test_initialization_with_defaults(self, sample_metadata):
        """Test registration initialization with default values."""
        reg_id = uuid4()
        registration = ModelServiceRegistration(
            registration_id=reg_id,
            service_metadata=sample_metadata,
            lifecycle="singleton",
            scope="global",
        )

        assert registration.registration_id == reg_id
        assert registration.service_metadata == sample_metadata
        assert registration.lifecycle == "singleton"
        assert registration.scope == "global"
        assert registration.dependencies == []
        assert registration.registration_status == "registered"
        assert registration.health_status == "healthy"
        assert isinstance(registration.registration_time, datetime)
        assert registration.last_access_time is None
        assert registration.access_count == 0
        assert registration.instance_count == 0
        assert registration.max_instances is None

    def test_initialization_with_all_fields(self, sample_metadata):
        """Test registration initialization with all fields."""
        reg_id = uuid4()
        reg_time = datetime.now()
        last_access = datetime.now()

        registration = ModelServiceRegistration(
            registration_id=reg_id,
            service_metadata=sample_metadata,
            lifecycle="transient",
            scope="request",
            dependencies=["dep1", "dep2"],
            registration_status="pending",
            health_status="degraded",
            registration_time=reg_time,
            last_access_time=last_access,
            access_count=5,
            instance_count=2,
            max_instances=10,
        )

        assert registration.registration_id == reg_id
        assert registration.lifecycle == "transient"
        assert registration.scope == "request"
        assert registration.dependencies == ["dep1", "dep2"]
        assert registration.registration_status == "pending"
        assert registration.health_status == "degraded"
        assert registration.registration_time == reg_time
        assert registration.last_access_time == last_access
        assert registration.access_count == 5
        assert registration.instance_count == 2
        assert registration.max_instances == 10

    @pytest.mark.asyncio
    async def test_validate_registration_valid(self, sample_registration):
        """Test validation of a valid registration."""
        assert await sample_registration.validate_registration() is True

    @pytest.mark.asyncio
    async def test_validate_registration_unregistered(self, sample_registration):
        """Test validation fails for unregistered status."""
        sample_registration.registration_status = "unregistered"
        assert await sample_registration.validate_registration() is False

    @pytest.mark.asyncio
    async def test_validate_registration_unhealthy(self, sample_registration):
        """Test validation fails for unhealthy status."""
        sample_registration.health_status = "unhealthy"
        assert await sample_registration.validate_registration() is False

    @pytest.mark.asyncio
    async def test_validate_registration_failed(self, sample_registration):
        """Test validation fails for failed status."""
        sample_registration.registration_status = "failed"
        assert await sample_registration.validate_registration() is False

    def test_is_active_when_healthy(self, sample_registration):
        """Test is_active returns True for healthy registered service."""
        assert sample_registration.is_active() is True

    def test_is_active_when_unregistered(self, sample_registration):
        """Test is_active returns False for unregistered service."""
        sample_registration.registration_status = "unregistered"
        assert sample_registration.is_active() is False

    def test_is_active_when_unhealthy(self, sample_registration):
        """Test is_active returns False for unhealthy service."""
        sample_registration.health_status = "unhealthy"
        assert sample_registration.is_active() is False

    def test_is_active_when_degraded(self, sample_registration):
        """Test is_active returns False for degraded service."""
        sample_registration.health_status = "degraded"
        assert sample_registration.is_active() is False

    def test_mark_accessed_updates_time_and_count(self, sample_registration):
        """Test mark_accessed updates last access time and count."""
        assert sample_registration.last_access_time is None
        assert sample_registration.access_count == 0

        initial_time = datetime.now()
        sample_registration.mark_accessed()

        assert sample_registration.last_access_time is not None
        assert sample_registration.last_access_time >= initial_time
        assert sample_registration.access_count == 1

        # Mark accessed again
        sample_registration.mark_accessed()
        assert sample_registration.access_count == 2

    def test_increment_instance_count(self, sample_registration):
        """Test increment_instance_count increases count."""
        assert sample_registration.instance_count == 0

        sample_registration.increment_instance_count()
        assert sample_registration.instance_count == 1

        sample_registration.increment_instance_count()
        assert sample_registration.instance_count == 2

    def test_decrement_instance_count(self, sample_registration):
        """Test decrement_instance_count decreases count."""
        sample_registration.instance_count = 3

        sample_registration.decrement_instance_count()
        assert sample_registration.instance_count == 2

        sample_registration.decrement_instance_count()
        assert sample_registration.instance_count == 1

    def test_decrement_instance_count_minimum_zero(self, sample_registration):
        """Test decrement_instance_count doesn't go below zero."""
        sample_registration.instance_count = 0

        sample_registration.decrement_instance_count()
        assert sample_registration.instance_count == 0

        # Should still be zero
        sample_registration.decrement_instance_count()
        assert sample_registration.instance_count == 0

    def test_lifecycle_types(self, sample_metadata):
        """Test different lifecycle types."""
        for lifecycle in ["singleton", "transient", "scoped", "pooled"]:
            registration = ModelServiceRegistration(
                registration_id=uuid4(),
                service_metadata=sample_metadata,
                lifecycle=lifecycle,  # type: ignore
                scope="global",
            )
            assert registration.lifecycle == lifecycle

    def test_scope_types(self, sample_metadata):
        """Test different scope types."""
        for scope in ["global", "request", "session", "custom"]:
            registration = ModelServiceRegistration(
                registration_id=uuid4(),
                service_metadata=sample_metadata,
                lifecycle="singleton",
                scope=scope,  # type: ignore
            )
            assert registration.scope == scope

    def test_registration_status_types(self, sample_metadata):
        """Test different registration status types."""
        for status in [
            "registered",
            "unregistered",
            "failed",
            "pending",
            "conflict",
            "invalid",
        ]:
            registration = ModelServiceRegistration(
                registration_id=uuid4(),
                service_metadata=sample_metadata,
                lifecycle="singleton",
                scope="global",
                registration_status=status,  # type: ignore
            )
            assert registration.registration_status == status

    def test_health_status_types(self, sample_metadata):
        """Test different health status types."""
        for health in ["healthy", "unhealthy", "degraded", "unknown"]:
            registration = ModelServiceRegistration(
                registration_id=uuid4(),
                service_metadata=sample_metadata,
                lifecycle="singleton",
                scope="global",
                health_status=health,  # type: ignore
            )
            assert registration.health_status == health

    def test_max_instances_for_pooled_lifecycle(self, sample_metadata):
        """Test max_instances configuration for pooled lifecycle."""
        registration = ModelServiceRegistration(
            registration_id=uuid4(),
            service_metadata=sample_metadata,
            lifecycle="pooled",
            scope="global",
            max_instances=5,
        )

        assert registration.max_instances == 5
        assert registration.lifecycle == "pooled"

    def test_dependencies_list(self, sample_metadata):
        """Test dependencies list handling."""
        dependencies = ["service_a", "service_b", "service_c"]
        registration = ModelServiceRegistration(
            registration_id=uuid4(),
            service_metadata=sample_metadata,
            lifecycle="singleton",
            scope="global",
            dependencies=dependencies,
        )

        assert registration.dependencies == dependencies
        assert len(registration.dependencies) == 3

    def test_serialization_deserialization(self, sample_registration):
        """Test model can be serialized and deserialized."""
        # Serialize to dict
        data = sample_registration.model_dump()

        # Deserialize from dict
        restored = ModelServiceRegistration(**data)

        assert restored.registration_id == sample_registration.registration_id
        assert restored.service_metadata == sample_registration.service_metadata
        assert restored.lifecycle == sample_registration.lifecycle
        assert restored.scope == sample_registration.scope
        assert restored.registration_status == sample_registration.registration_status

    def test_registration_workflow(self, sample_registration):
        """Test typical registration workflow."""
        # Initial state - pending
        sample_registration.registration_status = "pending"
        sample_registration.health_status = "unknown"
        assert not sample_registration.is_active()

        # Registration succeeds
        sample_registration.registration_status = "registered"
        sample_registration.health_status = "healthy"
        assert sample_registration.is_active()

        # Service gets accessed
        sample_registration.mark_accessed()
        assert sample_registration.access_count == 1

        # Instance created
        sample_registration.increment_instance_count()
        assert sample_registration.instance_count == 1

        # Service becomes degraded
        sample_registration.health_status = "degraded"
        assert not sample_registration.is_active()

        # Service recovered
        sample_registration.health_status = "healthy"
        assert sample_registration.is_active()

        # Service unregistered
        sample_registration.registration_status = "unregistered"
        assert not sample_registration.is_active()
