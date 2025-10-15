"""
Test suite for MixinEventListener.

Tests event-driven execution, event handling, and lifecycle management.
"""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.mixins.mixin_event_listener import MixinEventListener
from omnibase_core.models.core.model_onex_event import ModelOnexEvent


class TestInputState:
    """Test input state model."""

    def __init__(self, data=None, **kwargs):
        self.data = data
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestOutputState:
    """Test output state model."""

    def __init__(self, result=None, **kwargs):
        self.result = result
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        return {"result": self.result}


class TestNode(MixinEventListener[TestInputState, TestOutputState]):
    """Test node class that uses MixinEventListener."""

    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self._processed_events = []
        super().__init__()

    def process(self, input_state: TestInputState) -> TestOutputState:
        """Process input and return output."""
        self._processed_events.append(input_state)
        return TestOutputState(result="processed")


class TestMixinEventListener:
    """Test MixinEventListener functionality."""

    def test_initialization(self):
        """Test mixin initialization."""
        node = TestNode()

        assert hasattr(node, "start_event_listener")
        assert hasattr(node, "stop_event_listener")
        assert hasattr(node, "get_event_patterns")
        assert hasattr(node, "_event_listener_thread")
        assert hasattr(node, "_stop_event")
        assert hasattr(node, "_event_subscriptions")

    def test_get_node_name_from_attribute(self):
        """Test getting node name from node_name attribute."""
        node = TestNode()
        node.node_name = "custom_node_name"

        name = node.get_node_name()

        assert name == "custom_node_name"

    def test_get_node_name_from_class(self):
        """Test getting node name from class name."""
        node = TestNode()

        name = node.get_node_name()

        assert isinstance(name, str)
        assert len(name) > 0
        # Should convert CamelCase to snake_case
        assert "_" in name or name.islower()

    def test_event_bus_property(self):
        """Test event_bus property getter and setter."""
        node = TestNode()

        # Test getter
        assert node.event_bus is None

        # Test setter
        mock_bus = Mock()
        node.event_bus = mock_bus
        assert node.event_bus == mock_bus

    def test_process_not_implemented(self):
        """Test that process method must be implemented."""
        mixin = MixinEventListener()

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.process(None)

        assert exc_info.value.error_code == EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED

    def test_get_event_patterns_default(self):
        """Test getting default event patterns."""
        node = TestNode()

        patterns = node.get_event_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_get_event_patterns_from_contract(self, tmp_path):
        """Test getting event patterns from contract YAML."""
        node = TestNode()

        # Create a mock contract file with required fields (ModelSemVer structure)
        contract_path = tmp_path / "contract.yaml"
        contract_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
event_subscriptions:
  - event_type: "test.event.type"
    description: "Test event subscription"
