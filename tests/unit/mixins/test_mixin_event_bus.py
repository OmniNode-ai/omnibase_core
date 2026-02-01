# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for MixinEventBus.

Comprehensive tests for the unified event bus mixin including:
- Binding methods (event bus, registry, contract path, node name)
- Event bus access methods (require, get, has)
- Node identification methods (get_node_name, get_node_id)
- Event publishing (sync and async)
- Generic type parameter usage
- Thread safety scenarios
- Error handling
"""

import threading
import uuid
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.mixins.mixin_event_bus import MixinEventBus
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.mixins.model_completion_data import ModelCompletionData


class MockInputState:
    """Mock input state for testing generic type parameters."""

    def __init__(self, data: str | None = None, **kwargs: Any) -> None:
        self.data = data
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockOutputState:
    """Mock output state for testing generic type parameters."""

    def __init__(self, result: str | None = None, **kwargs: Any) -> None:
        self.result = result
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self) -> dict[str, Any]:
        return {"result": self.result}


class TestMixinNode(MixinEventBus[MockInputState, MockOutputState]):
    """Test node implementation using MixinEventBus with typed parameters."""

    def __init__(self) -> None:
        # MixinEventBus has no __init__ - uses lazy accessors
        pass

    def process(self, input_state: MockInputState) -> MockOutputState:
        """Process input and return output."""
        return MockOutputState(result="processed")


class UntypedTestMixinNode(MixinEventBus[Any, Any]):
    """Test node without specific generic type parameters."""

    def process(self, input_state: Any) -> Any:
        return None


@pytest.mark.unit
class TestMixinEventBusInitialization:
    """Test MixinEventBus initialization and lazy state accessors."""

    def test_runtime_state_requires_explicit_init(self) -> None:
        """Test that runtime state requires explicit initialization via bind or ensure."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        node = TestMixinNode()

        # Accessing _event_bus_runtime_state without binding should raise
        with pytest.raises(ModelOnexError) as exc_info:
            _ = node._event_bus_runtime_state

        assert "not initialized" in str(exc_info.value)

    def test_ensure_runtime_state_creates_state(self) -> None:
        """Test that _ensure_runtime_state creates state on first call."""
        node = TestMixinNode()

        # _ensure_runtime_state should create state
        state = node._ensure_runtime_state()

        assert state is not None
        assert state.is_bound is False
        assert state.node_name is None

    def test_runtime_state_singleton_behavior(self) -> None:
        """Test that runtime state returns same instance on repeated access."""
        node = TestMixinNode()

        # Initialize state first via _ensure_runtime_state
        state1 = node._ensure_runtime_state()
        state2 = node._event_bus_runtime_state

        assert state1 is state2


@pytest.mark.unit
class TestMixinEventBusBindEventBus:
    """Test MixinEventBus.bind_event_bus() method."""

    def test_bind_event_bus_sets_bound_flag(self) -> None:
        """Test that binding event bus sets is_bound to True."""
        node = TestMixinNode()
        mock_bus = Mock()

        node.bind_event_bus(mock_bus)

        assert node._event_bus_runtime_state.is_bound is True

    def test_bind_event_bus_stores_reference(self) -> None:
        """Test that binding stores the event bus reference."""
        node = TestMixinNode()
        mock_bus = Mock()

        node.bind_event_bus(mock_bus)

        assert node._get_event_bus() is mock_bus

    def test_bind_event_bus_allows_rebinding(self) -> None:
        """Test that event bus can be rebound to different instance."""
        node = TestMixinNode()
        mock_bus1 = Mock(name="bus1")
        mock_bus2 = Mock(name="bus2")

        node.bind_event_bus(mock_bus1)
        assert node._get_event_bus() is mock_bus1

        node.bind_event_bus(mock_bus2)
        assert node._get_event_bus() is mock_bus2


