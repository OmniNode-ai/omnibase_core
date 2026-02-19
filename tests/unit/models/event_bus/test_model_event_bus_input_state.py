# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEventBusInputState.

Comprehensive tests for event bus input state model including:
- Construction with valid inputs
- Field validation
- Factory methods
- Business logic methods
- Serialization and deserialization
- Edge cases
"""

import os
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_event_bus_input_state import (
    ModelEventBusInputState,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelEventBusInputStateConstruction:
    """Test ModelEventBusInputState construction."""

    def test_create_with_required_fields(self) -> None:
        """Test creating input state with required fields only."""
        state = ModelEventBusInputState(input_field="test_input")

        assert state.input_field == "test_input"
        assert state.version is not None
        assert state.priority == "normal"

    def test_create_with_all_fields(self) -> None:
        """Test creating input state with all fields."""
        correlation_id = uuid4()
        event_id = uuid4()

        state = ModelEventBusInputState(
            version="1.2.3",
            input_field="test_input",
            correlation_id=correlation_id,
            event_id=event_id,
            integration=True,
            priority="high",
            timeout_seconds=60,
            retry_count=5,
        )

        assert state.input_field == "test_input"
        assert state.version.major == 1
        assert state.version.minor == 2
        assert state.version.patch == 3
        assert state.correlation_id == correlation_id
        assert state.event_id == event_id
        assert state.integration is True
        assert state.priority == "high"
        assert state.timeout_seconds == 60
        assert state.retry_count == 5

    def test_create_with_model_semver(self) -> None:
        """Test creating input state with ModelSemVer instance."""
        version = ModelSemVer(major=2, minor=0, patch=0)

        state = ModelEventBusInputState(
            version=version,
            input_field="test",
        )

        assert state.version == version


@pytest.mark.unit
class TestModelEventBusInputStateInputFieldValidation:
    """Test ModelEventBusInputState input_field validation."""

    def test_input_field_required(self) -> None:
        """Test that input_field is required."""
        with pytest.raises(ValidationError):
            ModelEventBusInputState()  # type: ignore[call-arg]

    def test_input_field_empty_raises_error(self) -> None:
        """Test that empty input_field raises error (min_length=1)."""
        with pytest.raises(ValidationError):
            ModelEventBusInputState(input_field="")

    def test_input_field_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only input_field raises error."""
        with pytest.raises(ModelOnexError):
            ModelEventBusInputState(input_field="   ")

    def test_input_field_dangerous_patterns(self) -> None:
        """Test that dangerous patterns in input_field are rejected."""
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "vbscript:msgbox(1)",
            "<div onload=alert(1)>",
            "<img onerror=alert(1)>",
        ]

        for dangerous_input in dangerous_inputs:
            with pytest.raises(ModelOnexError):
                ModelEventBusInputState(input_field=dangerous_input)

    def test_input_field_strips_whitespace(self) -> None:
        """Test that input_field strips leading/trailing whitespace."""
        state = ModelEventBusInputState(input_field="  test  ")

        assert state.input_field == "test"

    def test_input_field_max_length(self) -> None:
        """Test input_field maximum length constraint."""
        long_input = "x" * 1000  # Max is 1000

        state = ModelEventBusInputState(input_field=long_input)

        assert len(state.input_field) == 1000

    def test_input_field_exceeds_max_length(self) -> None:
        """Test that exceeding max length raises error."""
        too_long = "x" * 1001

        with pytest.raises(ValidationError):
            ModelEventBusInputState(input_field=too_long)


@pytest.mark.unit
class TestModelEventBusInputStatePriorityValidation:
    """Test ModelEventBusInputState priority validation."""

    @pytest.mark.parametrize("priority", ["low", "normal", "high", "critical"])
    def test_valid_priority_values(self, priority: str) -> None:
        """Test that valid priority values are accepted."""
        state = ModelEventBusInputState(input_field="test", priority=priority)

        assert state.priority == priority

    def test_invalid_priority_raises_error(self) -> None:
        """Test that invalid priority values are rejected."""
        with pytest.raises(ValidationError):
            ModelEventBusInputState(input_field="test", priority="invalid")


