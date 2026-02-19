# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ModelEventBusRuntimeState.

Comprehensive tests for event bus runtime state management including
factory methods, state transitions, and field validation.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.constants.constants_field_limits import (
    MAX_NAME_LENGTH,
    MAX_PATH_LENGTH,
)
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.event_bus.model_event_bus_runtime_state import (
    ModelEventBusRuntimeState,
)


@pytest.mark.unit
class TestModelEventBusRuntimeStateFactoryMethods:
    """Test ModelEventBusRuntimeState factory methods."""

    def test_create_unbound_returns_unbound_state(self) -> None:
        """Test create_unbound() factory method returns unbound state."""
        state = ModelEventBusRuntimeState.create_unbound()

        assert state is not None
        assert isinstance(state, ModelEventBusRuntimeState)
        assert state.is_bound is False
        assert state.node_name is None
        assert state.contract_path is None

    def test_create_unbound_returns_new_instance_each_call(self) -> None:
        """Test create_unbound() returns a new instance each time."""
        state1 = ModelEventBusRuntimeState.create_unbound()
        state2 = ModelEventBusRuntimeState.create_unbound()

        assert state1 is not state2

    def test_create_bound_returns_bound_state_with_correct_values(self) -> None:
        """Test create_bound() factory method returns bound state with correct values."""
        node_name = "test_node"
        contract_path = "/path/to/contract.yaml"

        state = ModelEventBusRuntimeState.create_bound(
            node_name=node_name, contract_path=contract_path
        )

        assert state is not None
        assert isinstance(state, ModelEventBusRuntimeState)
        assert state.is_bound is True
        assert state.node_name == node_name
        assert state.contract_path == contract_path

    def test_create_bound_without_contract_path(self) -> None:
        """Test create_bound() works without contract_path."""
        node_name = "test_node"

        state = ModelEventBusRuntimeState.create_bound(node_name=node_name)

        assert state.is_bound is True
        assert state.node_name == node_name
        assert state.contract_path is None

    def test_create_bound_with_empty_node_name(self) -> None:
        """Test create_bound() with empty node name.

        Note: Empty string is still allowed for backwards compatibility,
        but the preferred "not set" value is None.
        """
        state = ModelEventBusRuntimeState.create_bound(node_name="")

        assert state.is_bound is True
        assert state.node_name == ""
        # Note: is_ready() will be False because node_name is empty


@pytest.mark.unit
class TestModelEventBusRuntimeStateIsReady:
    """Test ModelEventBusRuntimeState.is_ready() method."""

    def test_is_ready_returns_true_when_bound_and_has_node_name(self) -> None:
        """Test is_ready() returns True only when bound AND has node_name."""
        state = ModelEventBusRuntimeState(
            node_name="my_node",
            is_bound=True,
        )

        assert state.is_ready() is True

    def test_is_ready_returns_false_when_not_bound(self) -> None:
        """Test is_ready() returns False when not bound."""
        state = ModelEventBusRuntimeState(
            node_name="my_node",
            is_bound=False,
        )

        assert state.is_ready() is False

    def test_is_ready_returns_false_when_node_name_none(self) -> None:
        """Test is_ready() returns False when node_name is None."""
        state = ModelEventBusRuntimeState(
            node_name=None,
            is_bound=True,
        )

        assert state.is_ready() is False

    def test_is_ready_returns_false_when_node_name_empty(self) -> None:
        """Test is_ready() returns False when node_name is empty string."""
        state = ModelEventBusRuntimeState(
            node_name="",
            is_bound=True,
        )

        assert state.is_ready() is False

    def test_is_ready_returns_false_when_unbound_state(self) -> None:
        """Test is_ready() returns False for unbound state."""
        state = ModelEventBusRuntimeState.create_unbound()

        assert state.is_ready() is False

    @pytest.mark.parametrize(
        ("node_name", "is_bound", "expected"),
        [
            ("node", True, True),
            ("node", False, False),
            (None, True, False),
            (None, False, False),
            ("", True, False),
            ("", False, False),
            ("   ", True, True),  # Whitespace-only is truthy
        ],
    )
    def test_is_ready_parametrized(
        self, node_name: str | None, is_bound: bool, expected: bool
    ) -> None:
        """Test is_ready() with various combinations of node_name and is_bound."""
        state = ModelEventBusRuntimeState(
            node_name=node_name,
            is_bound=is_bound,
        )

        assert state.is_ready() is expected