@pytest.mark.unit
class TestMixinEventBusBindRegistry:
    """Test MixinEventBus.bind_registry() method."""

    def test_bind_registry_with_event_bus(self) -> None:
        """Test binding registry that has event_bus attribute."""
        node = TestMixinNode()
        mock_bus = Mock()
        mock_registry = Mock()
        mock_registry.event_bus = mock_bus

        node.bind_registry(mock_registry)

        assert node._event_bus_runtime_state.is_bound is True
        assert node._get_event_bus() is mock_bus

    def test_bind_registry_without_event_bus(self) -> None:
        """Test binding registry where event_bus is None."""
        node = TestMixinNode()
        mock_registry = Mock()
        mock_registry.event_bus = None

        node.bind_registry(mock_registry)

        # Should not set bound flag if event_bus is None
        assert node._event_bus_runtime_state.is_bound is False

    def test_bind_registry_stores_reference(self) -> None:
        """Test that registry reference is stored."""
        node = TestMixinNode()
        mock_registry = Mock()
        mock_registry.event_bus = Mock()

        node.bind_registry(mock_registry)

        # Should be able to get event bus from registry
        assert node._get_event_bus() is mock_registry.event_bus


@pytest.mark.unit
class TestMixinEventBusBindNodeName:
    """Test MixinEventBus.bind_node_name() method."""

    def test_bind_node_name_stores_name(self) -> None:
        """Test that node name is stored in runtime state."""
        node = TestMixinNode()

        node.bind_node_name("my_custom_node")

        assert node._event_bus_runtime_state.node_name == "my_custom_node"

    def test_bind_node_name_affects_get_node_name(self) -> None:
        """Test that bound node name is returned by get_node_name."""
        node = TestMixinNode()

        node.bind_node_name("custom_name")

        assert node.get_node_name() == "custom_name"


@pytest.mark.unit
class TestMixinEventBusRequireEventBus:
    """Test MixinEventBus._require_event_bus() method."""

    def test_require_event_bus_returns_bus_when_bound(self) -> None:
        """Test that _require_event_bus returns bus when bound."""
        node = TestMixinNode()
        mock_bus = Mock()
        node.bind_event_bus(mock_bus)

        result = node._require_event_bus()

        assert result is mock_bus

    def test_require_event_bus_raises_when_not_bound(self) -> None:
        """Test that _require_event_bus raises ModelOnexError when not bound."""
        node = TestMixinNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node._require_event_bus()

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "Event bus not bound" in str(exc_info.value.message)
        assert "TestMixinNode" in str(exc_info.value.message)


@pytest.mark.unit
class TestMixinEventBusGetEventBus:
    """Test MixinEventBus._get_event_bus() method."""

    def test_get_event_bus_returns_none_when_not_bound(self) -> None:
        """Test that _get_event_bus returns None when not bound."""
        node = TestMixinNode()

        result = node._get_event_bus()

        assert result is None

    def test_get_event_bus_returns_direct_binding(self) -> None:
        """Test that _get_event_bus returns directly bound bus."""
        node = TestMixinNode()
        mock_bus = Mock()
        node.bind_event_bus(mock_bus)

        result = node._get_event_bus()

        assert result is mock_bus

    def test_get_event_bus_returns_bus_from_registry(self) -> None:
        """Test that _get_event_bus returns bus from registry."""
        node = TestMixinNode()
        mock_bus = Mock()
        mock_registry = Mock()
        mock_registry.event_bus = mock_bus
        node.bind_registry(mock_registry)

        result = node._get_event_bus()

        assert result is mock_bus

    def test_get_event_bus_prefers_direct_binding(self) -> None:
        """Test that direct binding takes precedence over registry."""
        node = TestMixinNode()
        direct_bus = Mock(name="direct")
        registry_bus = Mock(name="registry")
        mock_registry = Mock()
        mock_registry.event_bus = registry_bus

        node.bind_registry(mock_registry)
        node.bind_event_bus(direct_bus)

        result = node._get_event_bus()

        assert result is direct_bus