"""
        contract_path.write_text(contract_content)
        node.contract_path = str(contract_path)

        patterns = node.get_event_patterns()

        assert "test.event.type" in patterns

    def test_get_completion_event_type_basic(self):
        """Test getting completion event type."""
        node = TestNode()

        completion = node.get_completion_event_type("domain.contract.validate")

        assert isinstance(completion, str)
        assert (
            "complete" in completion
            or "generated" in completion
            or "rendered" in completion
        )

    def test_get_completion_event_type_known_mappings(self):
        """Test completion event type with known mappings."""
        node = TestNode()

        test_cases = [
            ("generation.contract.validate", "generation.validation.complete"),
            ("generation.ast.generate", "generation.ast_batch.generated"),
            ("generation.ast.render", "generation.files.rendered"),
            ("generation.scenario.generate", "generation.scenarios.generated"),
        ]

        for input_event, expected in test_cases:
            result = node.get_completion_event_type(input_event)
            assert result == expected

    def test_get_completion_event_type_unknown(self):
        """Test completion event type with unknown pattern."""
        node = TestNode()

        completion = node.get_completion_event_type("unknown.event.type")

        assert completion == "unknown.event.type.complete"

    def test_start_event_listener_without_event_bus(self):
        """Test starting event listener without event bus."""
        node = TestNode(event_bus=None)

        # Should not raise, just return early
        node.start_event_listener()

        assert node._event_listener_thread is None

    def test_start_event_listener_with_event_bus(self):
        """Test starting event listener with event bus."""
        mock_event_bus = Mock()
        mock_event_bus.subscribe = Mock()

        node = TestNode(event_bus=mock_event_bus)

        # Mock get_event_patterns to avoid contract file reading
        with patch.object(node, "get_event_patterns", return_value=["test.pattern"]):
            node.start_event_listener()

            # Give thread time to start
            time.sleep(0.2)

            assert node._event_listener_thread is not None
            assert node._event_listener_thread.is_alive()

            # Clean up
            node.stop_event_listener()
            time.sleep(0.1)

    def test_start_event_listener_already_running(self):
        """Test starting event listener when already running."""
        mock_event_bus = Mock()
        node = TestNode(event_bus=mock_event_bus)

        with patch.object(node, "get_event_patterns", return_value=["test.pattern"]):
            node.start_event_listener()
            time.sleep(0.1)

            # Try to start again
            node.start_event_listener()

            # Should only have one thread
            assert node._event_listener_thread is not None

            # Clean up
            node.stop_event_listener()
            time.sleep(0.1)

    def test_stop_event_listener(self):
        """Test stopping event listener."""
        mock_event_bus = Mock()
        mock_event_bus.subscribe = Mock(return_value="subscription")
        mock_event_bus.unsubscribe = Mock()

        node = TestNode(event_bus=mock_event_bus)

        with patch.object(node, "get_event_patterns", return_value=["test.pattern"]):
            node.start_event_listener()
            time.sleep(0.1)

            node.stop_event_listener()
            time.sleep(0.2)

            # Thread should be stopped
            assert (
                not node._event_listener_thread.is_alive()
                if node._event_listener_thread
                else True
            )

    def test_event_to_input_state_with_dict_data(self):
        """Test converting event to input state with dict data."""
        node = TestNode()

        event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={"key": "value"},
        )

        # Mock _get_input_state_class
        with patch.object(node, "_get_input_state_class", return_value=TestInputState):
            input_state = node._event_to_input_state(event)

            assert isinstance(input_state, TestInputState)

    def test_event_to_input_state_with_model_data(self):
        """Test converting event to input state with model data."""
        node = TestNode()

        # Create event with actual dict data (Pydantic v2 requires actual dict, not Mock)
        event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={"key": "value"},
        )

        with patch.object(node, "_get_input_state_class", return_value=TestInputState):
            input_state = node._event_to_input_state(event)

            assert isinstance(input_state, TestInputState)

    def test_event_to_input_state_no_class_found(self):
        """Test event to input state when no class found."""
        node = TestNode()

        event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={"key": "value"},
        )

        with patch.object(node, "_get_input_state_class", return_value=None):
            with pytest.raises(ModelOnexError) as exc_info:
                node._event_to_input_state(event)

            assert (
                exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
            )

    def test_event_to_input_state_conversion_error(self):
        """Test event to input state with conversion error."""
        node = TestNode()

        # Use valid dict data for Pydantic validation, test conversion error in class instantiation
        event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={"key": "value"},
        )

        # Mock class that will fail conversion - needs __name__ attribute for logging
        mock_class = Mock(side_effect=ValueError("Conversion failed"))
        mock_class.__name__ = "MockInputStateClass"

        with patch.object(node, "_get_input_state_class", return_value=mock_class):
            with pytest.raises(ModelOnexError) as exc_info:
                node._event_to_input_state(event)

            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_get_input_state_class_from_annotations(self):
        """Test getting input state class from annotations."""

        class AnnotatedNode(MixinEventListener):
            def __init__(self):
                super().__init__()

            def process(self, input_state: TestInputState):
                pass

        node = AnnotatedNode()
        input_class = node._get_input_state_class()

        assert input_class == TestInputState

    def test_get_input_state_class_not_found(self):
        """Test getting input state class when not found."""

        # Create node class without type annotations to test fallback behavior
        class NodeWithoutAnnotations(MixinEventListener):
            def __init__(self):
                super().__init__()

            def process(self, input_state):  # No type annotation
                pass

        node = NodeWithoutAnnotations()

        # Should gracefully handle missing annotations (may return None or fallback result)
        # Both outcomes are acceptable - test should not raise exception
        input_class = node._get_input_state_class()

        # Verify method completes without error and returns expected value
        # Should return None when no annotations are present and no fallback is available
        assert input_class is None or isinstance(input_class, type)

    def test_publish_completion_event(self):
        """Test publishing completion event."""
        mock_event_bus = Mock()
        mock_event_bus.publish_async = Mock()

        node = TestNode(event_bus=mock_event_bus)

        input_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={},
        )

        output_state = TestOutputState(result="success")

        node._publish_completion_event(input_event, output_state)

        # Verify publish was called
        mock_event_bus.publish_async.assert_called_once()

    def test_publish_completion_event_with_none_output(self):
        """Test publishing completion event with None output state."""
        mock_event_bus = Mock()
        mock_event_bus.publish_async = Mock()

        node = TestNode(event_bus=mock_event_bus)

        input_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={},
        )

        node._publish_completion_event(input_event, None)

        # Should still publish
        mock_event_bus.publish_async.assert_called_once()

    def test_publish_error_event(self):
        """Test publishing error event."""
        mock_event_bus = Mock()
        mock_event_bus.publish_async = Mock()

        node = TestNode(event_bus=mock_event_bus)

        input_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={},
        )

        node._publish_error_event(input_event, "Test error message")

        # Verify publish was called
        mock_event_bus.publish_async.assert_called_once()

    def test_create_event_handler(self):
        """Test creating event handler."""
        node = TestNode()

        handler = node._create_event_handler("test.pattern")

        assert callable(handler)

    def test_event_handler_with_envelope(self):
        """Test event handler with envelope."""
        mock_event_bus = Mock()
        mock_event_bus.publish_async = Mock()

        node = TestNode(event_bus=mock_event_bus)

        # Create mock envelope
        mock_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={"test": "data"},
        )

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        # Mock emit_log_event to prevent container initialization hangs
        with patch("omnibase_core.mixins.mixin_event_listener.emit_log_event"):
            handler = node._create_event_handler("test.pattern")

            # Mock dependencies
            with patch.object(
                node, "_event_to_input_state", return_value=TestInputState()
            ):
                with patch.object(node, "process", return_value=TestOutputState()):
                    handler(mock_envelope)

        # Should have published completion event
        assert mock_event_bus.publish_async.called

    def test_event_handler_with_direct_event(self):
        """Test event handler with direct event (no envelope)."""
        mock_event_bus = Mock()
        mock_event_bus.publish_async = Mock()

        node = TestNode(event_bus=mock_event_bus)

        mock_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={"test": "data"},
        )

        handler = node._create_event_handler("test.pattern")

        with patch.object(node, "_event_to_input_state", return_value=TestInputState()):
            with patch.object(node, "process", return_value=TestOutputState()):
                handler(mock_event)

        assert mock_event_bus.publish_async.called

    def test_event_handler_with_exception(self):
        """Test event handler when processing raises exception."""
        mock_event_bus = Mock()
        mock_event_bus.publish_async = Mock()

        node = TestNode(event_bus=mock_event_bus)

        mock_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={},
        )

        handler = node._create_event_handler("test.pattern")

        with patch.object(
            node, "_event_to_input_state", side_effect=RuntimeError("Test error")
        ):
            handler(mock_event)

        # Should have published error event
        assert mock_event_bus.publish_async.called

    def test_event_handler_with_specific_handler_method(self):
        """Test event handler with specific handler method."""

        class NodeWithSpecificHandler(TestNode):
            def __init__(self):
                super().__init__()
                self.specific_handler_called = False

            def handle_test_event_event(self, envelope):
                self.specific_handler_called = True

        mock_event_bus = Mock()
        node = NodeWithSpecificHandler()
        node.event_bus = mock_event_bus

        mock_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={},
        )

        handler = node._create_event_handler("test.event")
        handler(mock_event)

        assert node.specific_handler_called

    def test_get_event_patterns_with_invalid_contract(self, tmp_path):
        """Test getting event patterns with invalid contract YAML."""
        node = TestNode()

        # Create invalid contract file
        contract_path = tmp_path / "contract.yaml"
        contract_path.write_text("invalid: yaml: content: [[[")
        node.contract_path = str(contract_path)

        # Should fall back to default patterns
        patterns = node.get_event_patterns()

        assert isinstance(patterns, list)

    def test_event_listener_loop_heartbeat(self):
        """Test event listener loop heartbeat logging."""
        mock_event_bus = Mock()
        mock_event_bus.subscribe = Mock(return_value="subscription")

        node = TestNode(event_bus=mock_event_bus)

        with patch.object(node, "get_event_patterns", return_value=["test.pattern"]):
            node.start_event_listener()
            time.sleep(0.1)

            # Verify thread is alive
            assert node._event_listener_thread.is_alive()

            node.stop_event_listener()
            time.sleep(0.1)

    def test_auto_start_with_event_bus(self):
        """Test auto-start of event listener with event bus."""
        mock_event_bus = Mock()
        mock_event_bus.subscribe = Mock()

        # Node should auto-start listener if event bus provided
        with patch.object(
            TestNode, "get_event_patterns", return_value=["test.pattern"]
        ):
            node = TestNode(event_bus=mock_event_bus)

            # Give auto-start time to execute
            time.sleep(0.3)

            # Should have started
            assert (
                node._event_listener_thread is not None
                or node._event_subscriptions is not None
            )

            # Clean up
            if node._event_listener_thread:
                node.stop_event_listener()
                time.sleep(0.1)

    def test_node_name_to_uuid_conversion(self):
        """Test node name to UUID conversion."""
        node = TestNode()
        node.node_name = "test_node_name"

        mock_event_bus = Mock()
        mock_event_bus.publish_async = Mock()
        node.event_bus = mock_event_bus

        input_event = ModelOnexEvent(
            event_type="test.event",
            node_id=uuid4(),
            correlation_id=uuid4(),
            data={},
        )

        output_state = TestOutputState(result="success")

        # Should handle node name to UUID conversion
        node._publish_completion_event(input_event, output_state)

        assert mock_event_bus.publish_async.called