@pytest.mark.unit
class TestModelEventBusRuntimeStateHasNodeName:
    """Test ModelEventBusRuntimeState.has_node_name() method."""

    def test_has_node_name_returns_true_when_set(self) -> None:
        """Test has_node_name() returns True when node_name is set."""
        state = ModelEventBusRuntimeState(node_name="my_node")

        assert state.has_node_name() is True

    def test_has_node_name_returns_false_when_none(self) -> None:
        """Test has_node_name() returns False when node_name is None."""
        state = ModelEventBusRuntimeState(node_name=None)

        assert state.has_node_name() is False

    def test_has_node_name_returns_false_when_empty_string(self) -> None:
        """Test has_node_name() returns False when node_name is empty string."""
        state = ModelEventBusRuntimeState(node_name="")

        assert state.has_node_name() is False

    def test_has_node_name_returns_false_for_default_state(self) -> None:
        """Test has_node_name() returns False for default state."""
        state = ModelEventBusRuntimeState()

        assert state.has_node_name() is False

    def test_has_node_name_returns_true_for_whitespace(self) -> None:
        """Test has_node_name() returns True for whitespace-only (truthy)."""
        state = ModelEventBusRuntimeState(node_name="   ")

        assert state.has_node_name() is True


@pytest.mark.unit
class TestModelEventBusRuntimeStateHasContract:
    """Test ModelEventBusRuntimeState.has_contract() method."""

    def test_has_contract_returns_true_when_contract_path_is_set(self) -> None:
        """Test has_contract() returns True when contract_path is set."""
        state = ModelEventBusRuntimeState(
            contract_path="/path/to/contract.yaml",
        )

        assert state.has_contract() is True

    def test_has_contract_returns_false_when_contract_path_is_none(self) -> None:
        """Test has_contract() returns False when contract_path is None."""
        state = ModelEventBusRuntimeState(
            contract_path=None,
        )

        assert state.has_contract() is False

    def test_has_contract_returns_true_for_empty_string_path(self) -> None:
        """Test has_contract() returns True for empty string (not None)."""
        state = ModelEventBusRuntimeState(
            contract_path="",
        )

        # Empty string is not None, so has_contract returns True
        assert state.has_contract() is True

    def test_has_contract_for_unbound_state(self) -> None:
        """Test has_contract() for unbound state (default None)."""
        state = ModelEventBusRuntimeState.create_unbound()

        assert state.has_contract() is False


@pytest.mark.unit
class TestModelEventBusRuntimeStateReset:
    """Test ModelEventBusRuntimeState.reset() method."""

    def test_reset_clears_is_bound(self) -> None:
        """Test reset() clears is_bound but preserves other fields."""
        state = ModelEventBusRuntimeState(
            node_name="my_node",
            contract_path="/path/to/contract.yaml",
            is_bound=True,
        )

        state.reset()

        assert state.is_bound is False
        # Other fields should be preserved
        assert state.node_name == "my_node"
        assert state.contract_path == "/path/to/contract.yaml"

    def test_reset_on_already_unbound_state(self) -> None:
        """Test reset() on already unbound state is idempotent."""
        state = ModelEventBusRuntimeState.create_unbound()

        state.reset()

        assert state.is_bound is False
        assert state.node_name is None
        assert state.contract_path is None

    def test_reset_multiple_times(self) -> None:
        """Test reset() can be called multiple times safely."""
        state = ModelEventBusRuntimeState(
            node_name="my_node",
            is_bound=True,
        )

        state.reset()
        state.reset()
        state.reset()

        assert state.is_bound is False
        assert state.node_name == "my_node"


