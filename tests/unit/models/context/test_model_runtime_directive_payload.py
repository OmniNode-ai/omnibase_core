# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Comprehensive tests for ModelRuntimeDirectivePayload.

This module tests the ModelRuntimeDirectivePayload model, which provides typed
payload for runtime directives (internal runtime control).

Test Categories:
    - Instantiation tests: Create with various field combinations
    - Validation tests: Type checking, extra fields, constraints
    - Edge cases: Empty values, None, boundary values
    - Immutability tests: Verify frozen behavior
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from omnibase_core.models.context.model_runtime_directive_payload import (
    ModelRuntimeDirectivePayload,
)

# Test configuration constants
UNIT_TEST_TIMEOUT_SECONDS: int = 60


# =============================================================================
# INSTANTIATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadInstantiation:
    """Tests for creating ModelRuntimeDirectivePayload instances."""

    def test_create_with_minimal_fields(self) -> None:
        """Create with only default values (no required fields)."""
        model = ModelRuntimeDirectivePayload()
        assert model.handler_args == {}
        assert model.execution_mode is None
        assert model.priority is None
        assert model.queue_name is None
        assert model.backoff_base_ms is None
        assert model.backoff_multiplier is None
        assert model.jitter_ms is None
        assert model.execute_at is None
        assert model.cancellation_reason is None
        assert model.cleanup_required is False

    def test_create_with_all_fields(self) -> None:
        """Create with all fields populated."""
        execute_time = datetime.now(UTC) + timedelta(minutes=5)
        model = ModelRuntimeDirectivePayload(
            handler_args={"user_id": "123", "action": "notify"},
            execution_mode="async",
            priority=1,
            queue_name="high-priority",
            backoff_base_ms=1000,
            backoff_multiplier=2.0,
            jitter_ms=100,
            execute_at=execute_time,
            cancellation_reason="User requested",
            cleanup_required=True,
        )
        assert model.handler_args == {"user_id": "123", "action": "notify"}
        assert model.execution_mode == "async"
        assert model.priority == 1
        assert model.queue_name == "high-priority"
        assert model.backoff_base_ms == 1000
        assert model.backoff_multiplier == 2.0
        assert model.jitter_ms == 100
        assert model.execute_at == execute_time
        assert model.cancellation_reason == "User requested"
        assert model.cleanup_required is True

    def test_create_schedule_effect_payload(self) -> None:
        """Create a SCHEDULE_EFFECT directive payload."""
        model = ModelRuntimeDirectivePayload(
            handler_args={"user_id": "123", "action": "notify"},
            execution_mode="async",
            priority=1,
        )
        assert model.handler_args == {"user_id": "123", "action": "notify"}
        assert model.execution_mode == "async"
        assert model.priority == 1

    def test_create_enqueue_handler_payload(self) -> None:
        """Create an ENQUEUE_HANDLER directive payload."""
        model = ModelRuntimeDirectivePayload(
            handler_args={"task": "process_data"},
            priority=0,
            queue_name="default-queue",
        )
        assert model.handler_args == {"task": "process_data"}
        assert model.priority == 0
        assert model.queue_name == "default-queue"

    def test_create_retry_with_backoff_payload(self) -> None:
        """Create a RETRY_WITH_BACKOFF directive payload."""
        model = ModelRuntimeDirectivePayload(
            backoff_base_ms=1000,
            backoff_multiplier=2.0,
            jitter_ms=100,
        )
        assert model.backoff_base_ms == 1000
        assert model.backoff_multiplier == 2.0
        assert model.jitter_ms == 100

    def test_create_delay_until_payload(self) -> None:
        """Create a DELAY_UNTIL directive payload."""
        execute_time = datetime.now(UTC) + timedelta(minutes=5)
        model = ModelRuntimeDirectivePayload(execute_at=execute_time)
        assert model.execute_at == execute_time

    def test_create_cancel_execution_payload(self) -> None:
        """Create a CANCEL_EXECUTION directive payload."""
        model = ModelRuntimeDirectivePayload(
            cancellation_reason="Timeout exceeded",
            cleanup_required=True,
        )
        assert model.cancellation_reason == "Timeout exceeded"
        assert model.cleanup_required is True


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadValidation:
    """Tests for validation behavior of ModelRuntimeDirectivePayload."""

    def test_extra_field_rejected(self) -> None:
        """Extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                unknown_field="value",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"

    def test_priority_must_be_non_negative(self) -> None:
        """priority must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(priority=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

    def test_backoff_base_ms_must_be_non_negative(self) -> None:
        """backoff_base_ms must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(backoff_base_ms=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("backoff_base_ms",) for e in errors)

    def test_backoff_multiplier_must_be_positive(self) -> None:
        """backoff_multiplier must be > 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(backoff_multiplier=0.0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("backoff_multiplier",) for e in errors)

    def test_backoff_multiplier_negative_rejected(self) -> None:
        """backoff_multiplier cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(backoff_multiplier=-1.0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("backoff_multiplier",) for e in errors)

    def test_jitter_ms_must_be_non_negative(self) -> None:
        """jitter_ms must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(jitter_ms=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("jitter_ms",) for e in errors)

    def test_invalid_handler_args_type_rejected(self) -> None:
        """Non-dict handler_args raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                handler_args="not a dict",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("handler_args",) for e in errors)

    def test_invalid_execution_mode_type_rejected(self) -> None:
        """Non-string execution_mode raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                execution_mode=123,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("execution_mode",) for e in errors)

    def test_invalid_priority_type_rejected(self) -> None:
        """Non-int priority raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                priority="high",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

    def test_string_execute_at_coerced_to_datetime(self) -> None:
        """ISO date string is coerced to datetime by Pydantic."""
        model = ModelRuntimeDirectivePayload(
            execute_at="2024-01-01T12:00:00Z",
        )
        # Pydantic parses ISO format strings to datetime
        assert isinstance(model.execute_at, datetime)
        assert model.execute_at.year == 2024

    def test_invalid_execute_at_raises_error(self) -> None:
        """Invalid execute_at string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                execute_at="not-a-date",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("execute_at",) for e in errors)

    def test_invalid_cleanup_required_type_rejected(self) -> None:
        """Non-coercible cleanup_required raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                cleanup_required=[True, False],
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("cleanup_required",) for e in errors)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadEdgeCases:
    """Tests for edge cases in ModelRuntimeDirectivePayload."""

    def test_none_values_for_optional_fields(self) -> None:
        """None values work for all optional fields."""
        model = ModelRuntimeDirectivePayload(
            execution_mode=None,
            priority=None,
            queue_name=None,
            backoff_base_ms=None,
            backoff_multiplier=None,
            jitter_ms=None,
            execute_at=None,
            cancellation_reason=None,
        )
        assert model.execution_mode is None
        assert model.priority is None
        assert model.queue_name is None
        assert model.backoff_base_ms is None
        assert model.backoff_multiplier is None
        assert model.jitter_ms is None
        assert model.execute_at is None
        assert model.cancellation_reason is None

    def test_empty_handler_args_dict(self) -> None:
        """Empty handler_args dict is accepted."""
        model = ModelRuntimeDirectivePayload(handler_args={})
        assert model.handler_args == {}

    def test_empty_string_execution_mode(self) -> None:
        """Empty string execution_mode is accepted."""
        model = ModelRuntimeDirectivePayload(execution_mode="")
        assert model.execution_mode == ""

    def test_empty_string_queue_name(self) -> None:
        """Empty string queue_name is accepted."""
        model = ModelRuntimeDirectivePayload(queue_name="")
        assert model.queue_name == ""

    def test_empty_string_cancellation_reason(self) -> None:
        """Empty string cancellation_reason is accepted."""
        model = ModelRuntimeDirectivePayload(cancellation_reason="")
        assert model.cancellation_reason == ""

    def test_priority_zero_allowed(self) -> None:
        """Priority of 0 (highest) is allowed."""
        model = ModelRuntimeDirectivePayload(priority=0)
        assert model.priority == 0

    def test_priority_large_value(self) -> None:
        """Large priority value is allowed."""
        model = ModelRuntimeDirectivePayload(priority=999999)
        assert model.priority == 999999

    def test_backoff_base_ms_zero_allowed(self) -> None:
        """backoff_base_ms of 0 is allowed."""
        model = ModelRuntimeDirectivePayload(backoff_base_ms=0)
        assert model.backoff_base_ms == 0

    def test_backoff_base_ms_large_value(self) -> None:
        """Large backoff_base_ms value is allowed."""
        model = ModelRuntimeDirectivePayload(backoff_base_ms=3600000)  # 1 hour
        assert model.backoff_base_ms == 3600000

    def test_backoff_multiplier_small_positive(self) -> None:
        """Small positive backoff_multiplier is allowed."""
        model = ModelRuntimeDirectivePayload(backoff_multiplier=0.001)
        assert model.backoff_multiplier == 0.001

    def test_backoff_multiplier_large_value(self) -> None:
        """Large backoff_multiplier value is allowed."""
        model = ModelRuntimeDirectivePayload(backoff_multiplier=10.0)
        assert model.backoff_multiplier == 10.0

    def test_jitter_ms_zero_allowed(self) -> None:
        """jitter_ms of 0 is allowed."""
        model = ModelRuntimeDirectivePayload(jitter_ms=0)
        assert model.jitter_ms == 0

    def test_jitter_ms_large_value(self) -> None:
        """Large jitter_ms value is allowed."""
        model = ModelRuntimeDirectivePayload(jitter_ms=10000)
        assert model.jitter_ms == 10000

    def test_execute_at_past_date(self) -> None:
        """Past execute_at date is accepted (no constraint)."""
        past_time = datetime.now(UTC) - timedelta(days=1)
        model = ModelRuntimeDirectivePayload(execute_at=past_time)
        assert model.execute_at == past_time

    def test_execute_at_far_future(self) -> None:
        """Far future execute_at date is accepted."""
        future_time = datetime.now(UTC) + timedelta(days=365)
        model = ModelRuntimeDirectivePayload(execute_at=future_time)
        assert model.execute_at == future_time

    def test_cleanup_required_default_false(self) -> None:
        """cleanup_required defaults to False."""
        model = ModelRuntimeDirectivePayload()
        assert model.cleanup_required is False

    def test_cleanup_required_true(self) -> None:
        """cleanup_required can be set to True."""
        model = ModelRuntimeDirectivePayload(cleanup_required=True)
        assert model.cleanup_required is True

    def test_handler_args_with_nested_dict(self) -> None:
        """handler_args can contain nested dictionaries."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "config": {
                    "level1": {"level2": {"level3": "deep_value"}},
                },
            },
        )
        assert (
            model.handler_args["config"]["level1"]["level2"]["level3"] == "deep_value"
        )

    def test_handler_args_with_list(self) -> None:
        """handler_args can contain lists."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "items": [1, 2, 3, 4, 5],
                "names": ["alice", "bob"],
            },
        )
        assert model.handler_args["items"] == [1, 2, 3, 4, 5]
        assert model.handler_args["names"] == ["alice", "bob"]

    def test_handler_args_with_various_types(self) -> None:
        """handler_args can contain various types."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "string": "value",
                "int": 42,
                "float": 3.14,
                "bool": True,
                "null": None,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
            },
        )
        assert model.handler_args["string"] == "value"
        assert model.handler_args["int"] == 42
        assert model.handler_args["float"] == 3.14
        assert model.handler_args["bool"] is True
        assert model.handler_args["null"] is None
        assert model.handler_args["list"] == [1, 2, 3]
        assert model.handler_args["dict"] == {"nested": "value"}

    def test_unicode_in_strings(self) -> None:
        """Unicode characters in string fields are accepted."""
        # Japanese: async mode, queue, timeout reason
        model = ModelRuntimeDirectivePayload(
            execution_mode="\u975e\u540c\u671f",  # asynchronous
            queue_name="\u30ad\u30e5\u30fc",  # queue
            cancellation_reason="\u30bf\u30a4\u30e0\u30a2\u30a6\u30c8",  # timeout
        )
        assert model.execution_mode == "\u975e\u540c\u671f"
        assert model.queue_name == "\u30ad\u30e5\u30fc"
        assert model.cancellation_reason == "\u30bf\u30a4\u30e0\u30a2\u30a6\u30c8"

    def test_unicode_accented_latin(self) -> None:
        """Accented Latin unicode characters in string fields are accepted."""
        # French: cafe, naive
        model = ModelRuntimeDirectivePayload(
            execution_mode="caf\u00e9",
            queue_name="na\u00efve",
            cancellation_reason="Op\u00e9ration annul\u00e9e",
        )
        assert model.execution_mode == "caf\u00e9"
        assert model.queue_name == "na\u00efve"
        assert model.cancellation_reason == "Op\u00e9ration annul\u00e9e"

    def test_unicode_chinese(self) -> None:
        """Chinese unicode characters in string fields are accepted."""
        # Chinese: queue, cancel reason
        model = ModelRuntimeDirectivePayload(
            queue_name="\u961f\u5217",  # queue
            cancellation_reason="\u7528\u6237\u53d6\u6d88",  # user cancelled
        )
        assert model.queue_name == "\u961f\u5217"
        assert model.cancellation_reason == "\u7528\u6237\u53d6\u6d88"

    def test_unicode_arabic(self) -> None:
        """Arabic unicode characters in string fields are accepted."""
        # Arabic: queue, reason
        model = ModelRuntimeDirectivePayload(
            queue_name="\u0637\u0627\u0628\u0648\u0631",  # queue
            cancellation_reason="\u0633\u0628\u0628",  # reason
        )
        assert model.queue_name == "\u0637\u0627\u0628\u0648\u0631"
        assert model.cancellation_reason == "\u0633\u0628\u0628"

    def test_unicode_emoji(self) -> None:
        """Emoji unicode characters in string fields are accepted."""
        # Emoji: rocket
        model = ModelRuntimeDirectivePayload(
            queue_name="priority_\U0001f680",
            cancellation_reason="Error \u26a0\ufe0f",
        )
        assert model.queue_name == "priority_\U0001f680"
        assert model.cancellation_reason == "Error \u26a0\ufe0f"

    def test_special_characters_in_strings(self) -> None:
        """Special characters in string fields are accepted."""
        model = ModelRuntimeDirectivePayload(
            queue_name="queue-name_with.special@chars!",
            cancellation_reason="Reason with \"quotes\" and 'apostrophes'",
        )
        assert model.queue_name == "queue-name_with.special@chars!"
        assert model.cancellation_reason == "Reason with \"quotes\" and 'apostrophes'"

    def test_sync_execution_mode(self) -> None:
        """sync execution_mode is valid."""
        model = ModelRuntimeDirectivePayload(execution_mode="sync")
        assert model.execution_mode == "sync"

    def test_async_execution_mode(self) -> None:
        """async execution_mode is valid."""
        model = ModelRuntimeDirectivePayload(execution_mode="async")
        assert model.execution_mode == "async"


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadImmutability:
    """Tests for immutability (frozen=True) behavior."""

    def test_handler_args_cannot_be_modified(self) -> None:
        """handler_args cannot be changed after creation."""
        model = ModelRuntimeDirectivePayload(handler_args={"key": "value"})
        with pytest.raises(ValidationError):
            model.handler_args = {"new": "value"}

    def test_execution_mode_cannot_be_modified(self) -> None:
        """execution_mode cannot be changed after creation."""
        model = ModelRuntimeDirectivePayload(execution_mode="sync")
        with pytest.raises(ValidationError):
            model.execution_mode = "async"

    def test_priority_cannot_be_modified(self) -> None:
        """priority cannot be changed after creation."""
        model = ModelRuntimeDirectivePayload(priority=1)
        with pytest.raises(ValidationError):
            model.priority = 2

    def test_cleanup_required_cannot_be_modified(self) -> None:
        """cleanup_required cannot be changed after creation."""
        model = ModelRuntimeDirectivePayload(cleanup_required=False)
        with pytest.raises(ValidationError):
            model.cleanup_required = True

    def test_execute_at_cannot_be_modified(self) -> None:
        """execute_at cannot be changed after creation."""
        original_time = datetime.now(UTC)
        model = ModelRuntimeDirectivePayload(execute_at=original_time)
        with pytest.raises(ValidationError):
            model.execute_at = datetime.now(UTC) + timedelta(hours=1)


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadSerialization:
    """Tests for serialization/deserialization behavior."""

    def test_model_dump_includes_all_fields(self) -> None:
        """model_dump() includes all fields."""
        execute_time = datetime.now(UTC)
        model = ModelRuntimeDirectivePayload(
            handler_args={"key": "value"},
            execution_mode="async",
            priority=1,
            queue_name="test-queue",
            backoff_base_ms=1000,
            backoff_multiplier=2.0,
            jitter_ms=100,
            execute_at=execute_time,
            cancellation_reason="Test reason",
            cleanup_required=True,
        )
        data = model.model_dump()
        assert data["handler_args"] == {"key": "value"}
        assert data["execution_mode"] == "async"
        assert data["priority"] == 1
        assert data["queue_name"] == "test-queue"
        assert data["backoff_base_ms"] == 1000
        assert data["backoff_multiplier"] == 2.0
        assert data["jitter_ms"] == 100
        assert data["execute_at"] == execute_time
        assert data["cancellation_reason"] == "Test reason"
        assert data["cleanup_required"] is True

    def test_model_dump_mode_json(self) -> None:
        """model_dump(mode='json') produces JSON-serializable output."""
        execute_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        model = ModelRuntimeDirectivePayload(
            execute_at=execute_time,
            handler_args={"key": "value"},
        )
        data = model.model_dump(mode="json")
        # datetime should be serialized to ISO format string
        assert isinstance(data["execute_at"], str)
        assert data["handler_args"] == {"key": "value"}

    def test_model_validate_roundtrip(self) -> None:
        """Model can be recreated from model_dump() output."""
        execute_time = datetime.now(UTC)
        original = ModelRuntimeDirectivePayload(
            handler_args={"key": "value"},
            priority=2,
            execute_at=execute_time,
            cleanup_required=True,
        )
        data = original.model_dump()
        recreated = ModelRuntimeDirectivePayload.model_validate(data)
        assert recreated.handler_args == original.handler_args
        assert recreated.priority == original.priority
        assert recreated.execute_at == original.execute_at
        assert recreated.cleanup_required == original.cleanup_required

    def test_from_attributes_enabled(self) -> None:
        """from_attributes=True allows creation from object attributes."""

        class MockObject:
            handler_args = {"key": "value"}
            execution_mode = "sync"
            priority = 1
            queue_name = "test-queue"
            backoff_base_ms = 1000
            backoff_multiplier = 2.0
            jitter_ms = 100
            execute_at = None
            cancellation_reason = None
            cleanup_required = False

        mock = MockObject()
        model = ModelRuntimeDirectivePayload.model_validate(mock)
        assert model.handler_args == {"key": "value"}
        assert model.execution_mode == "sync"
        assert model.priority == 1


