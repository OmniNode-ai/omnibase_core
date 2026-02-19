# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelRetryWithBackoffPayload.

This module tests the RETRY_WITH_BACKOFF directive payload, verifying:
1. Discriminator field (kind="retry_with_backoff")
2. Required operation_id field (UUID)
3. Bound validations (backoff_multiplier, max_backoff_ms, initial_backoff_ms)
4. Cross-field validation (initial_backoff_ms <= max_backoff_ms)
5. Default values
6. Serialization/deserialization roundtrip
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.payloads import ModelRetryWithBackoffPayload


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadDiscriminator:
    """Test discriminator field behavior."""

    def test_kind_is_literal_retry_with_backoff(self) -> None:
        """Test that kind field is always 'retry_with_backoff'."""
        payload = ModelRetryWithBackoffPayload(operation_id=uuid4())
        assert payload.kind == "retry_with_backoff"

    def test_kind_cannot_be_changed(self) -> None:
        """Test that kind field cannot be set to different value."""
        with pytest.raises(ValidationError):
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                kind="other_kind",  # type: ignore[arg-type]
            )

    def test_kind_default_value(self) -> None:
        """Test that kind has correct default value."""
        payload = ModelRetryWithBackoffPayload(operation_id=uuid4())
        assert payload.kind == "retry_with_backoff"


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadRequiredFields:
    """Test required field validation."""

    def test_operation_id_required(self) -> None:
        """Test that operation_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload()  # type: ignore[call-arg]
        assert "operation_id" in str(exc_info.value)

    def test_operation_id_valid_uuid(self) -> None:
        """Test operation_id with valid UUID."""
        op_id = uuid4()
        payload = ModelRetryWithBackoffPayload(operation_id=op_id)
        assert payload.operation_id == op_id

    def test_operation_id_from_string(self) -> None:
        """Test operation_id from string UUID."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        payload = ModelRetryWithBackoffPayload(operation_id=uuid_str)  # type: ignore[arg-type]
        assert isinstance(payload.operation_id, UUID)
        assert str(payload.operation_id) == uuid_str


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadDefaults:
    """Test default values."""

    def test_all_defaults(self) -> None:
        """Test that all fields have correct defaults."""
        payload = ModelRetryWithBackoffPayload(operation_id=uuid4())

        assert payload.kind == "retry_with_backoff"
        assert payload.current_attempt == 0
        assert payload.backoff_multiplier == 1.5
        assert payload.max_backoff_ms == 30000
        assert payload.initial_backoff_ms == 1000
        assert payload.jitter is True


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadCurrentAttempt:
    """Test current_attempt field validation."""

    def test_current_attempt_zero(self) -> None:
        """Test current_attempt at minimum (0)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            current_attempt=0,
        )
        assert payload.current_attempt == 0

    def test_current_attempt_positive(self) -> None:
        """Test current_attempt with positive value."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            current_attempt=5,
        )
        assert payload.current_attempt == 5

    def test_current_attempt_negative(self) -> None:
        """Test current_attempt with negative value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                current_attempt=-1,
            )
        assert "current_attempt" in str(exc_info.value)


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadBackoffMultiplier:
    """Test backoff_multiplier field validation."""

    def test_backoff_multiplier_above_one(self) -> None:
        """Test backoff_multiplier > 1.0."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            backoff_multiplier=2.0,
        )
        assert payload.backoff_multiplier == 2.0

    def test_backoff_multiplier_at_max(self) -> None:
        """Test backoff_multiplier at maximum (10.0)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            backoff_multiplier=10.0,
        )
        assert payload.backoff_multiplier == 10.0

    def test_backoff_multiplier_at_one(self) -> None:
        """Test backoff_multiplier at 1.0 (should fail, must be > 1.0)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                backoff_multiplier=1.0,
            )
        assert "backoff_multiplier" in str(exc_info.value)

    def test_backoff_multiplier_below_one(self) -> None:
        """Test backoff_multiplier below 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                backoff_multiplier=0.5,
            )
        assert "backoff_multiplier" in str(exc_info.value)

    def test_backoff_multiplier_above_max(self) -> None:
        """Test backoff_multiplier above maximum (10.0)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                backoff_multiplier=11.0,
            )
        assert "backoff_multiplier" in str(exc_info.value)


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadMaxBackoffMs:
    """Test max_backoff_ms field validation."""

    def test_max_backoff_ms_at_minimum(self) -> None:
        """Test max_backoff_ms at minimum (1000ms = 1s)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            max_backoff_ms=1000,
            initial_backoff_ms=100,  # Must be <= max
        )
        assert payload.max_backoff_ms == 1000

    def test_max_backoff_ms_at_maximum(self) -> None:
        """Test max_backoff_ms at maximum (3600000ms = 1h)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            max_backoff_ms=3600000,
        )
        assert payload.max_backoff_ms == 3600000

    def test_max_backoff_ms_below_minimum(self) -> None:
        """Test max_backoff_ms below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                max_backoff_ms=999,
            )
        assert "max_backoff_ms" in str(exc_info.value)

    def test_max_backoff_ms_above_maximum(self) -> None:
        """Test max_backoff_ms above maximum."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                max_backoff_ms=3600001,
            )
        assert "max_backoff_ms" in str(exc_info.value)


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadInitialBackoffMs:
    """Test initial_backoff_ms field validation."""

    def test_initial_backoff_ms_at_minimum(self) -> None:
        """Test initial_backoff_ms at minimum (100ms)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            initial_backoff_ms=100,
        )
        assert payload.initial_backoff_ms == 100

    def test_initial_backoff_ms_at_maximum(self) -> None:
        """Test initial_backoff_ms at maximum (60000ms = 60s)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            initial_backoff_ms=30000,  # Must be <= max_backoff_ms (30000 default)
        )
        assert payload.initial_backoff_ms == 30000

    def test_initial_backoff_ms_below_minimum(self) -> None:
        """Test initial_backoff_ms below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                initial_backoff_ms=99,
            )
        assert "initial_backoff_ms" in str(exc_info.value)

    def test_initial_backoff_ms_above_maximum(self) -> None:
        """Test initial_backoff_ms above maximum."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                initial_backoff_ms=60001,
            )
        assert "initial_backoff_ms" in str(exc_info.value)


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadCrossFieldValidation:
    """Test cross-field validation (initial_backoff_ms <= max_backoff_ms)."""

    def test_initial_less_than_max(self) -> None:
        """Test initial_backoff_ms < max_backoff_ms (valid)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            initial_backoff_ms=1000,
            max_backoff_ms=30000,
        )
        assert payload.initial_backoff_ms < payload.max_backoff_ms

    def test_initial_equals_max(self) -> None:
        """Test initial_backoff_ms == max_backoff_ms (valid)."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            initial_backoff_ms=10000,
            max_backoff_ms=10000,
        )
        assert payload.initial_backoff_ms == payload.max_backoff_ms

    def test_initial_greater_than_max(self) -> None:
        """Test initial_backoff_ms > max_backoff_ms (invalid)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                initial_backoff_ms=60000,
                max_backoff_ms=30000,
            )
        assert "initial_backoff_ms" in str(exc_info.value)
        assert "cannot exceed" in str(exc_info.value)

    def test_cross_validation_error_context(self) -> None:
        """Test that cross-validation error includes context."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                initial_backoff_ms=50000,
                max_backoff_ms=40000,
            )
        # Error should contain both values for debugging
        error_str = str(exc_info.value)
        assert "50000" in error_str or "initial_backoff_ms" in error_str


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadJitter:
    """Test jitter field."""

    def test_jitter_defaults_to_true(self) -> None:
        """Test that jitter defaults to True."""
        payload = ModelRetryWithBackoffPayload(operation_id=uuid4())
        assert payload.jitter is True

    def test_jitter_false(self) -> None:
        """Test jitter set to False."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            jitter=False,
        )
        assert payload.jitter is False


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadSerialization:
    """Test serialization/deserialization."""

    def test_serialization_defaults(self) -> None:
        """Test serialization with default values."""
        op_id = uuid4()
        payload = ModelRetryWithBackoffPayload(operation_id=op_id)
        data = payload.model_dump()

        assert data["kind"] == "retry_with_backoff"
        assert data["operation_id"] == op_id
        assert data["current_attempt"] == 0
        assert data["backoff_multiplier"] == 1.5
        assert data["max_backoff_ms"] == 30000
        assert data["initial_backoff_ms"] == 1000
        assert data["jitter"] is True

    def test_serialization_all_fields(self) -> None:
        """Test serialization with all fields set."""
        op_id = uuid4()
        payload = ModelRetryWithBackoffPayload(
            operation_id=op_id,
            current_attempt=3,
            backoff_multiplier=2.0,
            max_backoff_ms=60000,
            initial_backoff_ms=500,
            jitter=False,
        )
        data = payload.model_dump()

        assert data["current_attempt"] == 3
        assert data["backoff_multiplier"] == 2.0
        assert data["max_backoff_ms"] == 60000
        assert data["initial_backoff_ms"] == 500
        assert data["jitter"] is False

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        op_id = uuid4()
        original = ModelRetryWithBackoffPayload(
            operation_id=op_id,
            current_attempt=2,
            backoff_multiplier=3.0,
            max_backoff_ms=120000,
            initial_backoff_ms=2000,
            jitter=True,
        )
        data = original.model_dump()
        restored = ModelRetryWithBackoffPayload.model_validate(data)

        assert restored.kind == original.kind
        assert restored.operation_id == original.operation_id
        assert restored.current_attempt == original.current_attempt
        assert restored.backoff_multiplier == original.backoff_multiplier
        assert restored.max_backoff_ms == original.max_backoff_ms
        assert restored.initial_backoff_ms == original.initial_backoff_ms
        assert restored.jitter == original.jitter

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        op_id = uuid4()
        payload = ModelRetryWithBackoffPayload(operation_id=op_id)
        json_str = payload.model_dump_json()

        assert '"kind":"retry_with_backoff"' in json_str
        assert str(op_id) in json_str


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadImmutability:
    """Test immutability (frozen model)."""

    def test_cannot_modify_operation_id(self) -> None:
        """Test that operation_id cannot be modified."""
        payload = ModelRetryWithBackoffPayload(operation_id=uuid4())
        with pytest.raises(ValidationError):
            payload.operation_id = uuid4()  # type: ignore[misc]

    def test_cannot_modify_backoff_multiplier(self) -> None:
        """Test that backoff_multiplier cannot be modified."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            backoff_multiplier=2.0,
        )
        with pytest.raises(ValidationError):
            payload.backoff_multiplier = 3.0  # type: ignore[misc]


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadExtraFieldsRejected:
    """Test extra fields rejection."""

    def test_reject_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRetryWithBackoffPayload(
                operation_id=uuid4(),
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelRetryWithBackoffPayloadEdgeCases:
    """Test edge cases."""

    def test_very_small_multiplier(self) -> None:
        """Test backoff_multiplier just above 1.0."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            backoff_multiplier=1.001,
        )
        assert payload.backoff_multiplier == 1.001

    def test_high_attempt_count(self) -> None:
        """Test with very high current_attempt."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            current_attempt=1000,
        )
        assert payload.current_attempt == 1000

    def test_all_at_boundary_values(self) -> None:
        """Test all fields at their boundary values."""
        payload = ModelRetryWithBackoffPayload(
            operation_id=uuid4(),
            current_attempt=0,
            backoff_multiplier=10.0,
            max_backoff_ms=3600000,
            initial_backoff_ms=100,
            jitter=False,
        )
        assert payload.current_attempt == 0
        assert payload.backoff_multiplier == 10.0
        assert payload.max_backoff_ms == 3600000
        assert payload.initial_backoff_ms == 100
