# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelPartialUpdateOperation.

Tests cover:
1. Valid partial update operations with all required fields
2. Trigger event pattern validation (lowercase.segments.vN format)
3. Column list validation (non-empty)
4. Name validation (non-empty)
5. Optional fields (skip_idempotency, condition)
6. Unknown fields rejected (extra='forbid')
7. Frozen/immutable behavior
8. Serialization roundtrip (dict and JSON)

Use Cases Covered:
    - Heartbeat updates (updating last_heartbeat_at, liveness_deadline)
    - State transitions (updating current_state with skip_idempotency)
    - Timeout markers (conditional single-column updates)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelPartialUpdateOperationCreation:
    """Tests for ModelPartialUpdateOperation creation and validation."""

    def test_valid_operation_minimal(self) -> None:
        """Valid operation with only required fields."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at"],
            trigger_event="node.heartbeat.v1",
        )

        assert op.name == "heartbeat"
        assert op.columns == ["last_heartbeat_at"]
        assert op.trigger_event == "node.heartbeat.v1"
        assert op.skip_idempotency is False
        assert op.condition is None

    def test_valid_operation_with_all_fields(self) -> None:
        """Valid operation with all fields specified."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="state_transition",
            columns=["current_state", "updated_at"],
            trigger_event="node.state.changed.v1",
            skip_idempotency=True,
            condition="current_state != 'TERMINATED'",
        )

        assert op.name == "state_transition"
        assert op.columns == ["current_state", "updated_at"]
        assert op.trigger_event == "node.state.changed.v1"
        assert op.skip_idempotency is True
        assert op.condition == "current_state != 'TERMINATED'"

    def test_valid_operation_multiple_columns(self) -> None:
        """Valid operation with multiple columns."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at", "liveness_deadline", "updated_at"],
            trigger_event="node.heartbeat.v1",
        )

        assert len(op.columns) == 3
        assert "last_heartbeat_at" in op.columns
        assert "liveness_deadline" in op.columns
        assert "updated_at" in op.columns


@pytest.mark.unit
class TestModelPartialUpdateOperationTriggerEventValidation:
    """Tests for trigger_event pattern validation."""

    def test_valid_trigger_event_simple(self) -> None:
        """Simple event names are valid: domain.action.version."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="test",
            columns=["col1"],
            trigger_event="node.heartbeat.v1",
        )

        assert op.trigger_event == "node.heartbeat.v1"

    def test_valid_trigger_event_with_underscores(self) -> None:
        """Event names with underscores are valid."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="test",
            columns=["col1"],
            trigger_event="node_registration.heartbeat_received.v1",
        )

        assert op.trigger_event == "node_registration.heartbeat_received.v1"

    def test_valid_trigger_event_multi_segment(self) -> None:
        """Event names with multiple segments are valid."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="test",
            columns=["col1"],
            trigger_event="domain.subdomain.entity.action.v10",
        )

        assert op.trigger_event == "domain.subdomain.entity.action.v10"

    def test_invalid_trigger_event_no_version(self) -> None:
        """Event names without version suffix are rejected."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(
                name="test",
                columns=["col1"],
                trigger_event="node.heartbeat",  # Missing version
            )

        assert "node.heartbeat" in str(exc_info.value)

    def test_invalid_trigger_event_uppercase(self) -> None:
        """Event names with uppercase letters are rejected."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(
                name="test",
                columns=["col1"],
                trigger_event="Node.Heartbeat.v1",  # Uppercase not allowed
            )

        assert "Node.Heartbeat.v1" in str(exc_info.value)

    def test_invalid_trigger_event_hyphen(self) -> None:
        """Event names with hyphens are rejected (use underscores)."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(
                name="test",
                columns=["col1"],
                trigger_event="node-service.heartbeat.v1",  # Hyphen not allowed
            )

        assert "node-service.heartbeat.v1" in str(exc_info.value)

    def test_invalid_trigger_event_starts_with_number(self) -> None:
        """Event names starting with number are rejected."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(
                name="test",
                columns=["col1"],
                trigger_event="1node.heartbeat.v1",  # Starts with number
            )

        assert "1node.heartbeat.v1" in str(exc_info.value)


@pytest.mark.unit
class TestModelPartialUpdateOperationRequiredFields:
    """Tests for required field validation."""

    def test_name_is_required(self) -> None:
        """name field is required."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(  # type: ignore[call-arg]
                # name missing
                columns=["col1"],
                trigger_event="node.heartbeat.v1",
            )

        assert "name" in str(exc_info.value)

    def test_name_cannot_be_empty(self) -> None:
        """name field cannot be empty string."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(
                name="",  # Empty string
                columns=["col1"],
                trigger_event="node.heartbeat.v1",
            )

        error_str = str(exc_info.value).lower()
        assert "name" in error_str or "min_length" in error_str

    def test_columns_is_required(self) -> None:
        """columns field is required."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(  # type: ignore[call-arg]
                name="test",
                # columns missing
                trigger_event="node.heartbeat.v1",
            )

        assert "columns" in str(exc_info.value)

    def test_columns_cannot_be_empty(self) -> None:
        """columns field cannot be empty list."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(
                name="test",
                columns=[],  # Empty list
                trigger_event="node.heartbeat.v1",
            )

        error_str = str(exc_info.value).lower()
        assert "columns" in error_str or "min_length" in error_str

    def test_trigger_event_is_required(self) -> None:
        """trigger_event field is required."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(  # type: ignore[call-arg]
                name="test",
                columns=["col1"],
                # trigger_event missing
            )

        assert "trigger_event" in str(exc_info.value)


@pytest.mark.unit
class TestModelPartialUpdateOperationImmutability:
    """Tests for frozen/immutable behavior."""

    def test_operation_is_frozen(self) -> None:
        """Operation should be immutable after creation."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at"],
            trigger_event="node.heartbeat.v1",
        )

        with pytest.raises(ValidationError):
            op.name = "new_name"  # type: ignore[misc]

    def test_operation_is_hashable(self) -> None:
        """Frozen operation should be hashable."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at"],
            trigger_event="node.heartbeat.v1",
        )

        hash_value = hash(op)
        assert isinstance(hash_value, int)

    def test_operation_can_be_in_set(self) -> None:
        """Operation can be used in a set (hashable)."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op1 = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at"],
            trigger_event="node.heartbeat.v1",
        )

        op2 = ModelPartialUpdateOperation(
            name="state_transition",
            columns=["current_state"],
            trigger_event="node.state.changed.v1",
        )

        op_set = {op1, op2}
        assert len(op_set) == 2