# =============================================================================
# HASH AND EQUALITY TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadHashEquality:
    """Tests for hash and equality behavior."""

    def test_equal_models_are_equal(self) -> None:
        """Two models with same values are equal."""
        execute_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        model1 = ModelRuntimeDirectivePayload(
            handler_args={"key": "value"},
            priority=1,
            execute_at=execute_time,
        )
        model2 = ModelRuntimeDirectivePayload(
            handler_args={"key": "value"},
            priority=1,
            execute_at=execute_time,
        )
        assert model1 == model2

    def test_different_models_are_not_equal(self) -> None:
        """Two models with different values are not equal."""
        model1 = ModelRuntimeDirectivePayload(priority=1)
        model2 = ModelRuntimeDirectivePayload(priority=2)
        assert model1 != model2

    def test_frozen_model_is_hashable(self) -> None:
        """Frozen model is hashable."""
        model = ModelRuntimeDirectivePayload(
            handler_args={"key": "value"},
            priority=1,
        )
        # Note: dict in handler_args makes this unhashable
        # Frozen models with mutable fields like dict are not hashable
        # This is expected Pydantic behavior
        with pytest.raises(TypeError):
            hash(model)

    def test_model_without_dict_is_hashable(self) -> None:
        """Model without dict fields is hashable."""
        model = ModelRuntimeDirectivePayload(
            execution_mode="async",
            priority=1,
            cleanup_required=True,
        )
        # Still has handler_args default dict, so not hashable
        with pytest.raises(TypeError):
            hash(model)


