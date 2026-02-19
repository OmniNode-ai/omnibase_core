# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for MixinContractStateReducer.

Tests the contract-driven state reducer mixin, specifically:
- Null/None action handling
- Action name extraction edge cases
- State transition processing
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit

from omnibase_core.mixins.mixin_contract_state_reducer import MixinContractStateReducer


class TestNode(MixinContractStateReducer):
    """Test node class using contract state reducer mixin."""

    def __init__(self, node_name: str = "test_node") -> None:
        """Initialize test node."""
        super().__init__()
        self.node_name = node_name
        # Track log events for assertions
        self.logged_events: list[dict[str, Any]] = []


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def test_node() -> TestNode:
    """Create test node fixture."""
    return TestNode()


@pytest.fixture
def mock_transitions() -> list[MagicMock]:
    """Create mock state transitions."""
    transition = MagicMock()
    transition.triggers = ["test_action"]
    transition.priority = 1
    return [transition]


# =============================================================================
# TEST CLASSES
# =============================================================================


@pytest.mark.unit
class TestProcessActionWithTransitionsNullHandling:
    """Test null/None action handling in process_action_with_transitions."""

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_none_input_state_uses_unknown_action(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that None input_state results in action_name='unknown_action'.

        This tests the defensive None check at lines 184-188.
        """
        mock_load_transitions.return_value = []

        # Process with None input
        result = test_node.process_action_with_transitions(None)

        # Verify unknown_action was used in logging
        mock_emit_log.assert_any_call(
            pytest.approx(mock_emit_log.call_args_list[0][0][0], rel=0.1),  # LogLevel
            "Processing action with contract transitions: unknown_action",
            {"tool_name": "test_node", "action": "unknown_action"},
        )

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_input_state_without_action_attribute(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that input_state without action attribute uses unknown_action.

        This tests getattr(input_state, "action", None) returning None.
        """
        mock_load_transitions.return_value = []

        # Create input without action attribute
        class InputWithoutAction:
            pass

        result = test_node.process_action_with_transitions(InputWithoutAction())

        # Should use unknown_action
        log_calls = list(mock_emit_log.call_args_list)
        assert any("unknown_action" in str(call) for call in log_calls), (
            f"Expected 'unknown_action' in log calls: {log_calls}"
        )

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_action_without_action_name_attribute(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that action without action_name attribute uses unknown_action.

        This tests getattr(action, "action_name", None) returning None.
        """
        mock_load_transitions.return_value = []

        # Create input with action but no action_name
        class ActionWithoutName:
            pass

        class InputWithAction:
            def __init__(self) -> None:
                self.action = ActionWithoutName()

        result = test_node.process_action_with_transitions(InputWithAction())

        # Should use unknown_action
        log_calls = list(mock_emit_log.call_args_list)
        assert any("unknown_action" in str(call) for call in log_calls), (
            f"Expected 'unknown_action' in log calls: {log_calls}"
        )

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_action_name_not_string_uses_unknown_action(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that non-string action_name uses unknown_action.

        This tests isinstance(raw_action_name, str) check returning False.
        """
        mock_load_transitions.return_value = []

        # Create input with non-string action_name
        class ActionWithIntName:
            action_name = 123  # Not a string

        class InputWithIntAction:
            def __init__(self) -> None:
                self.action = ActionWithIntName()

        result = test_node.process_action_with_transitions(InputWithIntAction())

        # Should use unknown_action since action_name is not string
        log_calls = list(mock_emit_log.call_args_list)
        assert any("unknown_action" in str(call) for call in log_calls), (
            f"Expected 'unknown_action' in log calls: {log_calls}"
        )

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_empty_action_name_uses_unknown_action(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that empty string action_name uses unknown_action.

        This tests the truthy check: raw_action_name (empty string is falsy).
        """
        mock_load_transitions.return_value = []

        # Create input with empty action_name
        class ActionWithEmptyName:
            action_name = ""

        class InputWithEmptyAction:
            def __init__(self) -> None:
                self.action = ActionWithEmptyName()

        result = test_node.process_action_with_transitions(InputWithEmptyAction())

        # Should use unknown_action since action_name is empty
        log_calls = list(mock_emit_log.call_args_list)
        assert any("unknown_action" in str(call) for call in log_calls), (
            f"Expected 'unknown_action' in log calls: {log_calls}"
        )

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_valid_action_name_is_used(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that valid action_name is properly extracted and used."""
        mock_load_transitions.return_value = []

        # Create input with valid action_name
        class ValidAction:
            action_name = "submit_form"

        class InputWithValidAction:
            def __init__(self) -> None:
                self.action = ValidAction()

        result = test_node.process_action_with_transitions(InputWithValidAction())

        # Should use the actual action_name
        log_calls = list(mock_emit_log.call_args_list)
        assert any("submit_form" in str(call) for call in log_calls), (
            f"Expected 'submit_form' in log calls: {log_calls}"
        )

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_action_none_explicitly(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that explicit None action uses unknown_action."""
        mock_load_transitions.return_value = []

        # Create input with explicit None action
        class InputWithNoneAction:
            action = None

        result = test_node.process_action_with_transitions(InputWithNoneAction())

        # Should use unknown_action
        log_calls = list(mock_emit_log.call_args_list)
        assert any("unknown_action" in str(call) for call in log_calls), (
            f"Expected 'unknown_action' in log calls: {log_calls}"
        )


@pytest.mark.unit
class TestProcessActionWithTransitionsDefaultOutput:
    """Test default output state creation."""

    @patch.object(MixinContractStateReducer, "_load_state_transitions")
    @patch("omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event")
    def test_creates_default_output_when_no_main_logic(
        self,
        mock_emit_log: MagicMock,
        mock_load_transitions: MagicMock,
        test_node: TestNode,
    ) -> None:
        """Test that default output is created when _process_main_logic not defined."""
        mock_load_transitions.return_value = []

        # Process with None input - should create default output
        result = test_node.process_action_with_transitions(None)

        # Result should be a dict with expected fields (from _create_default_output_state)
        assert result is not None
        assert isinstance(result, dict)
        assert "status" in result


@pytest.mark.unit
class TestLoadStateTransitions:
    """Test _load_state_transitions method."""

    def test_returns_empty_list_when_no_tool_directory(
        self, test_node: TestNode
    ) -> None:
        """Test that missing tool directory returns empty list gracefully."""
        # Set a tool name that won't exist
        test_node.node_name = "nonexistent_tool_xyz"

        with patch(
            "omnibase_core.mixins.mixin_contract_state_reducer.emit_log_event"
        ) as mock_log:
            result = test_node._load_state_transitions()

        assert result == []
        assert test_node._transitions_loaded is True

    def test_caches_loaded_transitions(self, test_node: TestNode) -> None:
        """Test that transitions are cached after first load."""
        test_node.node_name = "nonexistent_tool"

        # First load
        result1 = test_node._load_state_transitions()

        # Mark as if we had transitions
        test_node._state_transitions = [MagicMock()]
        test_node._transitions_loaded = True

        # Second load should return cached
        result2 = test_node._load_state_transitions()

        # Should return cached transitions, not empty list
        assert len(result2) == 1