@pytest.mark.unit
class TestModelEventBusInputStateTimeoutValidation:
    """Test ModelEventBusInputState timeout_seconds validation."""

    def test_valid_timeout_seconds(self) -> None:
        """Test that valid timeout values are accepted."""
        state = ModelEventBusInputState(input_field="test", timeout_seconds=100)

        assert state.timeout_seconds == 100

    def test_timeout_seconds_minimum(self) -> None:
        """Test timeout_seconds minimum value constraint."""
        state = ModelEventBusInputState(input_field="test", timeout_seconds=1)

        assert state.timeout_seconds == 1

    def test_timeout_seconds_maximum(self) -> None:
        """Test timeout_seconds maximum value constraint."""
        state = ModelEventBusInputState(input_field="test", timeout_seconds=3600)

        assert state.timeout_seconds == 3600

    def test_timeout_seconds_below_minimum_raises_error(self) -> None:
        """Test that timeout below minimum raises error."""
        with pytest.raises(ValidationError):
            ModelEventBusInputState(input_field="test", timeout_seconds=0)

    def test_timeout_seconds_above_maximum_raises_error(self) -> None:
        """Test that timeout above maximum raises error."""
        with pytest.raises(ValidationError):
            ModelEventBusInputState(input_field="test", timeout_seconds=3601)


@pytest.mark.unit
class TestModelEventBusInputStateRetryValidation:
    """Test ModelEventBusInputState retry_count validation."""

    def test_retry_count_minimum(self) -> None:
        """Test retry_count minimum value constraint."""
        state = ModelEventBusInputState(input_field="test", retry_count=0)

        assert state.retry_count == 0

    def test_retry_count_maximum(self) -> None:
        """Test retry_count maximum value constraint."""
        state = ModelEventBusInputState(input_field="test", retry_count=10)

        assert state.retry_count == 10

    def test_retry_count_below_minimum_raises_error(self) -> None:
        """Test that retry_count below minimum raises error."""
        with pytest.raises(ValidationError):
            ModelEventBusInputState(input_field="test", retry_count=-1)

    def test_retry_count_above_maximum_raises_error(self) -> None:
        """Test that retry_count above maximum raises error."""
        with pytest.raises(ValidationError):
            ModelEventBusInputState(input_field="test", retry_count=11)


@pytest.mark.unit
class TestModelEventBusInputStatePriorityMethods:
    """Test ModelEventBusInputState priority-related methods."""

    def test_get_processing_priority_low(self) -> None:
        """Test get_processing_priority for low priority."""
        state = ModelEventBusInputState(input_field="test", priority="low")

        assert state.get_processing_priority() == 1

    def test_get_processing_priority_normal(self) -> None:
        """Test get_processing_priority for normal priority."""
        state = ModelEventBusInputState(input_field="test", priority="normal")

        assert state.get_processing_priority() == 5

    def test_get_processing_priority_high(self) -> None:
        """Test get_processing_priority for high priority."""
        state = ModelEventBusInputState(input_field="test", priority="high")

        assert state.get_processing_priority() == 8

    def test_get_processing_priority_critical(self) -> None:
        """Test get_processing_priority for critical priority."""
        state = ModelEventBusInputState(input_field="test", priority="critical")

        assert state.get_processing_priority() == 10

    def test_is_high_priority_returns_true_for_high(self) -> None:
        """Test is_high_priority returns True for high priority."""
        state = ModelEventBusInputState(input_field="test", priority="high")

        assert state.is_high_priority() is True

    def test_is_high_priority_returns_true_for_critical(self) -> None:
        """Test is_high_priority returns True for critical priority."""
        state = ModelEventBusInputState(input_field="test", priority="critical")

        assert state.is_high_priority() is True

    def test_is_high_priority_returns_false_for_normal(self) -> None:
        """Test is_high_priority returns False for normal priority."""
        state = ModelEventBusInputState(input_field="test", priority="normal")

        assert state.is_high_priority() is False

    def test_is_high_priority_returns_false_for_low(self) -> None:
        """Test is_high_priority returns False for low priority."""
        state = ModelEventBusInputState(input_field="test", priority="low")

        assert state.is_high_priority() is False


