# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for FSM payload models.

This module tests all FSM-related payloads:
- ModelPayloadFSMStateAction: State entry/exit action intents
- ModelPayloadFSMTransitionAction: Transition action intents
- ModelPayloadFSMCompleted: FSM completion notification intents

Verifying:
1. Field validation
2. Discriminator values
3. Serialization/deserialization
4. Immutability
5. Default values
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import (
    ModelPayloadFSMCompleted,
    ModelPayloadFSMStateAction,
    ModelPayloadFSMTransitionAction,
)

# ==============================================================================
# ModelPayloadFSMStateAction Tests
# ==============================================================================


@pytest.mark.unit
class TestModelPayloadFSMStateActionInstantiation:
    """Test ModelPayloadFSMStateAction instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = ModelPayloadFSMStateAction(
            state_name="authenticated",
            action_type="on_enter",
            action_name="log_session",
        )
        assert payload.state_name == "authenticated"
        assert payload.action_type == "on_enter"
        assert payload.action_name == "log_session"
        assert payload.intent_type == "fsm_state_action"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        fsm_id = uuid4()
        payload = ModelPayloadFSMStateAction(
            state_name="authenticated",
            action_type="on_enter",
            action_name="log_session",
            parameters={"user_id": "123", "ip": "192.168.1.1"},
            fsm_id=fsm_id,
        )
        assert payload.state_name == "authenticated"
        assert payload.action_type == "on_enter"
        assert payload.action_name == "log_session"
        assert payload.parameters == {"user_id": "123", "ip": "192.168.1.1"}
        assert payload.fsm_id == fsm_id


@pytest.mark.unit
class TestModelPayloadFSMStateActionDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'fsm_state_action'."""
        payload = ModelPayloadFSMStateAction(
            state_name="state",
            action_type="on_enter",
            action_name="action",
        )
        assert payload.intent_type == "fsm_state_action"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadFSMStateAction(
            state_name="state",
            action_type="on_enter",
            action_name="action",
        )
        data = payload.model_dump()
        assert data["intent_type"] == "fsm_state_action"


@pytest.mark.unit
class TestModelPayloadFSMStateActionValidation:
    """Test field validation."""

    def test_state_name_required(self) -> None:
        """Test that state_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMStateAction(action_type="on_enter", action_name="action")  # type: ignore[call-arg]
        assert "state_name" in str(exc_info.value)

    def test_action_type_required(self) -> None:
        """Test that action_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMStateAction(state_name="state", action_name="action")  # type: ignore[call-arg]
        assert "action_type" in str(exc_info.value)

    def test_action_name_required(self) -> None:
        """Test that action_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMStateAction(state_name="state", action_type="on_enter")  # type: ignore[call-arg]
        assert "action_name" in str(exc_info.value)

    def test_valid_action_types(self) -> None:
        """Test valid action_type values."""
        for action_type in ["on_enter", "on_exit"]:
            payload = ModelPayloadFSMStateAction(
                state_name="state",
                action_type=action_type,  # type: ignore[arg-type]
                action_name="action",
            )
            assert payload.action_type == action_type

    def test_invalid_action_type_rejected(self) -> None:
        """Test that invalid action_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMStateAction(
                state_name="state",
                action_type="on_transition",  # type: ignore[arg-type]
                action_name="action",
            )
        assert "action_type" in str(exc_info.value)

    def test_state_name_min_length(self) -> None:
        """Test state_name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMStateAction(
                state_name="",
                action_type="on_enter",
                action_name="action",
            )
        assert "state_name" in str(exc_info.value)

    def test_action_name_min_length(self) -> None:
        """Test action_name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMStateAction(
                state_name="state",
                action_type="on_enter",
                action_name="",
            )
        assert "action_name" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadFSMStateActionDefaultValues:
    """Test default values."""

    def test_default_parameters(self) -> None:
        """Test default parameters is empty dict."""
        payload = ModelPayloadFSMStateAction(
            state_name="state",
            action_type="on_enter",
            action_name="action",
        )
        assert payload.parameters == {}

    def test_default_fsm_id(self) -> None:
        """Test default fsm_id is None."""
        payload = ModelPayloadFSMStateAction(
            state_name="state",
            action_type="on_enter",
            action_name="action",
        )
        assert payload.fsm_id is None


