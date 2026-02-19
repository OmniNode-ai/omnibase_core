# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelFsmData.

Tests all aspects of the FSM data structure model including:
- Model instantiation and validation
- FSM structure validation
- State and transition queries
- Helper methods (get_state_by_name, get_transitions_from_state, etc.)
- Protocol implementations (execute, serialize, validate)
- Edge cases and complex FSM scenarios
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.fsm.model_fsm_data import ModelFsmData
from omnibase_core.models.fsm.model_fsm_state import ModelFsmState
from omnibase_core.models.fsm.model_fsm_transition import ModelFsmTransition


@pytest.mark.unit
class TestModelFsmDataInstantiation:
    """Test cases for ModelFsmData instantiation."""

    def test_model_instantiation_minimal(self):
        """Test model instantiation with minimal required data."""
        states = [
            ModelFsmState(name="start", is_initial=True),
            ModelFsmState(name="end", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="start", to_state="end", trigger="finish")
        ]

        fsm = ModelFsmData(
            state_machine_name="minimal_fsm",
            initial_state="start",
            states=states,
            transitions=transitions,
        )

        assert fsm.state_machine_name == "minimal_fsm"
        assert fsm.description == ""
        assert fsm.initial_state == "start"
        assert len(fsm.states) == 2
        assert len(fsm.transitions) == 1
        # Deep immutability: variables/metadata are tuple[tuple[str, str], ...]
        assert fsm.variables == ()
        # Deep immutability: global_actions is tuple[str, ...]
        assert fsm.global_actions == ()
        assert fsm.metadata == ()

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields populated."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="active"),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="idle", to_state="active", trigger="start"),
            ModelFsmTransition(from_state="active", to_state="done", trigger="finish"),
        ]

        fsm = ModelFsmData(
            state_machine_name="full_fsm",
            description="A complete FSM example",
            initial_state="idle",
            states=states,
            transitions=transitions,
            variables={"counter": "0", "mode": "normal"},
            global_actions=["log", "notify"],
            metadata={"version": "1.0", "author": "test"},
        )

        assert fsm.state_machine_name == "full_fsm"
        assert fsm.description == "A complete FSM example"
        assert fsm.initial_state == "idle"
        assert len(fsm.states) == 3
        assert len(fsm.transitions) == 2
        # Deep immutability: dict converted to tuple of tuples
        # Order depends on dict iteration order (Python 3.7+: insertion order)
        assert dict(fsm.variables) == {"counter": "0", "mode": "normal"}
        assert fsm.global_actions == ("log", "notify")
        assert dict(fsm.metadata) == {"version": "1.0", "author": "test"}


