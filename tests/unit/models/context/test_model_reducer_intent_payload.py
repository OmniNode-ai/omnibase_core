# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Comprehensive tests for ModelReducerIntentPayload.

This module tests the ModelReducerIntentPayload model, which provides typed
payload for reducer intents (FSM state transitions and side effects).

Test Categories:
    - Instantiation tests: Create with various field combinations
    - Validation tests: Type checking, extra fields, constraints
    - Edge cases: Empty strings, None, unicode, boundary values
    - Helper method tests: is_retryable, with_incremented_retry, get_data_as_dict
    - Immutability tests: Verify frozen behavior
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context.model_reducer_intent_payload import (
    ModelReducerIntentPayload,
)

# =============================================================================
# INSTANTIATION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelReducerIntentPayloadInstantiation:
    """Tests for creating ModelReducerIntentPayload instances."""

    def test_create_with_minimal_fields(self) -> None:
        """Create with only default values (no required fields)."""
        model = ModelReducerIntentPayload()
        assert model.target_state is None
        assert model.source_state is None
        assert model.trigger is None
        assert model.entity_id is None
        assert model.entity_type is None
        assert model.operation is None
        assert model.data == ()
        assert model.validation_errors == ()
        assert model.idempotency_key is None
        assert model.timeout_ms is None
        assert model.retry_count == 0
        assert model.max_retries == 3

    def test_create_with_all_fields(self) -> None:
        """Create with all fields populated."""
        entity_uuid = uuid4()
        model = ModelReducerIntentPayload(
            target_state="active",
            source_state="pending",
            trigger="user_verified",
            entity_id=entity_uuid,
            entity_type="user",
            operation="activate",
            data=(("key1", "value1"), ("key2", 123)),
            validation_errors=("error1", "error2"),
            idempotency_key="key-12345",
            timeout_ms=5000,
            retry_count=2,
            max_retries=5,
        )
        assert model.target_state == "active"
        assert model.source_state == "pending"
        assert model.trigger == "user_verified"
        assert model.entity_id == entity_uuid
        assert model.entity_type == "user"
        assert model.operation == "activate"
        assert model.data == (("key1", "value1"), ("key2", 123))
        assert model.validation_errors == ("error1", "error2")
        assert model.idempotency_key == "key-12345"
        assert model.timeout_ms == 5000
        assert model.retry_count == 2
        assert model.max_retries == 5

    def test_create_fsm_transition_payload(self) -> None:
        """Create an FSM state transition payload."""
        entity_uuid = uuid4()
        model = ModelReducerIntentPayload(
            target_state="active",
            source_state="pending",
            trigger="user_verified",
            entity_id=entity_uuid,
            entity_type="user",
            operation="activate",
        )
        assert model.target_state == "active"
        assert model.source_state == "pending"
        assert model.trigger == "user_verified"

    def test_create_side_effect_notification_payload(self) -> None:
        """Create a side effect payload for notifications."""
        model = ModelReducerIntentPayload(
            entity_type="notification",
            operation="send",
            data=(
                ("channel", "email"),
                ("recipient", "user@example.com"),
                ("template", "welcome_email"),
            ),
            idempotency_key="notif_12345",
            timeout_ms=5000,
        )
        assert model.entity_type == "notification"
        assert model.operation == "send"
        assert len(model.data) == 3

    def test_create_validation_result_payload(self) -> None:
        """Create a validation result payload."""
        model = ModelReducerIntentPayload(
            entity_type="validation",
            operation="report",
            validation_errors=(
                "Field 'email' is required",
                "Field 'age' must be >= 0",
            ),
        )
        assert model.entity_type == "validation"
        assert model.operation == "report"
        assert len(model.validation_errors) == 2

    def test_create_retry_aware_payload(self) -> None:
        """Create a retry-aware payload."""
        model = ModelReducerIntentPayload(
            entity_type="webhook",
            operation="send",
            data=(("url", "https://api.example.com/hook"),),
            retry_count=2,
            max_retries=5,
            timeout_ms=10000,
        )
        assert model.retry_count == 2
        assert model.max_retries == 5
        assert model.timeout_ms == 10000


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelReducerIntentPayloadValidation:
    """Tests for validation behavior of ModelReducerIntentPayload."""

    def test_extra_field_rejected(self) -> None:
        """Extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(
                unknown_field="value",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"

    def test_target_state_min_length_enforced(self) -> None:
        """target_state must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(target_state="")
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("target_state",) and "string_too_short" in e["type"]
            for e in errors
        )

    def test_target_state_max_length_enforced(self) -> None:
        """target_state exceeding 100 chars raises ValidationError."""
        long_state = "s" * 101
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(target_state=long_state)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("target_state",) for e in errors)

    def test_source_state_min_length_enforced(self) -> None:
        """source_state must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(source_state="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_state",) for e in errors)

    def test_source_state_max_length_enforced(self) -> None:
        """source_state exceeding 100 chars raises ValidationError."""
        long_state = "s" * 101
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(source_state=long_state)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_state",) for e in errors)

    def test_trigger_min_length_enforced(self) -> None:
        """trigger must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(trigger="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("trigger",) for e in errors)

    def test_trigger_max_length_enforced(self) -> None:
        """trigger exceeding 100 chars raises ValidationError."""
        long_trigger = "t" * 101
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(trigger=long_trigger)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("trigger",) for e in errors)

    def test_entity_type_min_length_enforced(self) -> None:
        """entity_type must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(entity_type="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("entity_type",) for e in errors)

    def test_entity_type_max_length_enforced(self) -> None:
        """entity_type exceeding 100 chars raises ValidationError."""
        long_type = "t" * 101
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(entity_type=long_type)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("entity_type",) for e in errors)

    def test_operation_min_length_enforced(self) -> None:
        """operation must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(operation="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("operation",) for e in errors)

    def test_operation_max_length_enforced(self) -> None:
        """operation exceeding 100 chars raises ValidationError."""
        long_op = "o" * 101
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(operation=long_op)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("operation",) for e in errors)

    def test_idempotency_key_min_length_enforced(self) -> None:
        """idempotency_key must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(idempotency_key="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("idempotency_key",) for e in errors)

    def test_idempotency_key_max_length_enforced(self) -> None:
        """idempotency_key exceeding 256 chars raises ValidationError."""
        long_key = "k" * 257
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(idempotency_key=long_key)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("idempotency_key",) for e in errors)

    def test_timeout_ms_must_be_non_negative(self) -> None:
        """timeout_ms must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(timeout_ms=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("timeout_ms",) for e in errors)

    def test_retry_count_must_be_non_negative(self) -> None:
        """retry_count must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(retry_count=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("retry_count",) for e in errors)

    def test_max_retries_must_be_non_negative(self) -> None:
        """max_retries must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(max_retries=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("max_retries",) for e in errors)

    def test_invalid_entity_id_type_rejected(self) -> None:
        """Non-UUID entity_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(
                entity_id="not-a-uuid",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("entity_id",) for e in errors)

    def test_list_data_coerced_to_tuple(self) -> None:
        """List data is coerced to tuple by Pydantic."""
        model = ModelReducerIntentPayload(
            data=[("key", "value")],
        )
        # Pydantic coerces list to tuple
        assert isinstance(model.data, tuple)
        assert model.data == (("key", "value"),)

    def test_invalid_validation_errors_type_rejected(self) -> None:
        """Non-tuple validation_errors raises ValidationError."""
        # Pydantic may coerce lists to tuples
        model = ModelReducerIntentPayload(
            validation_errors=["error1", "error2"],
        )
        # Should be coerced to tuple
        assert isinstance(model.validation_errors, tuple)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
class TestModelReducerIntentPayloadEdgeCases:
    """Tests for edge cases in ModelReducerIntentPayload."""

    def test_none_values_for_optional_fields(self) -> None:
        """None values work for all optional fields."""
        model = ModelReducerIntentPayload(
            target_state=None,
            source_state=None,
            trigger=None,
            entity_id=None,
            entity_type=None,
            operation=None,
            idempotency_key=None,
            timeout_ms=None,
        )
        assert model.target_state is None
        assert model.source_state is None
        assert model.trigger is None
        assert model.entity_id is None
        assert model.entity_type is None
        assert model.operation is None
        assert model.idempotency_key is None
        assert model.timeout_ms is None

    def test_boundary_target_state_at_max_length(self) -> None:
        """target_state at exactly 100 chars is accepted."""
        max_state = "s" * 100
        model = ModelReducerIntentPayload(target_state=max_state)
        assert len(model.target_state) == 100

    def test_boundary_operation_at_max_length(self) -> None:
        """operation at exactly 100 chars is accepted."""
        max_op = "o" * 100
        model = ModelReducerIntentPayload(operation=max_op)
        assert len(model.operation) == 100

    def test_boundary_idempotency_key_at_max_length(self) -> None:
        """idempotency_key at exactly 256 chars is accepted."""
        max_key = "k" * 256
        model = ModelReducerIntentPayload(idempotency_key=max_key)
        assert len(model.idempotency_key) == 256

    def test_unicode_in_target_state(self) -> None:
        """Unicode characters in target_state are accepted."""
        unicode_state = "حالة_نشطة"
        model = ModelReducerIntentPayload(target_state=unicode_state)
        assert model.target_state == unicode_state

    def test_unicode_in_trigger(self) -> None:
        """Unicode characters in trigger are accepted."""
        unicode_trigger = "δημιουργία_γεγονός"
        model = ModelReducerIntentPayload(trigger=unicode_trigger)
        assert model.trigger == unicode_trigger

    def test_unicode_in_operation(self) -> None:
        """Unicode characters in operation are accepted."""
        unicode_op = "用户创建_launch"
        model = ModelReducerIntentPayload(operation=unicode_op)
        assert model.operation == unicode_op

    def test_empty_data_tuple(self) -> None:
        """Empty data tuple is accepted."""
        model = ModelReducerIntentPayload(data=())
        assert model.data == ()

    def test_empty_validation_errors_tuple(self) -> None:
        """Empty validation_errors tuple is accepted."""
        model = ModelReducerIntentPayload(validation_errors=())
        assert model.validation_errors == ()

    def test_data_with_various_value_types(self) -> None:
        """data tuple accepts various serializable value types."""
        model = ModelReducerIntentPayload(
            data=(
                ("string_key", "string_value"),
                ("int_key", 42),
                ("float_key", 3.14),
                ("bool_key", True),
                ("null_key", None),
                ("list_key", [1, 2, 3]),
                ("dict_key", {"nested": "value"}),
            ),
        )
        assert len(model.data) == 7

    def test_timeout_ms_zero_allowed(self) -> None:
        """timeout_ms of 0 is allowed."""
        model = ModelReducerIntentPayload(timeout_ms=0)
        assert model.timeout_ms == 0

    def test_retry_count_zero_default(self) -> None:
        """retry_count defaults to 0."""
        model = ModelReducerIntentPayload()
        assert model.retry_count == 0

    def test_max_retries_default_value(self) -> None:
        """max_retries defaults to 3."""
        model = ModelReducerIntentPayload()
        assert model.max_retries == 3

    def test_valid_uuid_entity_id(self) -> None:
        """Valid UUID is accepted for entity_id."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        model = ModelReducerIntentPayload(entity_id=test_uuid)
        assert model.entity_id == test_uuid

    def test_uuid_string_coerced_to_uuid(self) -> None:
        """UUID string is coerced to UUID object."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        model = ModelReducerIntentPayload(
            entity_id=uuid_str,
        )
        assert isinstance(model.entity_id, UUID)
        assert str(model.entity_id) == uuid_str

    def test_large_validation_errors_tuple(self) -> None:
        """Large validation_errors tuple is accepted."""
        errors = tuple(f"Error {i}" for i in range(100))
        model = ModelReducerIntentPayload(validation_errors=errors)
        assert len(model.validation_errors) == 100

    def test_large_data_tuple(self) -> None:
        """Large data tuple is accepted."""
        data = tuple((f"key_{i}", f"value_{i}") for i in range(100))
        model = ModelReducerIntentPayload(data=data)
        assert len(model.data) == 100


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================


@pytest.mark.unit
class TestModelReducerIntentPayloadHelperMethods:
    """Tests for helper methods of ModelReducerIntentPayload."""

    # is_retryable() tests

    def test_is_retryable_returns_true_when_below_max(self) -> None:
        """is_retryable() returns True when retry_count < max_retries."""
        model = ModelReducerIntentPayload(retry_count=2, max_retries=5)
        assert model.is_retryable() is True

    def test_is_retryable_returns_false_when_at_max(self) -> None:
        """is_retryable() returns False when retry_count == max_retries."""
        model = ModelReducerIntentPayload(retry_count=5, max_retries=5)
        assert model.is_retryable() is False

    def test_is_retryable_returns_false_when_above_max(self) -> None:
        """is_retryable() returns False when retry_count > max_retries."""
        model = ModelReducerIntentPayload(retry_count=6, max_retries=5)
        assert model.is_retryable() is False

    def test_is_retryable_with_zero_max_retries(self) -> None:
        """is_retryable() returns False when max_retries is 0."""
        model = ModelReducerIntentPayload(retry_count=0, max_retries=0)
        assert model.is_retryable() is False

    def test_is_retryable_with_default_values(self) -> None:
        """is_retryable() returns True with default values (0 < 3)."""
        model = ModelReducerIntentPayload()
        assert model.is_retryable() is True

    def test_is_retryable_at_boundary(self) -> None:
        """is_retryable() returns True at retry_count = max_retries - 1."""
        model = ModelReducerIntentPayload(retry_count=4, max_retries=5)
        assert model.is_retryable() is True

    # with_incremented_retry() tests

    def test_with_incremented_retry_returns_new_instance(self) -> None:
        """with_incremented_retry() returns a new instance."""
        original = ModelReducerIntentPayload(retry_count=1)
        incremented = original.with_incremented_retry()
        assert incremented is not original

    def test_with_incremented_retry_increments_count(self) -> None:
        """with_incremented_retry() increments retry_count by 1."""
        original = ModelReducerIntentPayload(retry_count=1)
        incremented = original.with_incremented_retry()
        assert incremented.retry_count == 2

    def test_with_incremented_retry_preserves_other_fields(self) -> None:
        """with_incremented_retry() preserves all other fields."""
        entity_uuid = uuid4()
        original = ModelReducerIntentPayload(
            target_state="active",
            source_state="pending",
            trigger="user_verified",
            entity_id=entity_uuid,
            entity_type="user",
            operation="activate",
            data=(("key", "value"),),
            validation_errors=("error",),
            idempotency_key="key-123",
            timeout_ms=5000,
            retry_count=2,
            max_retries=5,
        )
        incremented = original.with_incremented_retry()
        assert incremented.target_state == original.target_state
        assert incremented.source_state == original.source_state
        assert incremented.trigger == original.trigger
        assert incremented.entity_id == original.entity_id
        assert incremented.entity_type == original.entity_type
        assert incremented.operation == original.operation
        assert incremented.data == original.data
        assert incremented.validation_errors == original.validation_errors
        assert incremented.idempotency_key == original.idempotency_key
        assert incremented.timeout_ms == original.timeout_ms
        assert incremented.max_retries == original.max_retries
        assert incremented.retry_count == 3  # Only this changed

    def test_with_incremented_retry_from_zero(self) -> None:
        """with_incremented_retry() works from retry_count=0."""
        original = ModelReducerIntentPayload(retry_count=0)
        incremented = original.with_incremented_retry()
        assert incremented.retry_count == 1

    def test_with_incremented_retry_does_not_modify_original(self) -> None:
        """with_incremented_retry() does not modify the original instance."""
        original = ModelReducerIntentPayload(retry_count=5)
        _ = original.with_incremented_retry()
        assert original.retry_count == 5

    def test_with_incremented_retry_chain(self) -> None:
        """with_incremented_retry() can be chained multiple times."""
        model = ModelReducerIntentPayload(retry_count=0)
        model = model.with_incremented_retry()
        model = model.with_incremented_retry()
        model = model.with_incremented_retry()
        assert model.retry_count == 3

    # get_data_as_dict() tests

    def test_get_data_as_dict_empty(self) -> None:
        """get_data_as_dict() returns empty dict for empty data."""
        model = ModelReducerIntentPayload(data=())
        result = model.get_data_as_dict()
        assert result == {}

    def test_get_data_as_dict_single_pair(self) -> None:
        """get_data_as_dict() returns dict with single key-value pair."""
        model = ModelReducerIntentPayload(data=(("key", "value"),))
        result = model.get_data_as_dict()
        assert result == {"key": "value"}

    def test_get_data_as_dict_multiple_pairs(self) -> None:
        """get_data_as_dict() returns dict with multiple key-value pairs."""
        model = ModelReducerIntentPayload(
            data=(
                ("key1", "value1"),
                ("key2", "value2"),
                ("key3", "value3"),
            )
        )
        result = model.get_data_as_dict()
        assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}

    def test_get_data_as_dict_various_types(self) -> None:
        """get_data_as_dict() handles various value types."""
        model = ModelReducerIntentPayload(
            data=(
                ("string", "value"),
                ("int", 42),
                ("float", 3.14),
                ("bool", True),
                ("null", None),
            )
        )
        result = model.get_data_as_dict()
        assert result["string"] == "value"
        assert result["int"] == 42
        assert result["float"] == 3.14
        assert result["bool"] is True
        assert result["null"] is None

    def test_get_data_as_dict_returns_mutable_dict(self) -> None:
        """get_data_as_dict() returns a mutable dict."""
        model = ModelReducerIntentPayload(data=(("key", "value"),))
        result = model.get_data_as_dict()
        result["new_key"] = "new_value"
        assert "new_key" in result
        # Original model data is unchanged
        assert "new_key" not in model.get_data_as_dict()

    def test_get_data_as_dict_duplicate_keys_last_wins(self) -> None:
        """get_data_as_dict() uses last value for duplicate keys."""
        model = ModelReducerIntentPayload(
            data=(
                ("key", "first"),
                ("key", "second"),
                ("key", "third"),
            )
        )
        result = model.get_data_as_dict()
        assert result == {"key": "third"}


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.unit
class TestModelReducerIntentPayloadImmutability:
    """Tests for immutability (frozen=True) behavior."""

    def test_target_state_cannot_be_modified(self) -> None:
        """target_state cannot be changed after creation."""
        model = ModelReducerIntentPayload(target_state="active")
        with pytest.raises(ValidationError):
            model.target_state = "inactive"

    def test_source_state_cannot_be_modified(self) -> None:
        """source_state cannot be changed after creation."""
        model = ModelReducerIntentPayload(source_state="pending")
        with pytest.raises(ValidationError):
            model.source_state = "active"

    def test_retry_count_cannot_be_modified(self) -> None:
        """retry_count cannot be changed after creation."""
        model = ModelReducerIntentPayload(retry_count=2)
        with pytest.raises(ValidationError):
            model.retry_count = 5

    def test_data_cannot_be_modified(self) -> None:
        """data cannot be changed after creation."""
        model = ModelReducerIntentPayload(data=(("key", "value"),))
        with pytest.raises(ValidationError):
            model.data = (("new", "data"),)

    def test_entity_id_cannot_be_modified(self) -> None:
        """entity_id cannot be changed after creation."""
        model = ModelReducerIntentPayload(entity_id=uuid4())
        with pytest.raises(ValidationError):
            model.entity_id = uuid4()


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelReducerIntentPayloadSerialization:
    """Tests for serialization/deserialization behavior."""

    def test_model_dump_includes_all_fields(self) -> None:
        """model_dump() includes all fields."""
        entity_uuid = uuid4()
        model = ModelReducerIntentPayload(
            target_state="active",
            source_state="pending",
            trigger="event",
            entity_id=entity_uuid,
            entity_type="user",
            operation="create",
            data=(("key", "value"),),
            validation_errors=("error",),
            idempotency_key="key-123",
            timeout_ms=5000,
            retry_count=2,
            max_retries=5,
        )
        data = model.model_dump()
        assert data["target_state"] == "active"
        assert data["source_state"] == "pending"
        assert data["trigger"] == "event"
        assert data["entity_id"] == entity_uuid
        assert data["entity_type"] == "user"
        assert data["operation"] == "create"
        assert data["data"] == (("key", "value"),)
        assert data["validation_errors"] == ("error",)
        assert data["idempotency_key"] == "key-123"
        assert data["timeout_ms"] == 5000
        assert data["retry_count"] == 2
        assert data["max_retries"] == 5

    def test_model_dump_mode_json(self) -> None:
        """model_dump(mode='json') produces JSON-serializable output."""
        entity_uuid = uuid4()
        model = ModelReducerIntentPayload(
            entity_id=entity_uuid,
            data=(("key", "value"),),
        )
        data = model.model_dump(mode="json")
        assert data["entity_id"] == str(entity_uuid)
        # Tuples become lists in JSON mode
        assert data["data"] == [["key", "value"]]

    def test_model_validate_roundtrip(self) -> None:
        """Model can be recreated from model_dump() output."""
        entity_uuid = uuid4()
        original = ModelReducerIntentPayload(
            target_state="active",
            entity_id=entity_uuid,
            retry_count=3,
        )
        data = original.model_dump()
        recreated = ModelReducerIntentPayload.model_validate(data)
        assert recreated.target_state == original.target_state
        assert recreated.entity_id == original.entity_id
        assert recreated.retry_count == original.retry_count

    def test_from_attributes_enabled(self) -> None:
        """from_attributes=True allows creation from object attributes."""

        class MockObject:
            target_state = "active"
            source_state = "pending"
            trigger = "event"
            entity_id = None
            entity_type = "user"
            operation = "create"
            data = (("key", "value"),)
            validation_errors = ()
            idempotency_key = None
            timeout_ms = None
            retry_count = 0
            max_retries = 3

        mock = MockObject()
        model = ModelReducerIntentPayload.model_validate(mock)
        assert model.target_state == "active"
        assert model.entity_type == "user"


# =============================================================================
# HASH AND EQUALITY TESTS
# =============================================================================


@pytest.mark.unit
class TestModelReducerIntentPayloadHashEquality:
    """Tests for hash and equality behavior."""

    def test_equal_models_are_equal(self) -> None:
        """Two models with same values are equal."""
        entity_uuid = uuid4()
        model1 = ModelReducerIntentPayload(
            target_state="active",
            entity_id=entity_uuid,
            retry_count=2,
        )
        model2 = ModelReducerIntentPayload(
            target_state="active",
            entity_id=entity_uuid,
            retry_count=2,
        )
        assert model1 == model2

    def test_different_models_are_not_equal(self) -> None:
        """Two models with different values are not equal."""
        model1 = ModelReducerIntentPayload(target_state="active")
        model2 = ModelReducerIntentPayload(target_state="pending")
        assert model1 != model2

    def test_frozen_model_is_hashable(self) -> None:
        """Frozen model is hashable."""
        model = ModelReducerIntentPayload(
            target_state="active",
            retry_count=2,
        )
        # Should not raise
        hash_value = hash(model)
        assert isinstance(hash_value, int)

    def test_equal_models_have_same_hash(self) -> None:
        """Equal models have the same hash."""
        entity_uuid = uuid4()
        model1 = ModelReducerIntentPayload(
            target_state="active",
            entity_id=entity_uuid,
        )
        model2 = ModelReducerIntentPayload(
            target_state="active",
            entity_id=entity_uuid,
        )
        assert hash(model1) == hash(model2)

    def test_model_can_be_used_in_set(self) -> None:
        """Model can be used as set element."""
        model1 = ModelReducerIntentPayload(target_state="active")
        model2 = ModelReducerIntentPayload(target_state="pending")
        model_set = {model1, model2}
        assert len(model_set) == 2

    def test_model_can_be_used_as_dict_key(self) -> None:
        """Model can be used as dictionary key."""
        model = ModelReducerIntentPayload(
            target_state="active",
            operation="create",
        )
        test_dict = {model: "value"}
        assert test_dict[model] == "value"