@pytest.mark.unit
class TestModelPartialUpdateOperationExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        with pytest.raises(ValidationError) as exc_info:
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at"],
                trigger_event="node.heartbeat.v1",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelPartialUpdateOperationSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        original = ModelPartialUpdateOperation(
            name="state_transition",
            columns=["current_state", "updated_at"],
            trigger_event="node.state.changed.v1",
            skip_idempotency=True,
            condition="current_state != 'TERMINATED'",
        )

        data = original.model_dump()
        restored = ModelPartialUpdateOperation.model_validate(data)

        assert restored.name == original.name
        assert restored.columns == original.columns
        assert restored.trigger_event == original.trigger_event
        assert restored.skip_idempotency == original.skip_idempotency
        assert restored.condition == original.condition

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        original = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at", "liveness_deadline"],
            trigger_event="node.heartbeat.v1",
        )

        json_str = original.model_dump_json()
        restored = ModelPartialUpdateOperation.model_validate_json(json_str)

        assert restored.name == original.name
        assert restored.columns == original.columns
        assert restored.trigger_event == original.trigger_event

    def test_yaml_roundtrip(self) -> None:
        """Model -> YAML -> Model produces identical result (if pyyaml available)."""
        pytest.importorskip("yaml")
        import yaml

        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        original = ModelPartialUpdateOperation(
            name="ack_timeout_marker",
            columns=["ack_timeout_emitted_at"],
            trigger_event="node.ack.timeout.v1",
            condition="ack_timeout_emitted_at IS NULL",
        )

        yaml_str = yaml.safe_dump(original.model_dump(), default_flow_style=False)
        loaded_data = yaml.safe_load(yaml_str)
        restored = ModelPartialUpdateOperation.model_validate(loaded_data)

        assert restored.name == original.name
        assert restored.columns == original.columns
        assert restored.trigger_event == original.trigger_event
        assert restored.condition == original.condition


@pytest.mark.unit
class TestModelPartialUpdateOperationRepr:
    """Tests for __repr__ method."""

    def test_repr_basic(self) -> None:
        """Test basic repr output contains class name, name, columns, and trigger."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at", "liveness_deadline"],
            trigger_event="node.heartbeat.v1",
        )
        result = repr(op)

        assert "ModelPartialUpdateOperation" in result
        assert "heartbeat" in result
        assert "columns=2" in result
        assert "node.heartbeat.v1" in result

    def test_repr_single_column(self) -> None:
        """Test repr correctly shows column count for single column."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="timeout_marker",
            columns=["timeout_emitted_at"],
            trigger_event="node.timeout.v1",
        )
        result = repr(op)

        assert "columns=1" in result


@pytest.mark.unit
class TestModelPartialUpdateOperationUseCases:
    """Tests for specific use cases from OMN-1170."""

    def test_heartbeat_update_use_case(self) -> None:
        """Test heartbeat update use case: updates last_heartbeat_at, liveness_deadline."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="heartbeat",
            columns=["last_heartbeat_at", "liveness_deadline"],
            trigger_event="node.heartbeat.v1",
        )

        assert op.name == "heartbeat"
        assert "last_heartbeat_at" in op.columns
        assert "liveness_deadline" in op.columns
        assert op.skip_idempotency is False  # Normal idempotency checking

    def test_state_transition_use_case(self) -> None:
        """Test state transition use case: updates current_state without idempotency."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="state_transition",
            columns=["current_state", "updated_at"],
            trigger_event="node.state.changed.v1",
            skip_idempotency=True,  # State transitions are inherently idempotent
        )

        assert op.name == "state_transition"
        assert "current_state" in op.columns
        assert op.skip_idempotency is True

    def test_ack_timeout_marker_use_case(self) -> None:
        """Test ack timeout marker use case: single column with condition."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="ack_timeout_marker",
            columns=["ack_timeout_emitted_at"],
            trigger_event="node.ack.timeout.v1",
            condition="ack_timeout_emitted_at IS NULL",
        )

        assert op.name == "ack_timeout_marker"
        assert op.columns == ["ack_timeout_emitted_at"]
        assert op.condition == "ack_timeout_emitted_at IS NULL"

    def test_liveness_timeout_marker_use_case(self) -> None:
        """Test liveness timeout marker use case: single column with condition."""
        from omnibase_core.models.projectors import ModelPartialUpdateOperation

        op = ModelPartialUpdateOperation(
            name="liveness_timeout_marker",
            columns=["liveness_timeout_emitted_at"],
            trigger_event="node.liveness.timeout.v1",
            condition="liveness_timeout_emitted_at IS NULL",
        )

        assert op.name == "liveness_timeout_marker"
        assert op.columns == ["liveness_timeout_emitted_at"]
        assert op.condition == "liveness_timeout_emitted_at IS NULL"