@pytest.mark.unit
class TestModelEventBusRuntimeStateBind:
    """Test ModelEventBusRuntimeState.bind() method."""

    def test_bind_sets_all_fields_correctly(self) -> None:
        """Test bind() sets all fields correctly."""
        state = ModelEventBusRuntimeState.create_unbound()

        state.bind(node_name="my_node", contract_path="/path/to/contract.yaml")

        assert state.node_name == "my_node"
        assert state.contract_path == "/path/to/contract.yaml"
        assert state.is_bound is True

    def test_bind_without_contract_path(self) -> None:
        """Test bind() without contract_path."""
        state = ModelEventBusRuntimeState.create_unbound()

        state.bind(node_name="my_node")

        assert state.node_name == "my_node"
        assert state.contract_path is None
        assert state.is_bound is True

    def test_bind_overwrites_existing_values(self) -> None:
        """Test bind() overwrites existing values."""
        state = ModelEventBusRuntimeState(
            node_name="old_node",
            contract_path="/old/path.yaml",
            is_bound=True,
        )

        state.bind(node_name="new_node", contract_path="/new/path.yaml")

        assert state.node_name == "new_node"
        assert state.contract_path == "/new/path.yaml"
        assert state.is_bound is True

    def test_bind_after_reset(self) -> None:
        """Test bind() after reset() restores bound state."""
        state = ModelEventBusRuntimeState(
            node_name="my_node",
            is_bound=True,
        )

        state.reset()
        assert not state.is_bound

        state.bind(node_name="new_node")
        assert state.is_bound
        assert state.node_name == "new_node"


@pytest.mark.unit
class TestModelEventBusRuntimeStateFieldValidation:
    """Test ModelEventBusRuntimeState field validation (max_length constraints)."""

    def test_node_name_max_length_constraint(self) -> None:
        """Test node_name respects max_length constraint."""
        # Should work with max length
        max_name = "x" * MAX_NAME_LENGTH
        state = ModelEventBusRuntimeState(node_name=max_name)
        assert len(state.node_name) == MAX_NAME_LENGTH

    def test_node_name_exceeds_max_length_raises_error(self) -> None:
        """Test node_name exceeding max_length raises ValidationError."""
        too_long_name = "x" * (MAX_NAME_LENGTH + 1)

        with pytest.raises(ValidationError) as exc_info:
            ModelEventBusRuntimeState(node_name=too_long_name)

        assert "node_name" in str(exc_info.value)

    def test_contract_path_max_length_constraint(self) -> None:
        """Test contract_path respects max_length constraint."""
        # Should work with max length
        max_path = "/" + "x" * (MAX_PATH_LENGTH - 1)
        state = ModelEventBusRuntimeState(contract_path=max_path)
        assert len(state.contract_path) == MAX_PATH_LENGTH

    def test_contract_path_exceeds_max_length_raises_error(self) -> None:
        """Test contract_path exceeding max_length raises ValidationError."""
        too_long_path = "/" + "x" * MAX_PATH_LENGTH

        with pytest.raises(ValidationError) as exc_info:
            ModelEventBusRuntimeState(contract_path=too_long_path)

        assert "contract_path" in str(exc_info.value)

    def test_bind_with_name_exceeding_max_length_raises_error(self) -> None:
        """Test that bind() properly validates max_length constraints.

        This validates the fix for PR #266 CodeRabbit review: bind() now
        explicitly validates max_length since direct field assignment bypasses
        Pydantic's field validation.
        """
        state = ModelEventBusRuntimeState()
        too_long_name = "x" * (MAX_NAME_LENGTH + 1)

        with pytest.raises(ModelOnexError) as exc_info:
            state.bind(node_name=too_long_name)

        assert "node_name exceeds max length" in str(exc_info.value)
        assert str(MAX_NAME_LENGTH) in str(exc_info.value)

    def test_bind_with_contract_path_exceeding_max_length_raises_error(self) -> None:
        """Test that bind() properly validates contract_path max_length constraints.

        This validates the fix for PR #266 CodeRabbit review: bind() now
        explicitly validates max_length since direct field assignment bypasses
        Pydantic's field validation.
        """
        state = ModelEventBusRuntimeState()
        too_long_path = "/" + "x" * MAX_PATH_LENGTH  # exceeds by 1

        with pytest.raises(ModelOnexError) as exc_info:
            state.bind(node_name="valid_name", contract_path=too_long_path)

        assert "contract_path exceeds max length" in str(exc_info.value)
        assert str(MAX_PATH_LENGTH) in str(exc_info.value)


