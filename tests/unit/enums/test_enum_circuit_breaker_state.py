"""Unit tests for EnumCircuitBreakerState."""

import pytest

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState


@pytest.mark.unit
class TestEnumCircuitBreakerState:
    """Test suite for EnumCircuitBreakerState enumeration."""

    def test_enum_values(self) -> None:
        """Test that all circuit breaker states are defined."""
        assert EnumCircuitBreakerState.CLOSED.value == "closed"
        assert EnumCircuitBreakerState.OPEN.value == "open"
        assert EnumCircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 3 members."""
        members = list(EnumCircuitBreakerState)
        assert len(members) == 3

    def test_closed_state(self) -> None:
        """Test CLOSED state represents normal operation."""
        assert EnumCircuitBreakerState.CLOSED.value == "closed"

    def test_open_state(self) -> None:
        """Test OPEN state represents failing/rejecting requests."""
        assert EnumCircuitBreakerState.OPEN.value == "open"

    def test_half_open_state(self) -> None:
        """Test HALF_OPEN state represents testing recovery."""
        assert EnumCircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        state1 = EnumCircuitBreakerState.CLOSED
        state2 = EnumCircuitBreakerState.CLOSED
        state3 = EnumCircuitBreakerState.OPEN

        assert state1 == state2
        assert state1 != state3
        assert state1 is state2

    def test_enum_in_collection(self) -> None:
        """Test enum usage in collections."""
        states = {EnumCircuitBreakerState.CLOSED, EnumCircuitBreakerState.HALF_OPEN}
        assert EnumCircuitBreakerState.CLOSED in states
        assert EnumCircuitBreakerState.OPEN not in states

    def test_enum_iteration(self) -> None:
        """Test iterating over enum members."""
        states = list(EnumCircuitBreakerState)
        assert EnumCircuitBreakerState.CLOSED in states
        assert EnumCircuitBreakerState.OPEN in states
        assert EnumCircuitBreakerState.HALF_OPEN in states
        assert len(states) == 3

    def test_enum_membership_check(self) -> None:
        """Test membership checks."""
        assert "closed" in [e.value for e in EnumCircuitBreakerState]
        assert "invalid" not in [e.value for e in EnumCircuitBreakerState]

    def test_enum_string_representation(self) -> None:
        """Test string representation."""
        assert str(EnumCircuitBreakerState.OPEN) == "EnumCircuitBreakerState.OPEN"
        assert (
            repr(EnumCircuitBreakerState.HALF_OPEN)
            == "<EnumCircuitBreakerState.HALF_OPEN: 'half_open'>"
        )

    def test_enum_value_uniqueness(self) -> None:
        """Test that all enum values are unique."""
        values = [e.value for e in EnumCircuitBreakerState]
        assert len(values) == len(set(values))

    def test_state_transitions(self) -> None:
        """Test typical state transition scenario."""
        # Normal flow: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
        states_sequence = [
            EnumCircuitBreakerState.CLOSED,
            EnumCircuitBreakerState.OPEN,
            EnumCircuitBreakerState.HALF_OPEN,
            EnumCircuitBreakerState.CLOSED,
        ]
        assert len(states_sequence) == 4
        assert states_sequence[0] == EnumCircuitBreakerState.CLOSED
        assert states_sequence[-1] == EnumCircuitBreakerState.CLOSED

    def test_enum_as_dict_key(self) -> None:
        """Test using enum as dictionary key."""
        state_config = {
            EnumCircuitBreakerState.CLOSED: {"max_failures": 5},
            EnumCircuitBreakerState.OPEN: {"timeout": 30},
            EnumCircuitBreakerState.HALF_OPEN: {"test_requests": 3},
        }
        assert state_config[EnumCircuitBreakerState.CLOSED]["max_failures"] == 5

    def test_enum_in_conditional(self) -> None:
        """Test using enum in conditional statements."""
        current_state = EnumCircuitBreakerState.OPEN

        if current_state == EnumCircuitBreakerState.CLOSED:
            result = "normal"
        elif current_state == EnumCircuitBreakerState.OPEN:
            result = "failing"
        elif current_state == EnumCircuitBreakerState.HALF_OPEN:
            result = "testing"
        else:
            result = "unknown"

        assert result == "failing"

    def test_enum_name_attribute(self) -> None:
        """Test enum name attribute."""
        assert EnumCircuitBreakerState.CLOSED.name == "CLOSED"
        assert EnumCircuitBreakerState.OPEN.name == "OPEN"
        assert EnumCircuitBreakerState.HALF_OPEN.name == "HALF_OPEN"