@pytest.mark.unit
class TestModelFsmDataValidation:
    """Test validation rules for ModelFsmData."""

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        # Missing state_machine_name
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmData(
                initial_state="s1",
                states=states,
                transitions=transitions,
            )
        assert "state_machine_name" in str(exc_info.value)

        # Missing initial_state
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmData(
                state_machine_name="fsm",
                states=states,
                transitions=transitions,
            )
        assert "initial_state" in str(exc_info.value)

        # Missing states
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmData(
                state_machine_name="fsm",
                initial_state="s1",
                transitions=transitions,
            )
        assert "states" in str(exc_info.value)

        # Missing transitions
        with pytest.raises(ValidationError) as exc_info:
            ModelFsmData(
                state_machine_name="fsm",
                initial_state="s1",
                states=states,
            )
        assert "transitions" in str(exc_info.value)

    def test_states_list_type_validation(self):
        """Test that states must be a list of ModelFsmState."""
        transitions = []

        # Invalid states type
        with pytest.raises(ValidationError):
            ModelFsmData(
                state_machine_name="fsm",
                initial_state="s1",
                states="not_a_list",
                transitions=transitions,
            )

        # Invalid item type in states list
        with pytest.raises(ValidationError):
            ModelFsmData(
                state_machine_name="fsm",
                initial_state="s1",
                states=["string_state"],
                transitions=transitions,
            )

    def test_transitions_list_type_validation(self):
        """Test that transitions must be a list of ModelFsmTransition."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]

        # Invalid transitions type
        with pytest.raises(ValidationError):
            ModelFsmData(
                state_machine_name="fsm",
                initial_state="s1",
                states=states,
                transitions="not_a_list",
            )

        # Invalid item type in transitions list
        with pytest.raises(ValidationError):
            ModelFsmData(
                state_machine_name="fsm",
                initial_state="s1",
                states=states,
                transitions=["string_transition"],
            )


@pytest.mark.unit
class TestModelFsmDataStateQueries:
    """Test state query methods."""

    def test_get_state_by_name_existing(self):
        """Test getting an existing state by name."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="active"),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        state = fsm.get_state_by_name("active")
        assert state is not None
        assert state.name == "active"

    def test_get_state_by_name_nonexistent(self):
        """Test getting a non-existent state returns None."""
        states = [ModelFsmState(name="idle", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        state = fsm.get_state_by_name("nonexistent")
        assert state is None

    def test_get_state_by_name_empty_states(self):
        """Test getting state when states list has only unrelated states.

        Note: ModelFsmData is frozen (immutable), so we test that searching
        for a non-matching state returns None rather than testing empty list.
        """
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="s1",
            states=states,
            transitions=transitions,
        )

        # Model is frozen - search for a state that doesn't exist
        state = fsm.get_state_by_name("any")
        assert state is None


@pytest.mark.unit
class TestModelFsmDataTransitionQueries:
    """Test transition query methods."""

    def test_get_transitions_from_state(self):
        """Test getting transitions from a specific state."""
        states = [
            ModelFsmState(name="a", is_initial=True),
            ModelFsmState(name="b"),
            ModelFsmState(name="c", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="a", to_state="b", trigger="t1"),
            ModelFsmTransition(from_state="a", to_state="c", trigger="t2"),
            ModelFsmTransition(from_state="b", to_state="c", trigger="t3"),
        ]

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="a",
            states=states,
            transitions=transitions,
        )

        from_a = fsm.get_transitions_from_state("a")
        assert len(from_a) == 2
        assert all(t.from_state == "a" for t in from_a)

        from_b = fsm.get_transitions_from_state("b")
        assert len(from_b) == 1
        assert from_b[0].from_state == "b"

    def test_get_transitions_from_state_no_transitions(self):
        """Test getting transitions from state with no outgoing transitions."""
        states = [
            ModelFsmState(name="start", is_initial=True),
            ModelFsmState(name="end", is_final=True),
        ]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="start",
            states=states,
            transitions=transitions,
        )

        result = fsm.get_transitions_from_state("end")
        assert result == []

    def test_get_transitions_to_state(self):
        """Test getting transitions to a specific state."""
        states = [
            ModelFsmState(name="a", is_initial=True),
            ModelFsmState(name="b"),
            ModelFsmState(name="c", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="a", to_state="c", trigger="t1"),
            ModelFsmTransition(from_state="b", to_state="c", trigger="t2"),
        ]

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="a",
            states=states,
            transitions=transitions,
        )

        to_c = fsm.get_transitions_to_state("c")
        assert len(to_c) == 2
        assert all(t.to_state == "c" for t in to_c)

    def test_get_transitions_to_state_no_incoming(self):
        """Test getting transitions to state with no incoming transitions."""
        states = [
            ModelFsmState(name="start", is_initial=True),
            ModelFsmState(name="end", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="start", to_state="end", trigger="finish")
        ]

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="start",
            states=states,
            transitions=transitions,
        )

        result = fsm.get_transitions_to_state("start")
        assert result == []