@pytest.mark.unit
class TestModelEventBusInputStateTimeoutMethods:
    """Test ModelEventBusInputState timeout-related methods."""

    def test_get_effective_timeout_normal_priority(self) -> None:
        """Test get_effective_timeout for normal priority."""
        state = ModelEventBusInputState(
            input_field="test",
            priority="normal",
            timeout_seconds=30,
        )

        assert state.get_effective_timeout() == 30

    def test_get_effective_timeout_high_priority_doubles(self) -> None:
        """Test get_effective_timeout doubles for high priority."""
        state = ModelEventBusInputState(
            input_field="test",
            priority="high",
            timeout_seconds=30,
        )

        assert state.get_effective_timeout() == 60

    def test_get_effective_timeout_high_priority_capped_at_3600(self) -> None:
        """Test get_effective_timeout is capped at 3600 for high priority."""
        state = ModelEventBusInputState(
            input_field="test",
            priority="high",
            timeout_seconds=2000,
        )

        assert state.get_effective_timeout() == 3600

    def test_get_effective_timeout_default_value(self) -> None:
        """Test get_effective_timeout uses default when timeout is None."""
        state = ModelEventBusInputState(input_field="test")
        state_dict = state.model_dump()
        state_dict["timeout_seconds"] = None
        state = ModelEventBusInputState.model_validate(state_dict)

        # Default is 30
        result = state.get_effective_timeout()
        assert result == 30


@pytest.mark.unit
class TestModelEventBusInputStateRetryStrategy:
    """Test ModelEventBusInputState retry strategy methods."""

    def test_get_retry_strategy_normal_priority(self) -> None:
        """Test get_retry_strategy for normal priority."""
        state = ModelEventBusInputState(
            input_field="test",
            priority="normal",
            retry_count=3,
        )

        strategy = state.get_retry_strategy()

        assert strategy.max_retries == 3
        assert strategy.backoff_multiplier == 1.5
        assert strategy.max_backoff == 30

    def test_get_retry_strategy_high_priority(self) -> None:
        """Test get_retry_strategy for high priority."""
        state = ModelEventBusInputState(
            input_field="test",
            priority="high",
            retry_count=3,
        )

        strategy = state.get_retry_strategy()

        assert strategy.max_retries == 5  # 3 + 2 for high priority
        assert strategy.backoff_multiplier == 2.0
        assert strategy.max_backoff == 60


@pytest.mark.unit
class TestModelEventBusInputStateTrackingMetadata:
    """Test ModelEventBusInputState tracking metadata methods."""

    def test_get_tracking_metadata_basic(self) -> None:
        """Test get_tracking_metadata returns basic fields."""
        state = ModelEventBusInputState(input_field="test")

        metadata = state.get_tracking_metadata()

        assert "version" in metadata
        assert "priority" in metadata
        assert "timestamp" in metadata

    def test_get_tracking_metadata_with_ids(self) -> None:
        """Test get_tracking_metadata includes correlation and event IDs."""
        correlation_id = uuid4()
        event_id = uuid4()

        state = ModelEventBusInputState(
            input_field="test",
            correlation_id=correlation_id,
            event_id=event_id,
        )

        metadata = state.get_tracking_metadata()

        assert metadata["correlation_id"] == str(correlation_id)
        assert metadata["event_id"] == str(event_id)


@pytest.mark.unit
class TestModelEventBusInputStateValidation:
    """Test ModelEventBusInputState validation methods."""

    def test_validate_for_processing_valid_state(self) -> None:
        """Test validate_for_processing returns empty list for valid state."""
        state = ModelEventBusInputState(
            version="1.0.0",
            input_field="test",
            timeout_seconds=30,
        )

        issues = state.validate_for_processing()

        assert len(issues) == 0

    def test_validate_for_processing_pre_release_version(self) -> None:
        """Test validate_for_processing warns about pre-release versions."""
        state = ModelEventBusInputState(
            version="0.1.0",
            input_field="test",
        )

        issues = state.validate_for_processing()

        assert any("Pre-release" in issue for issue in issues)

    def test_validate_for_processing_short_timeout(self) -> None:
        """Test validate_for_processing warns about short timeout."""
        state = ModelEventBusInputState(
            input_field="test",
            timeout_seconds=3,
        )

        issues = state.validate_for_processing()

        assert any("5 seconds" in issue for issue in issues)

    def test_is_valid_for_processing_true(self) -> None:
        """Test is_valid_for_processing returns True for valid state."""
        state = ModelEventBusInputState(
            version="1.0.0",
            input_field="test",
            timeout_seconds=30,
        )

        assert state.is_valid_for_processing() is True

    def test_is_valid_for_processing_false(self) -> None:
        """Test is_valid_for_processing returns False with issues."""
        state = ModelEventBusInputState(
            version="0.1.0",
            input_field="test",
            timeout_seconds=3,
        )

        assert state.is_valid_for_processing() is False