@pytest.mark.unit
class TestModelPayloadFSMStateActionImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_state_name(self) -> None:
        """Test that state_name cannot be modified after creation."""
        payload = ModelPayloadFSMStateAction(
            state_name="state",
            action_type="on_enter",
            action_name="action",
        )
        with pytest.raises(ValidationError):
            payload.state_name = "new_state"  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadFSMStateActionSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        fsm_id = uuid4()
        original = ModelPayloadFSMStateAction(
            state_name="authenticated",
            action_type="on_enter",
            action_name="log_session",
            parameters={"user_id": "123"},
            fsm_id=fsm_id,
        )
        data = original.model_dump()
        restored = ModelPayloadFSMStateAction.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadFSMStateAction(
            state_name="state",
            action_type="on_enter",
            action_name="action",
        )
        json_str = original.model_dump_json()
        restored = ModelPayloadFSMStateAction.model_validate_json(json_str)
        assert restored == original


# ==============================================================================
# ModelPayloadFSMTransitionAction Tests
# ==============================================================================


@pytest.mark.unit
class TestModelPayloadFSMTransitionActionInstantiation:
    """Test ModelPayloadFSMTransitionAction instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = ModelPayloadFSMTransitionAction(
            from_state="cart",
            to_state="checkout",
            trigger="proceed_to_checkout",
            action_name="calculate_totals",
        )
        assert payload.from_state == "cart"
        assert payload.to_state == "checkout"
        assert payload.trigger == "proceed_to_checkout"
        assert payload.action_name == "calculate_totals"
        assert payload.intent_type == "fsm_transition_action"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        fsm_id = uuid4()
        payload = ModelPayloadFSMTransitionAction(
            from_state="cart",
            to_state="checkout",
            trigger="proceed_to_checkout",
            action_name="calculate_totals",
            parameters={"apply_discount": True},
            fsm_id=fsm_id,
        )
        assert payload.from_state == "cart"
        assert payload.to_state == "checkout"
        assert payload.trigger == "proceed_to_checkout"
        assert payload.action_name == "calculate_totals"
        assert payload.parameters == {"apply_discount": True}
        assert payload.fsm_id == fsm_id


@pytest.mark.unit
class TestModelPayloadFSMTransitionActionDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'fsm_transition_action'."""
        payload = ModelPayloadFSMTransitionAction(
            from_state="a",
            to_state="b",
            trigger="go",
            action_name="action",
        )
        assert payload.intent_type == "fsm_transition_action"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadFSMTransitionAction(
            from_state="a",
            to_state="b",
            trigger="go",
            action_name="action",
        )
        data = payload.model_dump()
        assert data["intent_type"] == "fsm_transition_action"