@pytest.mark.unit
class TestModelFsmDataStructureValidation:
    """Test FSM structure validation."""

    def test_validate_fsm_structure_valid(self):
        """Test validation of a valid FSM structure."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="active"),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="idle", to_state="active", trigger="start"),
            ModelFsmTransition(from_state="active", to_state="done", trigger="finish"),
        ]

        fsm = ModelFsmData(
            state_machine_name="valid",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert errors == []

    def test_validate_fsm_structure_missing_initial_state(self):
        """Test validation fails when initial state doesn't exist."""
        states = [
            ModelFsmState(name="active"),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="nonexistent",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert len(errors) > 0
        assert any("Initial state" in error for error in errors)

    def test_validate_fsm_structure_no_final_state(self):
        """Test validation fails when no final state exists."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="active"),
        ]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert len(errors) > 0
        assert any("final state" in error for error in errors)

    def test_validate_fsm_structure_invalid_transition_from(self):
        """Test validation fails for transition from non-existent state."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(
                from_state="nonexistent", to_state="done", trigger="finish"
            )
        ]

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert len(errors) > 0
        assert any("unknown state" in error.lower() for error in errors)

    def test_validate_fsm_structure_invalid_transition_to(self):
        """Test validation fails for transition to non-existent state."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(
                from_state="idle", to_state="nonexistent", trigger="start"
            )
        ]

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert len(errors) > 0
        assert any("unknown state" in error.lower() for error in errors)

    def test_validate_fsm_structure_multiple_errors(self):
        """Test validation with multiple errors."""
        states = [ModelFsmState(name="only_state")]
        transitions = [
            ModelFsmTransition(from_state="bad1", to_state="bad2", trigger="t")
        ]

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="nonexistent",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert len(errors) >= 3  # Initial state, no final state, bad transitions


@pytest.mark.unit
class TestModelFsmDataProtocols:
    """Test protocol implementations for ModelFsmData."""

    def test_execute_protocol(self):
        """Test execute protocol method."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="s1",
            states=states,
            transitions=transitions,
        )

        result = fsm.execute()
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="idle", to_state="done", trigger="finish")
        ]

        fsm = ModelFsmData(
            state_machine_name="serialize_test",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        serialized = fsm.serialize()

        assert isinstance(serialized, dict)
        assert serialized["state_machine_name"] == "serialize_test"
        assert serialized["initial_state"] == "idle"
        assert "states" in serialized
        assert "transitions" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="test",
            initial_state="s1",
            states=states,
            transitions=transitions,
        )

        result = fsm.validate_instance()
        assert result is True


@pytest.mark.unit
class TestModelFsmDataSerialization:
    """Test serialization and deserialization for ModelFsmData."""

    def test_model_dump(self):
        """Test model_dump method."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="dump_test",
            initial_state="s1",
            states=states,
            transitions=transitions,
        )

        data = fsm.model_dump()

        assert isinstance(data, dict)
        assert data["state_machine_name"] == "dump_test"
        assert "states" in data
        assert "transitions" in data

    def test_model_validate(self):
        """Test model_validate method."""
        data = {
            "state_machine_name": "validate_test",
            "initial_state": "start",
            "states": [{"name": "start", "is_initial": True, "is_final": True}],
            "transitions": [],
        }

        fsm = ModelFsmData.model_validate(data)

        assert fsm.state_machine_name == "validate_test"
        assert fsm.initial_state == "start"
        assert len(fsm.states) == 1

    def test_model_dump_json(self):
        """Test JSON serialization."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="json_test",
            initial_state="s1",
            states=states,
            transitions=transitions,
        )

        json_str = fsm.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str