@pytest.mark.unit
class TestModelEventBusRuntimeStateSerialization:
    """Test ModelEventBusRuntimeState serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump() serialization."""
        state = ModelEventBusRuntimeState(
            node_name="my_node",
            contract_path="/path/to/contract.yaml",
            is_bound=True,
        )

        data = state.model_dump()

        assert isinstance(data, dict)
        assert data["node_name"] == "my_node"
        assert data["contract_path"] == "/path/to/contract.yaml"
        assert data["is_bound"] is True

    def test_model_validate(self) -> None:
        """Test model_validate() deserialization."""
        data = {
            "node_name": "my_node",
            "contract_path": "/path/to/contract.yaml",
            "is_bound": True,
        }

        state = ModelEventBusRuntimeState.model_validate(data)

        assert state.node_name == "my_node"
        assert state.contract_path == "/path/to/contract.yaml"
        assert state.is_bound is True

    def test_serialization_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusRuntimeState(
            node_name="my_node",
            contract_path="/path/to/contract.yaml",
            is_bound=True,
        )

        data = original.model_dump()
        restored = ModelEventBusRuntimeState.model_validate(data)

        assert restored.node_name == original.node_name
        assert restored.contract_path == original.contract_path
        assert restored.is_bound == original.is_bound

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        state = ModelEventBusRuntimeState(
            node_name="my_node",
            is_bound=True,
        )

        json_data = state.model_dump_json()

        assert isinstance(json_data, str)
        assert "node_name" in json_data
        assert "is_bound" in json_data


@pytest.mark.unit
class TestModelEventBusRuntimeStateModelConfig:
    """Test ModelEventBusRuntimeState model configuration."""

    def test_model_is_mutable(self) -> None:
        """Test that the model is mutable (frozen=False)."""
        state = ModelEventBusRuntimeState(node_name="original")

        # Should be able to modify in place
        state.node_name = "modified"

        assert state.node_name == "modified"

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventBusRuntimeState(
                node_name="my_node",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

        assert "extra_field" in str(exc_info.value)

    def test_model_copy(self) -> None:
        """Test model_copy() creates an independent copy."""
        original = ModelEventBusRuntimeState(
            node_name="my_node",
            is_bound=True,
        )

        copied = original.model_copy()

        assert copied is not original
        assert copied.node_name == original.node_name
        assert copied.is_bound == original.is_bound

        # Modify copy should not affect original
        copied.node_name = "modified"
        assert original.node_name == "my_node"


@pytest.mark.unit
class TestModelEventBusRuntimeStateDefaults:
    """Test ModelEventBusRuntimeState default values."""

    def test_default_values(self) -> None:
        """Test default values when creating empty instance."""
        state = ModelEventBusRuntimeState()

        assert state.node_name is None
        assert state.contract_path is None
        assert state.is_bound is False

    def test_default_state_is_not_ready(self) -> None:
        """Test default state is not ready."""
        state = ModelEventBusRuntimeState()

        assert state.is_ready() is False

    def test_default_state_has_no_contract(self) -> None:
        """Test default state has no contract."""
        state = ModelEventBusRuntimeState()

        assert state.has_contract() is False