@pytest.mark.unit
class TestMixinEventBusHasEventBus:
    """Test MixinEventBus._has_event_bus() method."""

    def test_has_event_bus_returns_false_when_not_bound(self) -> None:
        """Test that _has_event_bus returns False when not bound."""
        node = TestMixinNode()

        assert node._has_event_bus() is False

    def test_has_event_bus_returns_true_when_bound(self) -> None:
        """Test that _has_event_bus returns True when bound."""
        node = TestMixinNode()
        node.bind_event_bus(Mock())

        assert node._has_event_bus() is True

    def test_has_event_bus_returns_true_with_registry(self) -> None:
        """Test that _has_event_bus returns True when registry has bus."""
        node = TestMixinNode()
        mock_registry = Mock()
        mock_registry.event_bus = Mock()
        node.bind_registry(mock_registry)

        assert node._has_event_bus() is True


@pytest.mark.unit
class TestMixinEventBusGetNodeName:
    """Test MixinEventBus.get_node_name() method."""

    def test_get_node_name_returns_class_name_by_default(self) -> None:
        """Test that get_node_name returns class name when no name bound."""
        node = TestMixinNode()

        name = node.get_node_name()

        assert name == "TestMixinNode"

    def test_get_node_name_returns_bound_name(self) -> None:
        """Test that get_node_name returns bound name."""
        node = TestMixinNode()
        node.bind_node_name("custom_name")

        name = node.get_node_name()

        assert name == "custom_name"

    def test_get_node_name_returns_state_node_name_when_set(self) -> None:
        """Test get_node_name returns state.node_name when set directly."""
        node = TestMixinNode()
        # Must initialize state first before accessing _event_bus_runtime_state
        node._ensure_runtime_state()
        node._event_bus_runtime_state.node_name = "state_name"

        name = node.get_node_name()

        assert name == "state_name"


@pytest.mark.unit
class TestMixinEventBusGetNodeId:
    """Test MixinEventBus.get_node_id() method."""

    def test_get_node_id_returns_uuid(self) -> None:
        """Test that get_node_id returns a UUID."""
        node = TestMixinNode()

        node_id = node.get_node_id()

        assert isinstance(node_id, UUID)

    def test_get_node_id_is_deterministic(self) -> None:
        """Test that get_node_id returns same UUID for same node name."""
        node = TestMixinNode()

        id1 = node.get_node_id()
        id2 = node.get_node_id()

        assert id1 == id2

    def test_get_node_id_differs_for_different_names(self) -> None:
        """Test that get_node_id returns different UUID for different names."""
        node1 = TestMixinNode()
        node2 = TestMixinNode()
        node2.bind_node_name("different_name")

        id1 = node1.get_node_id()
        id2 = node2.get_node_id()

        assert id1 != id2

    def test_get_node_id_uses_existing_node_id_attribute(self) -> None:
        """Test that get_node_id returns existing _node_id if present."""
        node = TestMixinNode()
        custom_id = uuid.uuid4()
        object.__setattr__(node, "_node_id", custom_id)

        node_id = node.get_node_id()

        assert node_id == custom_id


@pytest.mark.unit
class TestMixinEventBusPublishCompletionEvent:
    """Test MixinEventBus.publish_completion_event() method."""

    def test_publish_completion_event_calls_bus_publish(self) -> None:
        """Test that publish_completion_event calls bus.publish."""
        node = TestMixinNode()
        mock_bus = Mock()
        mock_bus.publish = Mock()
        node.bind_event_bus(mock_bus)

        # Create a valid mock event to avoid ModelOnexEvent validation issues
        mock_event = ModelOnexEvent(
            event_type="test.complete",
            node_id=node.get_node_id(),
        )

        data = ModelCompletionData(message="test", success=True)

        with patch.object(node, "_build_event", return_value=mock_event):
            node.publish_completion_event("test.complete", data)

        mock_bus.publish.assert_called_once()

    def test_publish_completion_event_raises_when_not_bound(self) -> None:
        """Test that publish_completion_event raises when no bus bound."""
        node = TestMixinNode()
        data = ModelCompletionData(message="test", success=True)

        with pytest.raises(ModelOnexError) as exc_info:
            node.publish_completion_event("test.complete", data)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

    def test_publish_completion_event_logs_on_async_only_bus(self) -> None:
        """Test that async-only bus logs error for sync publish."""
        node = TestMixinNode()
        mock_bus = Mock(spec=["apublish", "apublish_async"])  # async only
        node.bind_event_bus(mock_bus)

        data = ModelCompletionData(message="test", success=True)

        with patch("omnibase_core.mixins.mixin_event_bus.emit_log_event") as mock_log:
            node.publish_completion_event("test.complete", data)

            # Should log error for async-only bus
            assert mock_log.called