@pytest.mark.unit
class TestModelFsmDataEdgeCases:
    """Test edge cases for ModelFsmData."""

    def test_empty_state_machine_name(self):
        """Test FSM with empty name."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="",
            initial_state="s1",
            states=states,
            transitions=transitions,
        )
        assert fsm.state_machine_name == ""

    def test_single_state_fsm(self):
        """Test FSM with single state (both initial and final)."""
        states = [ModelFsmState(name="only", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="single",
            initial_state="only",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert errors == []

    def test_self_transitions(self):
        """Test FSM with self-transitions."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="done", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="idle", to_state="idle", trigger="retry"),
            ModelFsmTransition(from_state="idle", to_state="done", trigger="finish"),
        ]

        fsm = ModelFsmData(
            state_machine_name="self_loop",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert errors == []

        self_transitions = fsm.get_transitions_from_state("idle")
        assert len(self_transitions) == 2

    def test_multiple_final_states(self):
        """Test FSM with multiple final states."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="success", is_final=True),
            ModelFsmState(name="failure", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(from_state="idle", to_state="success", trigger="ok"),
            ModelFsmTransition(from_state="idle", to_state="failure", trigger="fail"),
        ]

        fsm = ModelFsmData(
            state_machine_name="multi_final",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        errors = fsm.validate_fsm_structure()
        assert errors == []

    def test_disconnected_states(self):
        """Test FSM with disconnected states."""
        states = [
            ModelFsmState(name="idle", is_initial=True),
            ModelFsmState(name="done", is_final=True),
            ModelFsmState(name="orphan"),  # Disconnected state
        ]
        transitions = [
            ModelFsmTransition(from_state="idle", to_state="done", trigger="finish")
        ]

        fsm = ModelFsmData(
            state_machine_name="disconnected",
            initial_state="idle",
            states=states,
            transitions=transitions,
        )

        # Structure validation passes (doesn't check connectivity)
        errors = fsm.validate_fsm_structure()
        assert errors == []

    def test_complex_fsm_structure(self):
        """Test complex FSM with multiple paths."""
        states = [
            ModelFsmState(name="start", is_initial=True),
            ModelFsmState(name="processing"),
            ModelFsmState(name="waiting"),
            ModelFsmState(name="retrying"),
            ModelFsmState(name="success", is_final=True),
            ModelFsmState(name="failed", is_final=True),
        ]
        transitions = [
            ModelFsmTransition(
                from_state="start", to_state="processing", trigger="begin"
            ),
            ModelFsmTransition(
                from_state="processing", to_state="waiting", trigger="wait"
            ),
            ModelFsmTransition(
                from_state="waiting", to_state="processing", trigger="continue"
            ),
            ModelFsmTransition(
                from_state="processing", to_state="retrying", trigger="retry"
            ),
            ModelFsmTransition(
                from_state="retrying", to_state="processing", trigger="retry_done"
            ),
            ModelFsmTransition(
                from_state="processing", to_state="success", trigger="complete"
            ),
            ModelFsmTransition(
                from_state="processing", to_state="failed", trigger="error"
            ),
        ]

        fsm = ModelFsmData(
            state_machine_name="complex",
            initial_state="start",
            states=states,
            transitions=transitions,
            variables={"retry_count": "0", "max_retries": "3"},
            global_actions=["log", "notify"],
            metadata={"version": "2.0", "complexity": "high"},
        )

        errors = fsm.validate_fsm_structure()
        assert errors == []

        # Test queries on complex FSM
        processing_out = fsm.get_transitions_from_state("processing")
        assert len(processing_out) == 4

        processing_in = fsm.get_transitions_to_state("processing")
        assert len(processing_in) == 3

    def test_empty_variables_and_metadata(self):
        """Test FSM with empty variables and metadata."""
        states = [ModelFsmState(name="s1", is_initial=True, is_final=True)]
        transitions = []

        fsm = ModelFsmData(
            state_machine_name="empty_extra",
            initial_state="s1",
            states=states,
            transitions=transitions,
            variables={},
            global_actions=[],
            metadata={},
        )

        # Deep immutability: empty dict/list become empty tuple
        assert fsm.variables == ()
        assert fsm.global_actions == ()
        assert fsm.metadata == ()

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        data = {
            "state_machine_name": "test",
            "initial_state": "s1",
            "states": [{"name": "s1", "is_initial": True, "is_final": True}],
            "transitions": [],
            "extra_field": "ignored",
        }

        fsm = ModelFsmData.model_validate(data)
        assert not hasattr(fsm, "extra_field")


@pytest.mark.unit
class TestModelFsmDataValidateInstanceFalse:
    """Test validate_instance returning False for invalid states."""

    def test_validate_instance_empty_state_machine_name_returns_false(self):
        """Test validate_instance returns False for empty state_machine_name."""
        data = ModelFsmData(
            state_machine_name="",
            initial_state="idle",
            states=[ModelFsmState(name="idle", is_initial=True, is_final=True)],
            transitions=[],
        )
        assert data.validate_instance() is False

    def test_validate_instance_whitespace_state_machine_name_returns_false(self):
        """Test validate_instance returns False for whitespace-only state_machine_name."""
        data = ModelFsmData(
            state_machine_name="   ",
            initial_state="idle",
            states=[ModelFsmState(name="idle", is_initial=True, is_final=True)],
            transitions=[],
        )
        assert data.validate_instance() is False

    def test_validate_instance_empty_initial_state_returns_false(self):
        """Test validate_instance returns False for empty initial_state."""
        data = ModelFsmData(
            state_machine_name="test_fsm",
            initial_state="",
            states=[ModelFsmState(name="idle", is_initial=True, is_final=True)],
            transitions=[],
        )
        assert data.validate_instance() is False

    def test_validate_instance_whitespace_initial_state_returns_false(self):
        """Test validate_instance returns False for whitespace-only initial_state."""
        data = ModelFsmData(
            state_machine_name="test_fsm",
            initial_state="   ",
            states=[ModelFsmState(name="idle", is_initial=True, is_final=True)],
            transitions=[],
        )
        assert data.validate_instance() is False

    def test_validate_instance_valid_returns_true(self):
        """Test validate_instance returns True for valid data."""
        data = ModelFsmData(
            state_machine_name="test_fsm",
            initial_state="idle",
            states=[ModelFsmState(name="idle", is_initial=True, is_final=True)],
            transitions=[],
        )
        assert data.validate_instance() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