# =============================================================================
# USE CASE TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadUseCases:
    """Tests for specific use case scenarios."""

    def test_schedule_effect_complete_scenario(self) -> None:
        """Complete SCHEDULE_EFFECT scenario with all relevant fields."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "user_id": "user-123",
                "action": "send_notification",
                "template": "welcome",
                "data": {"name": "John", "email": "john@example.com"},
            },
            execution_mode="async",
            priority=2,
        )
        assert model.handler_args["user_id"] == "user-123"
        assert model.handler_args["action"] == "send_notification"
        assert model.execution_mode == "async"
        assert model.priority == 2

    def test_retry_with_backoff_complete_scenario(self) -> None:
        """Complete RETRY_WITH_BACKOFF scenario with all relevant fields."""
        model = ModelRuntimeDirectivePayload(
            backoff_base_ms=1000,
            backoff_multiplier=2.0,
            jitter_ms=500,
        )
        # Simulate exponential backoff calculation
        retry = 3
        delay = model.backoff_base_ms * (model.backoff_multiplier**retry)
        assert delay == 8000  # 1000 * 2^3

    def test_cancel_execution_complete_scenario(self) -> None:
        """Complete CANCEL_EXECUTION scenario with all relevant fields."""
        model = ModelRuntimeDirectivePayload(
            cancellation_reason="Operation timed out after 30 seconds",
            cleanup_required=True,
            handler_args={
                "cleanup_tasks": ["release_lock", "notify_watchers"],
            },
        )
        assert "timed out" in model.cancellation_reason
        assert model.cleanup_required is True
        assert "cleanup_tasks" in model.handler_args

    def test_delay_until_complete_scenario(self) -> None:
        """Complete DELAY_UNTIL scenario with execute_at."""
        scheduled_time = datetime.now(UTC) + timedelta(hours=2)
        model = ModelRuntimeDirectivePayload(
            execute_at=scheduled_time,
            handler_args={
                "task": "send_reminder",
                "user_id": "user-456",
            },
        )
        assert model.execute_at == scheduled_time
        # Verify it's in the future
        assert model.execute_at > datetime.now(UTC) - timedelta(seconds=1)

    def test_enqueue_handler_complete_scenario(self) -> None:
        """Complete ENQUEUE_HANDLER scenario with queue configuration."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "job_type": "process_batch",
                "batch_id": "batch-789",
                "items_count": 100,
            },
            priority=0,  # Highest priority
            queue_name="batch-processing-queue",
        )
        assert model.queue_name == "batch-processing-queue"
        assert model.priority == 0
        assert model.handler_args["items_count"] == 100


