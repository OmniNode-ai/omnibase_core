# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

"""
Tests for NodeReducer model hardening (frozen + extra=forbid).

Verifies that ModelReducerInput, ModelReducerOutput, and ModelIntent
are properly hardened with frozen=True and extra="forbid".

These tests ensure:
- Models are immutable after creation (frozen=True)
- Extra fields are rejected at instantiation (extra="forbid")
- Field constraints are properly enforced
"""

from uuid import uuid4

from pydantic import ValidationError

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelReducerInputHardening:
    """Tests for ModelReducerInput frozen and extra=forbid."""

    def test_is_frozen(self) -> None:
        """Verify ModelReducerInput is immutable after creation."""
        input_model = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )
        with pytest.raises(ValidationError):
            input_model.data = [4, 5, 6]  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput(
                data=[1, 2, 3],
                reduction_type=EnumReductionType.FOLD,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_batch_size_bounds(self) -> None:
        """Verify batch_size constraints (gt=0, le=10000)."""
        # Valid batch size
        valid = ModelReducerInput(
            data=[1],
            reduction_type=EnumReductionType.FOLD,
            batch_size=5000,
        )
        assert valid.batch_size == 5000

        # Too small (must be > 0)
        with pytest.raises(ValidationError):
            ModelReducerInput(
                data=[1],
                reduction_type=EnumReductionType.FOLD,
                batch_size=0,
            )

        # Too large (must be <= 10000)
        with pytest.raises(ValidationError):
            ModelReducerInput(
                data=[1],
                reduction_type=EnumReductionType.FOLD,
                batch_size=10001,
            )

    def test_window_size_ms_bounds(self) -> None:
        """Verify window_size_ms constraints (ge=1000, le=60000)."""
        # Valid window size
        valid = ModelReducerInput(
            data=[1],
            reduction_type=EnumReductionType.FOLD,
            window_size_ms=5000,
        )
        assert valid.window_size_ms == 5000

        # Too small (must be >= 1000)
        with pytest.raises(ValidationError):
            ModelReducerInput(
                data=[1],
                reduction_type=EnumReductionType.FOLD,
                window_size_ms=999,
            )

        # Too large (must be <= 60000)
        with pytest.raises(ValidationError):
            ModelReducerInput(
                data=[1],
                reduction_type=EnumReductionType.FOLD,
                window_size_ms=60001,
            )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelReducerInput.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelReducerInput.model_config
        assert config.get("extra") == "forbid"


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelReducerOutputHardening:
    """Tests for ModelReducerOutput frozen and extra=forbid."""

    def test_is_frozen(self) -> None:
        """Verify ModelReducerOutput is immutable after creation."""
        output_model = ModelReducerOutput(
            result={"sum": 10},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=1.5,
            items_processed=3,
        )
        with pytest.raises(ValidationError):
            output_model.result = {"sum": 20}  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput(
                result={"sum": 10},
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=1.5,
                items_processed=3,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelReducerOutput.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelReducerOutput.model_config
        assert config.get("extra") == "forbid"


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelIntentHardening:
    """Tests for ModelIntent frozen and extra=forbid."""

    def test_is_frozen(self) -> None:
        """Verify ModelIntent is immutable after creation."""
        intent = ModelIntent(
            intent_type="emit_event",
            target="user.created",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        with pytest.raises(ValidationError):
            intent.intent_type = "notify"  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="emit_event",
                target="user.created",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_priority_bounds(self) -> None:
        """Verify priority constraints (ge=1, le=10)."""
        # Valid priority
        valid = ModelIntent(
            intent_type="emit_event",
            target="user.created",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            priority=5,
        )
        assert valid.priority == 5

        # Too small (must be >= 1)
        with pytest.raises(ValidationError):
            ModelIntent(
                intent_type="emit_event",
                target="user.created",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                priority=0,
            )

        # Too large (must be <= 10)
        with pytest.raises(ValidationError):
            ModelIntent(
                intent_type="emit_event",
                target="user.created",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                priority=11,
            )

    def test_intent_type_length_bounds(self) -> None:
        """Verify intent_type length constraints (min=1, max=100)."""
        # Valid intent_type
        valid = ModelIntent(
            intent_type="emit_event",
            target="user.created",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert valid.intent_type == "emit_event"

        # Too short (must be >= 1)
        with pytest.raises(ValidationError):
            ModelIntent(
                intent_type="",
                target="user.created",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )

        # Too long (must be <= 100)
        with pytest.raises(ValidationError):
            ModelIntent(
                intent_type="x" * 101,
                target="user.created",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )

    def test_target_length_bounds(self) -> None:
        """Verify target length constraints (min=1, max=200)."""
        # Valid target
        valid = ModelIntent(
            intent_type="emit_event",
            target="user.created",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert valid.target == "user.created"

        # Too short (must be >= 1)
        with pytest.raises(ValidationError):
            ModelIntent(
                intent_type="emit_event",
                target="",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )

        # Too long (must be <= 200)
        with pytest.raises(ValidationError):
            ModelIntent(
                intent_type="emit_event",
                target="x" * 201,
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )

    def test_epoch_bounds(self) -> None:
        """Verify epoch constraints (ge=0 when provided)."""
        # Valid epoch
        valid = ModelIntent(
            intent_type="emit_event",
            target="user.created",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            epoch=0,
        )
        assert valid.epoch == 0

        # Negative epoch should fail
        with pytest.raises(ValidationError):
            ModelIntent(
                intent_type="emit_event",
                target="user.created",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                epoch=-1,
            )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelIntent.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelIntent.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelIntent(
            intent_type="emit_event",
            target="user.created",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            priority=5,
        )

        # Create a modified copy (this is the correct pattern for frozen models)
        modified = original.model_copy(update={"priority": 8})

        assert original.priority == 5  # Original unchanged
        assert modified.priority == 8  # Copy has new value
        assert original.intent_type == modified.intent_type  # Other fields preserved