@pytest.mark.unit
class TestModelEventBusInputStateFactoryMethods:
    """Test ModelEventBusInputState factory methods."""

    def test_create_basic(self) -> None:
        """Test create_basic factory method."""
        state = ModelEventBusInputState.create_basic("1.0.0", "test_input")

        assert state.input_field == "test_input"
        assert state.version.major == 1

    def test_create_basic_with_model_semver(self) -> None:
        """Test create_basic with ModelSemVer."""
        version = ModelSemVer(major=2, minor=1, patch=0)

        state = ModelEventBusInputState.create_basic(version, "test")

        assert state.version == version

    def test_create_with_tracking(self) -> None:
        """Test create_with_tracking factory method."""
        correlation_id = uuid4()

        state = ModelEventBusInputState.create_with_tracking(
            version="1.0.0",
            input_field="test",
            correlation_id=correlation_id,
        )

        assert state.correlation_id == correlation_id
        assert state.event_id is not None

    def test_create_high_priority(self) -> None:
        """Test create_high_priority factory method."""
        state = ModelEventBusInputState.create_high_priority(
            version="1.0.0",
            input_field="urgent_task",
        )

        assert state.priority == "high"
        assert state.timeout_seconds == 60
        assert state.retry_count == 5

    def test_create_high_priority_custom_timeout(self) -> None:
        """Test create_high_priority with custom timeout."""
        state = ModelEventBusInputState.create_high_priority(
            version="1.0.0",
            input_field="urgent",
            timeout_seconds=120,
        )

        assert state.timeout_seconds == 120


@pytest.mark.unit
class TestModelEventBusInputStateEnvironmentMethods:
    """Test ModelEventBusInputState environment-related methods."""

    def test_get_environment_mapping(self) -> None:
        """Test get_environment_mapping returns correct mappings."""
        state = ModelEventBusInputState(input_field="test")

        mapping = state.get_environment_mapping()

        assert "timeout_seconds" in mapping
        assert mapping["timeout_seconds"] == "ONEX_EVENT_BUS_TIMEOUT_SECONDS"
        assert mapping["priority"] == "ONEX_EVENT_BUS_PRIORITY"

    def test_get_environment_mapping_custom_prefix(self) -> None:
        """Test get_environment_mapping with custom prefix."""
        state = ModelEventBusInputState(input_field="test")

        mapping = state.get_environment_mapping(env_prefix="CUSTOM_")

        assert mapping["timeout_seconds"] == "CUSTOM_TIMEOUT_SECONDS"

    def test_apply_environment_overrides_no_env_vars(self) -> None:
        """Test apply_environment_overrides with no env vars set."""
        state = ModelEventBusInputState(
            input_field="test",
            timeout_seconds=30,
        )

        result = state.apply_environment_overrides()

        assert result.timeout_seconds == 30  # Unchanged

    def test_apply_environment_overrides_with_env_vars(self) -> None:
        """Test apply_environment_overrides with env vars set."""
        state = ModelEventBusInputState(
            input_field="test",
            timeout_seconds=30,
            priority="normal",
        )

        # Set environment variable
        os.environ["ONEX_EVENT_BUS_TIMEOUT_SECONDS"] = "60"
        os.environ["ONEX_EVENT_BUS_PRIORITY"] = "high"

        try:
            result = state.apply_environment_overrides()

            assert result.timeout_seconds == 60
            assert result.priority == "high"
        finally:
            # Clean up
            del os.environ["ONEX_EVENT_BUS_TIMEOUT_SECONDS"]
            del os.environ["ONEX_EVENT_BUS_PRIORITY"]


@pytest.mark.unit
class TestModelEventBusInputStateSerialization:
    """Test ModelEventBusInputState serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump() serialization."""
        state = ModelEventBusInputState(
            input_field="test",
            priority="high",
        )

        data = state.model_dump()

        assert isinstance(data, dict)
        assert data["input_field"] == "test"
        assert data["priority"] == "high"

    def test_model_validate(self) -> None:
        """Test model_validate() deserialization."""
        data = {
            "input_field": "test_input",
            "priority": "normal",
        }

        state = ModelEventBusInputState.model_validate(data)

        assert state.input_field == "test_input"
        assert state.priority == "normal"

    def test_serialization_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusInputState(
            version="1.2.3",
            input_field="test_input",
            priority="high",
            timeout_seconds=60,
        )

        data = original.model_dump()
        restored = ModelEventBusInputState.model_validate(data)

        assert restored.input_field == original.input_field
        assert restored.priority == original.priority
        assert restored.timeout_seconds == original.timeout_seconds

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        state = ModelEventBusInputState(input_field="test")

        json_data = state.model_dump_json()

        assert isinstance(json_data, str)
        assert "input_field" in json_data