@pytest.mark.unit
class TestModelPayloadFSMTransitionActionValidation:
    """Test field validation."""

    def test_from_state_required(self) -> None:
        """Test that from_state is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMTransitionAction(
                to_state="b",
                trigger="go",
                action_name="action",
            )  # type: ignore[call-arg]
        assert "from_state" in str(exc_info.value)

    def test_to_state_required(self) -> None:
        """Test that to_state is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMTransitionAction(
                from_state="a",
                trigger="go",
                action_name="action",
            )  # type: ignore[call-arg]
        assert "to_state" in str(exc_info.value)

    def test_trigger_required(self) -> None:
        """Test that trigger is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMTransitionAction(
                from_state="a",
                to_state="b",
                action_name="action",
            )  # type: ignore[call-arg]
        assert "trigger" in str(exc_info.value)

    def test_action_name_required(self) -> None:
        """Test that action_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMTransitionAction(
                from_state="a",
                to_state="b",
                trigger="go",
            )  # type: ignore[call-arg]
        assert "action_name" in str(exc_info.value)

    def test_from_state_min_length(self) -> None:
        """Test from_state minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMTransitionAction(
                from_state="",
                to_state="b",
                trigger="go",
                action_name="action",
            )
        assert "from_state" in str(exc_info.value)

    def test_to_state_min_length(self) -> None:
        """Test to_state minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMTransitionAction(
                from_state="a",
                to_state="",
                trigger="go",
                action_name="action",
            )
        assert "to_state" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadFSMTransitionActionDefaultValues:
    """Test default values."""

    def test_default_parameters(self) -> None:
        """Test default parameters is empty dict."""
        payload = ModelPayloadFSMTransitionAction(
            from_state="a",
            to_state="b",
            trigger="go",
            action_name="action",
        )
        assert payload.parameters == {}

    def test_default_fsm_id(self) -> None:
        """Test default fsm_id is None."""
        payload = ModelPayloadFSMTransitionAction(
            from_state="a",
            to_state="b",
            trigger="go",
            action_name="action",
        )
        assert payload.fsm_id is None


@pytest.mark.unit
class TestModelPayloadFSMTransitionActionImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_from_state(self) -> None:
        """Test that from_state cannot be modified after creation."""
        payload = ModelPayloadFSMTransitionAction(
            from_state="a",
            to_state="b",
            trigger="go",
            action_name="action",
        )
        with pytest.raises(ValidationError):
            payload.from_state = "new"  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadFSMTransitionActionSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        fsm_id = uuid4()
        original = ModelPayloadFSMTransitionAction(
            from_state="cart",
            to_state="checkout",
            trigger="proceed",
            action_name="calculate",
            parameters={"discount": 10},
            fsm_id=fsm_id,
        )
        data = original.model_dump()
        restored = ModelPayloadFSMTransitionAction.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadFSMTransitionAction(
            from_state="a",
            to_state="b",
            trigger="go",
            action_name="action",
        )
        json_str = original.model_dump_json()
        restored = ModelPayloadFSMTransitionAction.model_validate_json(json_str)
        assert restored == original


# ==============================================================================
# ModelPayloadFSMCompleted Tests
# ==============================================================================


@pytest.mark.unit
class TestModelPayloadFSMCompletedInstantiation:
    """Test ModelPayloadFSMCompleted instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        fsm_id = uuid4()
        payload = ModelPayloadFSMCompleted(
            fsm_id=fsm_id,
            final_state="completed",
            completion_status="success",
        )
        assert payload.fsm_id == fsm_id
        assert payload.final_state == "completed"
        assert payload.completion_status == "success"
        assert payload.intent_type == "fsm_completed"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        fsm_id = uuid4()
        payload = ModelPayloadFSMCompleted(
            fsm_id=fsm_id,
            final_state="completed",
            completion_status="success",
            result_data={"order_total": 99.99, "items_count": 3},
            metadata={"duration_ms": 1500, "transitions": 5},
        )
        assert payload.fsm_id == fsm_id
        assert payload.final_state == "completed"
        assert payload.completion_status == "success"
        assert payload.result_data == {"order_total": 99.99, "items_count": 3}
        assert payload.metadata == {"duration_ms": 1500, "transitions": 5}


@pytest.mark.unit
class TestModelPayloadFSMCompletedDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'fsm_completed'."""
        payload = ModelPayloadFSMCompleted(
            fsm_id=uuid4(),
            final_state="done",
            completion_status="success",
        )
        assert payload.intent_type == "fsm_completed"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadFSMCompleted(
            fsm_id=uuid4(),
            final_state="done",
            completion_status="success",
        )
        data = payload.model_dump()
        assert data["intent_type"] == "fsm_completed"


