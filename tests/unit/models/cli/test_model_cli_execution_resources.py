# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive tests for ModelCliExecutionResources.

Tests resource limits, retry logic, timeout checks, user context,
and factory methods for CLI execution resources.
"""

import uuid

import pytest

from omnibase_core.models.cli.model_cli_execution_resources import (
    ModelCliExecutionResources,
)


@pytest.mark.unit
class TestModelCliExecutionResourcesBasic:
    """Test basic resource creation and configuration."""

    def test_create_unlimited_resources(self) -> None:
        """Test creating unlimited resources (no constraints)."""
        resources = ModelCliExecutionResources.create_unlimited()

        assert resources.timeout_seconds is None
        assert resources.max_memory_mb is None
        assert resources.max_retries == 0
        assert resources.retry_count == 0
        assert resources.user_id is None
        assert resources.session_id is None

    def test_create_limited_resources(self) -> None:
        """Test creating resources with limits."""
        resources = ModelCliExecutionResources.create_limited(
            timeout_seconds=120,
            max_memory_mb=512,
            max_retries=5,
        )

        assert resources.timeout_seconds == 120
        assert resources.max_memory_mb == 512
        assert resources.max_retries == 5
        assert resources.retry_count == 0

    def test_create_quick_resources(self) -> None:
        """Test creating quick operation resources."""
        resources = ModelCliExecutionResources.create_quick()

        assert resources.timeout_seconds == 30
        assert resources.max_memory_mb == 256
        assert resources.max_retries == 1
        assert resources.retry_count == 0

    def test_default_construction(self) -> None:
        """Test default constructor creates unlimited resources."""
        resources = ModelCliExecutionResources()

        assert resources.timeout_seconds is None
        assert resources.max_memory_mb is None
        assert resources.max_retries == 0
        assert resources.retry_count == 0

    def test_custom_configuration(self) -> None:
        """Test custom resource configuration."""
        resources = ModelCliExecutionResources(
            timeout_seconds=300,
            max_memory_mb=2048,
            max_retries=10,
            retry_count=0,
        )

        assert resources.timeout_seconds == 300
        assert resources.max_memory_mb == 2048
        assert resources.max_retries == 10
        assert resources.retry_count == 0


@pytest.mark.unit
class TestModelCliExecutionResourcesTimeouts:
    """Test timeout checking functionality."""

    def test_is_timed_out_no_limit(self) -> None:
        """Test timeout check when no limit is set."""
        resources = ModelCliExecutionResources.create_unlimited()

        # No timeout limit means never times out
        assert not resources.is_timed_out(0.0)
        assert not resources.is_timed_out(1000.0)
        assert not resources.is_timed_out(999999.0)

    def test_is_timed_out_within_limit(self) -> None:
        """Test timeout check when within limit."""
        resources = ModelCliExecutionResources(timeout_seconds=60)

        assert not resources.is_timed_out(0.0)
        assert not resources.is_timed_out(30.0)
        assert not resources.is_timed_out(59.9)
        assert not resources.is_timed_out(60.0)

    def test_is_timed_out_exceeded(self) -> None:
        """Test timeout check when limit exceeded."""
        resources = ModelCliExecutionResources(timeout_seconds=60)

        assert resources.is_timed_out(60.1)
        assert resources.is_timed_out(100.0)
        assert resources.is_timed_out(1000.0)

    def test_is_timed_out_boundary_conditions(self) -> None:
        """Test timeout boundary conditions."""
        resources = ModelCliExecutionResources(timeout_seconds=1)

        assert not resources.is_timed_out(0.999)
        assert not resources.is_timed_out(1.0)
        assert resources.is_timed_out(1.001)


@pytest.mark.unit
class TestModelCliExecutionResourcesRetries:
    """Test retry logic and counter management."""

    def test_increment_retry_available(self) -> None:
        """Test incrementing retry when more retries available."""
        resources = ModelCliExecutionResources(max_retries=3)

        # First retry
        assert resources.retry_count == 0
        assert resources.increment_retry()
        assert resources.retry_count == 1

        # Second retry
        assert resources.increment_retry()
        assert resources.retry_count == 2

        # Third retry
        assert resources.increment_retry()
        assert resources.retry_count == 3

    def test_increment_retry_exhausted(self) -> None:
        """Test incrementing retry when no retries left."""
        resources = ModelCliExecutionResources(max_retries=1)

        # First retry succeeds
        assert resources.increment_retry()
        assert resources.retry_count == 1

        # Second retry fails (max_retries=1 means only 1 retry)
        assert not resources.increment_retry()
        assert resources.retry_count == 2

    def test_can_attempt_retry_available(self) -> None:
        """Test checking retry availability when retries available."""
        resources = ModelCliExecutionResources(max_retries=3)

        assert resources.can_attempt_retry()  # 0 < 3

        resources.retry_count = 1
        assert resources.can_attempt_retry()  # 1 < 3

        resources.retry_count = 2
        assert resources.can_attempt_retry()  # 2 < 3

    def test_can_attempt_retry_exhausted(self) -> None:
        """Test checking retry availability when exhausted."""
        resources = ModelCliExecutionResources(max_retries=3, retry_count=3)

        assert not resources.can_attempt_retry()  # 3 < 3 is False

        resources.retry_count = 4
        assert not resources.can_attempt_retry()  # 4 < 3 is False

    def test_reset_retries(self) -> None:
        """Test resetting retry counter."""
        resources = ModelCliExecutionResources(max_retries=5, retry_count=3)

        assert resources.retry_count == 3
        resources.reset_retries()
        assert resources.retry_count == 0

    def test_retry_workflow(self) -> None:
        """Test complete retry workflow."""
        resources = ModelCliExecutionResources(max_retries=2)

        # Initial state
        assert resources.can_attempt_retry()

        # First attempt fails, retry
        assert resources.increment_retry()
        assert resources.retry_count == 1
        assert resources.can_attempt_retry()

        # Second attempt fails, retry
        assert resources.increment_retry()
        assert resources.retry_count == 2
        assert not resources.can_attempt_retry()

        # Third attempt fails, no more retries
        assert not resources.increment_retry()
        assert resources.retry_count == 3

        # Reset for new operation
        resources.reset_retries()
        assert resources.retry_count == 0
        assert resources.can_attempt_retry()

    def test_no_retries_allowed(self) -> None:
        """Test behavior when max_retries=0."""
        resources = ModelCliExecutionResources(max_retries=0)

        assert not resources.can_attempt_retry()
        assert not resources.increment_retry()
        assert resources.retry_count == 1


@pytest.mark.unit
class TestModelCliExecutionResourcesUserContext:
    """Test user and session context management."""

    def test_set_user_context_full(self) -> None:
        """Test setting user context with session."""
        resources = ModelCliExecutionResources()
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()

        resources.set_user_context(user_id, session_id)

        assert resources.user_id == user_id
        assert resources.session_id == session_id

    def test_set_user_context_no_session(self) -> None:
        """Test setting user context without session."""
        resources = ModelCliExecutionResources()
        user_id = uuid.uuid4()

        resources.set_user_context(user_id)

        assert resources.user_id == user_id
        assert resources.session_id is None

    def test_set_user_context_overwrite(self) -> None:
        """Test overwriting existing user context."""
        resources = ModelCliExecutionResources()
        user_id_1 = uuid.uuid4()
        session_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        session_id_2 = uuid.uuid4()

        resources.set_user_context(user_id_1, session_id_1)
        assert resources.user_id == user_id_1
        assert resources.session_id == session_id_1

        resources.set_user_context(user_id_2, session_id_2)
        assert resources.user_id == user_id_2
        assert resources.session_id == session_id_2

    def test_user_context_in_constructor(self) -> None:
        """Test setting user context via constructor."""
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()

        resources = ModelCliExecutionResources(
            user_id=user_id,
            session_id=session_id,
        )

        assert resources.user_id == user_id
        assert resources.session_id == session_id


@pytest.mark.unit
class TestModelCliExecutionResourcesProtocols:
    """Test protocol method implementations (Serializable, Nameable, Validatable)."""

    def test_serialize(self) -> None:
        """Test serialization to dictionary."""
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        resources = ModelCliExecutionResources(
            timeout_seconds=120,
            max_memory_mb=1024,
            max_retries=3,
            retry_count=1,
            user_id=user_id,
            session_id=session_id,
        )

        serialized = resources.serialize()

        assert isinstance(serialized, dict)
        assert serialized["timeout_seconds"] == 120
        assert serialized["max_memory_mb"] == 1024
        assert serialized["max_retries"] == 3
        assert serialized["retry_count"] == 1
        assert serialized["user_id"] == user_id
        assert serialized["session_id"] == session_id

    def test_get_name(self) -> None:
        """Test getting name via Nameable protocol."""
        resources = ModelCliExecutionResources()

        # Should return default name since model has no name field
        name = resources.get_name()
        assert "ModelCliExecutionResources" in name

    def test_set_name(self) -> None:
        """Test setting name via Nameable protocol."""
        resources = ModelCliExecutionResources()

        # Should not raise even though model has no name field
        resources.set_name("CustomName")

    def test_validate_instance(self) -> None:
        """Test instance validation via Validatable protocol."""
        resources = ModelCliExecutionResources()

        assert resources.validate_instance() is True


@pytest.mark.unit
class TestModelCliExecutionResourcesValidation:
    """Test Pydantic validation and constraints."""

    def test_timeout_seconds_positive(self) -> None:
        """Test timeout_seconds must be positive if set."""
        # Valid values
        ModelCliExecutionResources(timeout_seconds=1)
        ModelCliExecutionResources(timeout_seconds=9999)

        # Invalid values
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelCliExecutionResources(timeout_seconds=0)

        with pytest.raises(Exception):
            ModelCliExecutionResources(timeout_seconds=-1)

    def test_max_memory_mb_positive(self) -> None:
        """Test max_memory_mb must be positive if set."""
        # Valid values
        ModelCliExecutionResources(max_memory_mb=1)
        ModelCliExecutionResources(max_memory_mb=16384)

        # Invalid values
        with pytest.raises(Exception):
            ModelCliExecutionResources(max_memory_mb=0)

        with pytest.raises(Exception):
            ModelCliExecutionResources(max_memory_mb=-100)

    def test_max_retries_non_negative(self) -> None:
        """Test max_retries must be non-negative."""
        # Valid values
        ModelCliExecutionResources(max_retries=0)
        ModelCliExecutionResources(max_retries=100)

        # Invalid values
        with pytest.raises(Exception):
            ModelCliExecutionResources(max_retries=-1)

    def test_retry_count_non_negative(self) -> None:
        """Test retry_count must be non-negative."""
        # Valid values
        ModelCliExecutionResources(retry_count=0)
        ModelCliExecutionResources(retry_count=10)

        # Invalid values
        with pytest.raises(Exception):
            ModelCliExecutionResources(retry_count=-1)


@pytest.mark.unit
class TestModelCliExecutionResourcesEdgeCases:
    """Test edge cases and complex scenarios."""

    def test_serialization_with_none_values(self) -> None:
        """Test serialization includes None values."""
        resources = ModelCliExecutionResources.create_unlimited()
        serialized = resources.serialize()

        assert "timeout_seconds" in serialized
        assert "max_memory_mb" in serialized
        assert "user_id" in serialized
        assert "session_id" in serialized

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip maintains data integrity."""
        original = ModelCliExecutionResources(
            timeout_seconds=60,
            max_memory_mb=512,
            max_retries=3,
            retry_count=1,
        )

        serialized = original.serialize()
        restored = ModelCliExecutionResources(**serialized)

        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.max_memory_mb == original.max_memory_mb
        assert restored.max_retries == original.max_retries
        assert restored.retry_count == original.retry_count

    def test_validate_assignment_enabled(self) -> None:
        """Test that validate_assignment is enabled in model_config."""
        resources = ModelCliExecutionResources(timeout_seconds=60)

        # Should validate on assignment
        with pytest.raises(Exception):
            resources.timeout_seconds = -1  # Invalid value

    def test_factory_method_defaults(self) -> None:
        """Test factory methods use reasonable defaults."""
        limited = ModelCliExecutionResources.create_limited()
        assert limited.timeout_seconds == 300
        assert limited.max_memory_mb == 1024
        assert limited.max_retries == 3

        quick = ModelCliExecutionResources.create_quick()
        assert quick.timeout_seconds == 30
        assert quick.max_memory_mb == 256
        assert quick.max_retries == 1

    def test_complex_retry_scenario(self) -> None:
        """Test complex retry scenario with multiple operations."""
        resources = ModelCliExecutionResources(max_retries=2)

        # Operation 1: Success on first try
        assert resources.can_attempt_retry()
        resources.reset_retries()

        # Operation 2: Requires all retries
        assert resources.increment_retry()  # 1st retry
        assert resources.increment_retry()  # 2nd retry
        assert not resources.increment_retry()  # No more retries

        # Operation 3: Start fresh
        resources.reset_retries()
        assert resources.can_attempt_retry()