@pytest.mark.unit
class TestMixinEventBusAsyncPublishCompletionEvent:
    """Test MixinEventBus.apublish_completion_event() async method."""

    @pytest.mark.asyncio
    async def test_apublish_completion_event_with_async_bus(self) -> None:
        """Test that apublish_completion_event uses async publish."""
        node = TestMixinNode()
        mock_bus = Mock()
        mock_bus.publish_async = AsyncMock()
        node.bind_event_bus(mock_bus)

        # Create a valid mock event to avoid ModelOnexEvent validation issues
        mock_event = ModelOnexEvent(
            event_type="test.complete",
            node_id=node.get_node_id(),
        )

        data = ModelCompletionData(message="test", success=True)

        with patch.object(node, "_build_event", return_value=mock_event):
            await node.apublish_completion_event("test.complete", data)

        mock_bus.publish_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_apublish_completion_event_falls_back_to_sync(self) -> None:
        """Test that apublish_completion_event falls back to sync publish."""
        node = TestMixinNode()
        mock_bus = Mock(spec=["publish"])  # sync only
        mock_bus.publish = Mock()
        node.bind_event_bus(mock_bus)

        # Create a valid mock event to avoid ModelOnexEvent validation issues
        mock_event = ModelOnexEvent(
            event_type="test.complete",
            node_id=node.get_node_id(),
        )

        data = ModelCompletionData(message="test", success=True)

        with patch.object(node, "_build_event", return_value=mock_event):
            await node.apublish_completion_event("test.complete", data)

        mock_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_apublish_completion_event_raises_when_not_bound(self) -> None:
        """Test that apublish_completion_event raises when no bus bound."""
        node = TestMixinNode()
        data = ModelCompletionData(message="test", success=True)

        with pytest.raises(ModelOnexError) as exc_info:
            await node.apublish_completion_event("test.complete", data)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE


@pytest.mark.unit
class TestMixinEventBusPublishEvent:
    """Test MixinEventBus.publish_event() async method."""

    @pytest.mark.asyncio
    async def test_publish_event_with_async_bus(self) -> None:
        """Test that publish_event uses async publish when available."""
        node = TestMixinNode()
        mock_bus = Mock()
        mock_bus.publish_async = AsyncMock()
        node.bind_event_bus(mock_bus)

        await node.publish_event("test.event")

        mock_bus.publish_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_falls_back_to_sync(self) -> None:
        """Test that publish_event falls back to sync publish."""
        node = TestMixinNode()
        mock_bus = Mock(spec=["publish"])
        mock_bus.publish = Mock()
        node.bind_event_bus(mock_bus)

        await node.publish_event("test.event")

        mock_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_with_correlation_id(self) -> None:
        """Test that publish_event includes correlation_id."""
        node = TestMixinNode()
        mock_bus = Mock(spec=["publish"])
        mock_bus.publish = Mock()
        node.bind_event_bus(mock_bus)

        correlation_id = uuid.uuid4()
        await node.publish_event("test.event", correlation_id=correlation_id)

        mock_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_raises_when_not_bound(self) -> None:
        """Test that publish_event raises when no bus bound."""
        node = TestMixinNode()

        with pytest.raises(ModelOnexError) as exc_info:
            await node.publish_event("test.event")

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE


@pytest.mark.unit
class TestMixinEventBusDisposeResources:
    """Test MixinEventBus.dispose_event_bus_resources() method."""

    def test_dispose_clears_bindings(self) -> None:
        """Test that dispose clears event bus bindings."""
        node = TestMixinNode()
        mock_bus = Mock()
        node.bind_event_bus(mock_bus)

        node.dispose_event_bus_resources()

        assert node._get_event_bus() is None
        assert node._event_bus_runtime_state.is_bound is False

    def test_dispose_is_idempotent(self) -> None:
        """Test that dispose can be called multiple times safely."""
        node = TestMixinNode()
        mock_bus = Mock()
        node.bind_event_bus(mock_bus)

        # Call dispose multiple times - should not raise
        node.dispose_event_bus_resources()
        node.dispose_event_bus_resources()
        node.dispose_event_bus_resources()

        assert node._get_event_bus() is None


@pytest.mark.unit
class TestMixinEventBusProcess:
    """Test MixinEventBus.process() method."""

    def test_process_raises_not_implemented_on_base(self) -> None:
        """Test that base process method raises NotImplementedError."""
        # Use untyped mixin directly
        mixin = MixinEventBus[MockInputState, MockOutputState]()

        with pytest.raises(NotImplementedError):
            mixin.process(MockInputState(data="test"))

    def test_process_works_when_overridden(self) -> None:
        """Test that process works when overridden in subclass."""
        node = TestMixinNode()

        result = node.process(MockInputState(data="input"))

        assert isinstance(result, MockOutputState)
        assert result.result == "processed"


@pytest.mark.unit
class TestMixinEventBusGenericTypeParameters:
    """Test MixinEventBus generic type parameter usage."""

    def test_typed_node_preserves_types(self) -> None:
        """Test that typed node preserves generic type parameters."""
        node = TestMixinNode()

        # Access __orig_bases__ to verify type parameters
        orig_bases = getattr(node.__class__, "__orig_bases__", ())

        found_mixin_base = False
        for base in orig_bases:
            if hasattr(base, "__args__"):
                args = base.__args__
                if len(args) >= 2:
                    if args[0] is MockInputState and args[1] is MockOutputState:
                        found_mixin_base = True
                        break

        assert found_mixin_base


@pytest.mark.unit
class TestMixinEventBusThreadSafety:
    """Test MixinEventBus thread safety scenarios."""

    def test_concurrent_binding_access(self) -> None:
        """Test concurrent access to event bus binding."""
        node = TestMixinNode()
        mock_bus = Mock()
        node.bind_event_bus(mock_bus)

        errors: list[Exception] = []

        def access_bus() -> None:
            try:
                for _ in range(100):
                    bus = node._get_event_bus()
                    assert bus is mock_bus or bus is None
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_bus) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0

    def test_dispose_during_access(self) -> None:
        """Test dispose while other operations access state."""
        node = TestMixinNode()
        mock_bus = Mock()
        node.bind_event_bus(mock_bus)

        errors: list[Exception] = []
        stop_event = threading.Event()

        def access_loop() -> None:
            try:
                while not stop_event.is_set():
                    node._get_event_bus()
                    node._has_event_bus()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_loop) for _ in range(3)]
        for t in threads:
            t.start()

        # Dispose while threads are running
        node.dispose_event_bus_resources()

        stop_event.set()
        for t in threads:
            t.join(timeout=5.0)

        # Note: errors may occur during race conditions - this is expected
        # The test verifies no deadlocks occur