@pytest.mark.unit
class TestModelPayloadFSMCompletedValidation:
    """Test field validation."""

    def test_fsm_id_required(self) -> None:
        """Test that fsm_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMCompleted(
                final_state="done",
                completion_status="success",
            )  # type: ignore[call-arg]
        assert "fsm_id" in str(exc_info.value)

    def test_final_state_required(self) -> None:
        """Test that final_state is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMCompleted(
                fsm_id=uuid4(),
                completion_status="success",
            )  # type: ignore[call-arg]
        assert "final_state" in str(exc_info.value)

    def test_completion_status_required(self) -> None:
        """Test that completion_status is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMCompleted(
                fsm_id=uuid4(),
                final_state="done",
            )  # type: ignore[call-arg]
        assert "completion_status" in str(exc_info.value)

    def test_valid_completion_statuses(self) -> None:
        """Test valid completion_status values."""
        for status in ["success", "failure", "cancelled", "timeout"]:
            payload = ModelPayloadFSMCompleted(
                fsm_id=uuid4(),
                final_state="done",
                completion_status=status,  # type: ignore[arg-type]
            )
            assert payload.completion_status == status

    def test_invalid_completion_status_rejected(self) -> None:
        """Test that invalid completion_status is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMCompleted(
                fsm_id=uuid4(),
                final_state="done",
                completion_status="error",  # type: ignore[arg-type]
            )
        assert "completion_status" in str(exc_info.value)

    def test_final_state_min_length(self) -> None:
        """Test final_state minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMCompleted(
                fsm_id=uuid4(),
                final_state="",
                completion_status="success",
            )
        assert "final_state" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadFSMCompletedDefaultValues:
    """Test default values."""

    def test_default_result_data(self) -> None:
        """Test default result_data is empty dict."""
        payload = ModelPayloadFSMCompleted(
            fsm_id=uuid4(),
            final_state="done",
            completion_status="success",
        )
        assert payload.result_data == {}

    def test_default_metadata(self) -> None:
        """Test default metadata is empty dict."""
        payload = ModelPayloadFSMCompleted(
            fsm_id=uuid4(),
            final_state="done",
            completion_status="success",
        )
        assert payload.metadata == {}


@pytest.mark.unit
class TestModelPayloadFSMCompletedImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_fsm_id(self) -> None:
        """Test that fsm_id cannot be modified after creation."""
        payload = ModelPayloadFSMCompleted(
            fsm_id=uuid4(),
            final_state="done",
            completion_status="success",
        )
        with pytest.raises(ValidationError):
            payload.fsm_id = uuid4()  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadFSMCompletedSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        fsm_id = uuid4()
        original = ModelPayloadFSMCompleted(
            fsm_id=fsm_id,
            final_state="completed",
            completion_status="success",
            result_data={"total": 100},
            metadata={"time_ms": 500},
        )
        data = original.model_dump()
        restored = ModelPayloadFSMCompleted.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadFSMCompleted(
            fsm_id=uuid4(),
            final_state="done",
            completion_status="success",
        )
        json_str = original.model_dump_json()
        restored = ModelPayloadFSMCompleted.model_validate_json(json_str)
        assert restored == original


@pytest.mark.unit
class TestModelPayloadFSMCompletedExtraFieldsRejected:
    """Test that extra fields are rejected for all FSM payloads."""

    def test_reject_extra_field_state_action(self) -> None:
        """Test that extra fields are rejected for ModelPayloadFSMStateAction."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMStateAction(
                state_name="state",
                action_type="on_enter",
                action_name="action",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)

    def test_reject_extra_field_transition_action(self) -> None:
        """Test that extra fields are rejected for ModelPayloadFSMTransitionAction."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMTransitionAction(
                from_state="a",
                to_state="b",
                trigger="go",
                action_name="action",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)

    def test_reject_extra_field_completed(self) -> None:
        """Test that extra fields are rejected for ModelPayloadFSMCompleted."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadFSMCompleted(
                fsm_id=uuid4(),
                final_state="done",
                completion_status="success",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