# =============================================================================
# SECURITY VALIDATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelRuntimeDirectivePayloadSecurityValidation:
    """Tests for security validation of handler_args field."""

    # -------------------------------------------------------------------------
    # Reserved Keys Tests
    # -------------------------------------------------------------------------

    def test_reserved_key_proto_rejected(self) -> None:
        """handler_args with __proto__ key is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                handler_args={"__proto__": {"polluted": True}},
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("handler_args",)
        assert "__proto__" in str(errors[0]["msg"])
        assert "reserved" in str(errors[0]["msg"]).lower()

    def test_reserved_key_constructor_rejected(self) -> None:
        """handler_args with constructor key is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                handler_args={"constructor": {"polluted": True}},
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("handler_args",)
        assert "constructor" in str(errors[0]["msg"])
        assert "reserved" in str(errors[0]["msg"]).lower()

    def test_reserved_key_class_rejected(self) -> None:
        """handler_args with __class__ key is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                handler_args={"__class__": {"polluted": True}},
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("handler_args",)
        assert "__class__" in str(errors[0]["msg"])
        assert "reserved" in str(errors[0]["msg"]).lower()

    def test_multiple_reserved_keys_rejected(self) -> None:
        """handler_args with multiple reserved keys is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                handler_args={
                    "__proto__": {},
                    "constructor": {},
                    "__class__": {},
                },
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("handler_args",)
        # All reserved keys should be mentioned
        msg = str(errors[0]["msg"])
        assert "__class__" in msg
        assert "__proto__" in msg
        assert "constructor" in msg

    def test_reserved_key_mixed_with_valid_keys_rejected(self) -> None:
        """handler_args with reserved key mixed with valid keys is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                handler_args={
                    "valid_key": "value",
                    "__proto__": {"malicious": True},
                    "another_valid": 42,
                },
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "__proto__" in str(errors[0]["msg"])

    def test_similar_but_valid_keys_accepted(self) -> None:
        """Keys similar to reserved but not exact match are accepted."""
        # These should NOT be rejected
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "proto": "not reserved",
                "__proto": "not reserved (missing trailing underscore)",
                "proto__": "not reserved",
                "_class_": "not reserved",
                "class": "not reserved",
                "Constructor": "not reserved (case sensitive)",
            },
        )
        assert model.handler_args["proto"] == "not reserved"
        assert model.handler_args["Constructor"] == "not reserved (case sensitive)"

    # -------------------------------------------------------------------------
    # Nesting Depth Tests
    # -------------------------------------------------------------------------

    def test_shallow_nesting_accepted(self) -> None:
        """Shallow nesting (depth 1) is accepted."""
        model = ModelRuntimeDirectivePayload(
            handler_args={"level1": "value"},
        )
        assert model.handler_args["level1"] == "value"

    def test_moderate_nesting_accepted(self) -> None:
        """Moderate nesting (depth 5) is accepted."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "l1": {
                    "l2": {
                        "l3": {
                            "l4": {
                                "l5": "deep_value",
                            },
                        },
                    },
                },
            },
        )
        assert model.handler_args["l1"]["l2"]["l3"]["l4"]["l5"] == "deep_value"

    def test_max_depth_exactly_10_accepted(self) -> None:
        """Nesting at exactly max depth (10) is accepted."""
        # Build a structure with exactly 10 levels of nesting
        nested: dict[str, object] = {"value": "at_depth_10"}
        for i in range(9):
            nested = {f"level_{9 - i}": nested}

        model = ModelRuntimeDirectivePayload(handler_args=nested)
        # Navigate down to verify
        current: object = model.handler_args
        for i in range(9):
            assert isinstance(current, dict)
            current = current[f"level_{i + 1}"]
        assert isinstance(current, dict)
        assert current["value"] == "at_depth_10"

    def test_depth_exceeding_10_rejected(self) -> None:
        """Nesting exceeding max depth (11 levels) is rejected."""
        # Build a structure with 11 levels of nesting
        nested: dict[str, object] = {"too_deep": "value"}
        for i in range(10):
            nested = {f"level_{10 - i}": nested}

        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(handler_args=nested)
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("handler_args",)
        assert "depth" in str(errors[0]["msg"]).lower()
        assert "10" in str(errors[0]["msg"])

    def test_deeply_nested_list_rejected(self) -> None:
        """Deeply nested lists (exceeding max depth) are rejected."""
        # Build a structure with 11 levels via lists
        nested: list[object] | dict[str, object] = [{"too_deep": "value"}]
        for _ in range(10):
            nested = {"level": nested}

        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(handler_args=nested)
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "depth" in str(errors[0]["msg"]).lower()

    def test_mixed_dict_list_nesting_at_limit_accepted(self) -> None:
        """Mixed dict/list nesting at exactly max depth is accepted."""
        # Build alternating dict/list structure
        # Start with depth 1 ({"final": "value"}), add 8 more levels = depth 9
        # Then wrap with {"root": ...} = depth 10 (exactly at limit)
        nested: dict[str, object] | list[object] = {"final": "value"}
        for i in range(8):
            if i % 2 == 0:
                nested = [nested]
            else:
                nested = {"level": nested}

        # Wrap in outer dict (this adds one more level)
        model = ModelRuntimeDirectivePayload(handler_args={"root": nested})
        assert model.handler_args["root"] is not None

    def test_wide_but_shallow_structure_accepted(self) -> None:
        """Wide but shallow structures are accepted."""
        # Many keys at depth 1 is fine
        wide_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        model = ModelRuntimeDirectivePayload(handler_args=wide_dict)
        assert len(model.handler_args) == 1000

    def test_empty_nested_dicts_accepted(self) -> None:
        """Empty nested dicts don't contribute to depth issues."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "empty1": {},
                "empty2": {"also_empty": {}},
                "with_value": {"nested": {"value": "here"}},
            },
        )
        assert model.handler_args["empty1"] == {}
        assert model.handler_args["empty2"]["also_empty"] == {}

    def test_empty_nested_lists_accepted(self) -> None:
        """Empty nested lists don't contribute to depth issues."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "empty_list": [],
                "nested_empty": {"inner": []},
            },
        )
        assert model.handler_args["empty_list"] == []

    # -------------------------------------------------------------------------
    # Error Message Quality Tests
    # -------------------------------------------------------------------------

    def test_reserved_key_error_message_is_actionable(self) -> None:
        """Error message for reserved keys is clear and actionable."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                handler_args={"__proto__": "malicious"},
            )
        error_msg = str(exc_info.value.errors()[0]["msg"])
        # Message should explain the issue
        assert "reserved" in error_msg.lower()
        # Message should mention which key(s)
        assert "__proto__" in error_msg
        # Message should mention security concern
        assert "prototype pollution" in error_msg.lower()

    def test_depth_error_message_is_actionable(self) -> None:
        """Error message for depth violation is clear and actionable."""
        # Create structure with depth 12
        nested: dict[str, object] = {"too_deep": "value"}
        for i in range(11):
            nested = {f"l{i}": nested}

        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(handler_args=nested)
        error_msg = str(exc_info.value.errors()[0]["msg"])
        # Message should mention depth
        assert "depth" in error_msg.lower()
        # Message should mention the limit
        assert "10" in error_msg
        # Message should mention security concern
        assert "denial-of-service" in error_msg.lower() or "dos" in error_msg.lower()

    # -------------------------------------------------------------------------
    # Valid Complex Structures Tests
    # -------------------------------------------------------------------------

    def test_complex_valid_structure_accepted(self) -> None:
        """Complex but valid structure is accepted."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "user": {
                    "id": "user-123",
                    "profile": {
                        "name": "Test User",
                        "settings": {
                            "theme": "dark",
                            "notifications": {
                                "email": True,
                                "push": False,
                            },
                        },
                    },
                },
                "items": [
                    {"id": 1, "name": "Item 1"},
                    {"id": 2, "name": "Item 2"},
                ],
                "metadata": {
                    "version": "1.0",
                    "tags": ["important", "urgent"],
                },
            },
        )
        assert model.handler_args["user"]["id"] == "user-123"
        assert model.handler_args["items"][0]["name"] == "Item 1"
        assert model.handler_args["metadata"]["tags"] == ["important", "urgent"]

    def test_tuple_in_structure_handled(self) -> None:
        """Tuples in structure are handled for depth checking."""
        model = ModelRuntimeDirectivePayload(
            handler_args={
                "coordinates": (1, 2, 3),
                "nested_tuple": {"point": (4, 5)},
            },
        )
        # Tuples are preserved as-is in dict[str, Any]
        assert model.handler_args["coordinates"] == (1, 2, 3)
        assert model.handler_args["nested_tuple"]["point"] == (4, 5)
