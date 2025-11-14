"""Tests for ModelServiceInstance."""

from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.models.container.model_service_instance import ModelServiceInstance


class MockService:
    """Mock service for testing."""

    def __init__(self, name: str):
        self.name = name


@pytest.fixture
def sample_instance():
    """Create sample service instance."""
    return ModelServiceInstance(
        instance_id=uuid4(),
        service_registration_id=uuid4(),
        instance=MockService("test"),
        lifecycle="singleton",
        scope="global",
    )


class TestModelServiceInstance:
    """Tests for ModelServiceInstance model."""

    def test_initialization_with_defaults(self):
        """Test instance initialization with default values."""
        inst_id = uuid4()
        reg_id = uuid4()
        mock_service = MockService("test")

        instance = ModelServiceInstance(
            instance_id=inst_id,
            service_registration_id=reg_id,
            instance=mock_service,
            lifecycle="singleton",
            scope="global",
        )

        assert instance.instance_id == inst_id
        assert instance.service_registration_id == reg_id
        assert instance.instance == mock_service
        assert instance.lifecycle == "singleton"
        assert instance.scope == "global"
        assert isinstance(instance.created_at, datetime)
        assert isinstance(instance.last_accessed, datetime)
        assert instance.access_count == 0
        assert instance.is_disposed is False
        assert instance.metadata == {}

    def test_initialization_with_all_fields(self):
        """Test instance initialization with all fields."""
        inst_id = uuid4()
        reg_id = uuid4()
        mock_service = MockService("test")
        created = datetime.now()
        accessed = datetime.now()
        metadata = {"key1": "value1", "key2": 123}

        instance = ModelServiceInstance(
            instance_id=inst_id,
            service_registration_id=reg_id,
            instance=mock_service,
            lifecycle="transient",
            scope="request",
            created_at=created,
            last_accessed=accessed,
            access_count=5,
            is_disposed=False,
            metadata=metadata,
        )

        assert instance.created_at == created
        assert instance.last_accessed == accessed
        assert instance.access_count == 5
        assert instance.is_disposed is False
        assert instance.metadata == metadata

    @pytest.mark.asyncio
    async def test_validate_instance_valid(self, sample_instance):
        """Test validation of valid instance."""
        assert await sample_instance.validate_instance() is True

    @pytest.mark.asyncio
    async def test_validate_instance_disposed(self, sample_instance):
        """Test validation fails for disposed instance."""
        sample_instance.is_disposed = True
        assert await sample_instance.validate_instance() is False

    @pytest.mark.asyncio
    async def test_validate_instance_none(self, sample_instance):
        """Test validation fails for None instance."""
        sample_instance.instance = None
        assert await sample_instance.validate_instance() is False

    @pytest.mark.asyncio
    async def test_validate_instance_disposed_and_none(self, sample_instance):
        """Test validation fails for disposed and None instance."""
        sample_instance.is_disposed = True
        sample_instance.instance = None
        assert await sample_instance.validate_instance() is False

    def test_is_active_when_not_disposed(self, sample_instance):
        """Test is_active returns True when not disposed."""
        assert sample_instance.is_active() is True

    def test_is_active_when_disposed(self, sample_instance):
        """Test is_active returns False when disposed."""
        sample_instance.is_disposed = True
        assert sample_instance.is_active() is False

    def test_mark_accessed_updates_time_and_count(self, sample_instance):
        """Test mark_accessed updates timestamp and count."""
        initial_count = sample_instance.access_count
        initial_time = sample_instance.last_accessed

        # Wait a moment to ensure time difference
        sample_instance.mark_accessed()

        assert sample_instance.access_count == initial_count + 1
        assert sample_instance.last_accessed >= initial_time

        # Mark again
        sample_instance.mark_accessed()
        assert sample_instance.access_count == initial_count + 2

    def test_dispose_marks_disposed_and_clears_instance(self, sample_instance):
        """Test dispose marks instance as disposed and clears reference."""
        assert sample_instance.is_disposed is False
        assert sample_instance.instance is not None

        sample_instance.dispose()

        assert sample_instance.is_disposed is True
        assert sample_instance.instance is None

    def test_lifecycle_types(self):
        """Test different lifecycle types."""
        inst_id = uuid4()
        reg_id = uuid4()

        for lifecycle in ["singleton", "transient", "scoped", "pooled"]:
            instance = ModelServiceInstance(
                instance_id=inst_id,
                service_registration_id=reg_id,
                instance=MockService("test"),
                lifecycle=lifecycle,  # type: ignore[arg-type]
                scope="global",
            )
            assert instance.lifecycle == lifecycle

    def test_scope_types(self):
        """Test different scope types."""
        inst_id = uuid4()
        reg_id = uuid4()

        for scope in ["global", "request", "session", "custom"]:
            instance = ModelServiceInstance(
                instance_id=inst_id,
                service_registration_id=reg_id,
                instance=MockService("test"),
                lifecycle="singleton",
                scope=scope,  # type: ignore[arg-type]
            )
            assert instance.scope == scope

    def test_metadata_tracking(self, sample_instance):
        """Test metadata tracking."""
        sample_instance.metadata = {
            "pool_size": 10,
            "max_age_seconds": 300,
            "priority": "high",
        }

        assert sample_instance.metadata["pool_size"] == 10
        assert sample_instance.metadata["max_age_seconds"] == 300
        assert sample_instance.metadata["priority"] == "high"

    def test_instance_lifecycle(self):
        """Test typical instance lifecycle."""
        instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance=MockService("lifecycle_test"),
            lifecycle="transient",
            scope="request",
        )

        # Initial state
        assert instance.is_active()
        assert instance.access_count == 0

        # Used several times
        for _ in range(5):
            instance.mark_accessed()

        assert instance.access_count == 5
        assert instance.is_active()

        # Disposed
        instance.dispose()
        assert not instance.is_active()
        assert instance.is_disposed
        assert instance.instance is None

    def test_singleton_instance(self):
        """Test singleton instance tracking."""
        singleton_service = MockService("singleton")
        instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance=singleton_service,
            lifecycle="singleton",
            scope="global",
        )

        # Accessed multiple times
        for _ in range(100):
            instance.mark_accessed()

        # Should still be active with high access count
        assert instance.is_active()
        assert instance.access_count == 100
        assert instance.instance is singleton_service

    def test_transient_instance(self):
        """Test transient instance (typically disposed quickly)."""
        transient_service = MockService("transient")
        instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance=transient_service,
            lifecycle="transient",
            scope="request",
        )

        # Used once
        instance.mark_accessed()
        assert instance.access_count == 1

        # Disposed after use
        instance.dispose()
        assert not instance.is_active()

    def test_scoped_instance_with_metadata(self):
        """Test scoped instance with scope metadata."""
        scoped_service = MockService("scoped")
        instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance=scoped_service,
            lifecycle="scoped",
            scope="session",
            metadata={"session_id": "session-123", "user_id": "user-456"},
        )

        assert instance.lifecycle == "scoped"
        assert instance.scope == "session"
        assert instance.metadata["session_id"] == "session-123"
        assert instance.metadata["user_id"] == "user-456"

    def test_pooled_instance_with_tracking(self):
        """Test pooled instance with pool metadata."""
        pooled_service = MockService("pooled")
        instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance=pooled_service,
            lifecycle="pooled",
            scope="global",
            metadata={"pool_index": 3, "pool_name": "worker_pool"},
        )

        assert instance.lifecycle == "pooled"
        assert instance.metadata["pool_index"] == 3
        assert instance.metadata["pool_name"] == "worker_pool"

    def test_arbitrary_instance_types(self):
        """Test that arbitrary types are allowed for instance."""

        # Simple types
        string_instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance="string_service",
            lifecycle="singleton",
            scope="global",
        )
        assert string_instance.instance == "string_service"

        # Dict
        dict_instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance={"key": "value"},
            lifecycle="singleton",
            scope="global",
        )
        assert dict_instance.instance == {"key": "value"}

        # Lambda
        lambda_instance = ModelServiceInstance(
            instance_id=uuid4(),
            service_registration_id=uuid4(),
            instance=lambda x: x * 2,
            lifecycle="singleton",
            scope="global",
        )
        assert lambda_instance.instance(5) == 10