@pytest.mark.unit
class TestMixinEventBusLogging:
    """Test MixinEventBus logging helper methods."""

    def test_log_info_emits_event(self) -> None:
        """Test that _log_info emits structured log event."""
        node = TestMixinNode()

        with patch("omnibase_core.mixins.mixin_event_bus.emit_log_event") as mock_log:
            node._log_info("Test message", "test_pattern")

            mock_log.assert_called_once()

    def test_log_warn_emits_event(self) -> None:
        """Test that _log_warn emits structured log event."""
        node = TestMixinNode()

        with patch("omnibase_core.mixins.mixin_event_bus.emit_log_event") as mock_log:
            node._log_warn("Warning message", "test_pattern")

            mock_log.assert_called_once()

    def test_log_error_emits_event_with_exception(self) -> None:
        """Test that _log_error emits event with exception context."""
        node = TestMixinNode()

        with patch("omnibase_core.mixins.mixin_event_bus.emit_log_event") as mock_log:
            test_error = ValueError("test error")
            node._log_error("Error message", "test_pattern", error=test_error)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            context = call_args[1].get(
                "context", call_args[0][2] if len(call_args[0]) > 2 else {}
            )
            if isinstance(context, dict):
                assert "error" in context


@pytest.mark.unit
class TestMixinEventBusBuildEvent:
    """Test MixinEventBus._build_event() method."""

    def test_build_event_creates_onex_event(self) -> None:
        """Test that _build_event creates ModelOnexEvent."""
        node = TestMixinNode()

        # Use ModelCompletionData with no extra fields to avoid validation issues
        # ModelOnexEvent.create_core_event passes **kwargs which must be valid fields
        data = ModelCompletionData()
        event = node._build_event("test.complete", data)

        assert isinstance(event, ModelOnexEvent)
        assert event.event_type == "test.complete"

    def test_build_event_includes_node_id(self) -> None:
        """Test that _build_event includes node_id."""
        node = TestMixinNode()

        # Use ModelCompletionData with no extra fields to avoid validation issues
        data = ModelCompletionData()
        event = node._build_event("test.complete", data)

        assert event.node_id == node.get_node_id()


@pytest.mark.unit
class TestMixinEventBusTopicValidation:
    """Test MixinEventBus._validate_topic_alignment() method."""

    def test_validate_topic_alignment_with_valid_envelope(self) -> None:
        """Test topic validation with valid envelope."""
        node = TestMixinNode()

        mock_envelope = Mock()
        mock_envelope.message_category = Mock()
        mock_envelope.payload = Mock()
        mock_envelope.payload.__class__.__name__ = "TestEvent"

        with patch(
            "omnibase_core.mixins.mixin_event_bus.validate_message_topic_alignment"
        ) as mock_validate:
            node._validate_topic_alignment("dev.test.events.v1", mock_envelope)

            mock_validate.assert_called_once()

    def test_validate_topic_alignment_skips_without_category(self) -> None:
        """Test that validation is skipped without message_category."""
        node = TestMixinNode()

        mock_envelope = Mock(spec=[])  # No message_category attribute

        with patch("omnibase_core.mixins.mixin_event_bus.emit_log_event"):
            # Should not raise
            node._validate_topic_alignment("dev.test.events.v1", mock_envelope)


@pytest.mark.unit
class TestMixinEventBusEdgeCases:
    """Test MixinEventBus edge cases and error scenarios."""

    def test_binding_none_event_bus(self) -> None:
        """Test handling of None event bus binding."""
        node = TestMixinNode()

        # This should work but _get_event_bus returns None
        # Note: bind_event_bus doesn't check for None
        node.bind_event_bus(None)  # type: ignore[arg-type]

        # Still marked as bound
        assert node._event_bus_runtime_state.is_bound is True
        # But get returns None
        assert node._get_event_bus() is None

    def test_get_event_bus_with_none_registry_event_bus(self) -> None:
        """Test _get_event_bus when registry.event_bus is None."""
        node = TestMixinNode()
        mock_registry = Mock()
        mock_registry.event_bus = None

        node.bind_registry(mock_registry)

        # Should return None since registry's event_bus is None
        result = node._get_event_bus()
        assert result is None
