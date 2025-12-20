# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Comprehensive tests for MessageDispatchEngine.

Tests cover:
- Route registration (valid, duplicate, after freeze)
- Handler registration (valid, with message types, after freeze)
- Freeze pattern (freeze, is_frozen, double freeze)
- Dispatch success (single handler, multiple handlers, fan-out)
- Dispatch errors (no handlers, category mismatch, invalid topic, handler exception)
- Async handlers
- Metrics collection
- Deterministic routing (same input -> same handlers)

OMN-934: Message dispatch engine implementation
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.dispatch.model_dispatch_result import ModelDispatchResult
from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.runtime.message_dispatch_engine import MessageDispatchEngine

# ============================================================================
# Test Event Types (for category inference)
# ============================================================================


class UserCreatedEvent:
    """Test event class that ends with 'Event'."""

    def __init__(self, user_id: UUID, name: str) -> None:
        self.user_id = user_id
        self.name = name


class CreateUserCommand:
    """Test command class that ends with 'Command'."""

    def __init__(self, name: str) -> None:
        self.name = name


class ProvisionUserIntent:
    """Test intent class that ends with 'Intent'."""

    def __init__(self, user_type: str) -> None:
        self.user_type = user_type


class SomeGenericPayload:
    """Generic payload class - defaults to EVENT category."""

    def __init__(self, data: str) -> None:
        self.data = data


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def dispatch_engine() -> MessageDispatchEngine:
    """Create a fresh MessageDispatchEngine for each test."""
    return MessageDispatchEngine()


@pytest.fixture
def event_envelope() -> ModelEventEnvelope[UserCreatedEvent]:
    """Create a test event envelope."""
    return ModelEventEnvelope(
        payload=UserCreatedEvent(
            user_id=UUID("00000000-0000-0000-0000-000000000123"), name="Test User"
        ),
        correlation_id=uuid4(),
    )


@pytest.fixture
def command_envelope() -> ModelEventEnvelope[CreateUserCommand]:
    """Create a test command envelope."""
    return ModelEventEnvelope(
        payload=CreateUserCommand(name="New User"),
        correlation_id=uuid4(),
    )


@pytest.fixture
def intent_envelope() -> ModelEventEnvelope[ProvisionUserIntent]:
    """Create a test intent envelope."""
    return ModelEventEnvelope(
        payload=ProvisionUserIntent(user_type="admin"),
        correlation_id=uuid4(),
    )


# ============================================================================
# Route Registration Tests
# ============================================================================


@pytest.mark.unit
class TestRouteRegistration:
    """Tests for route registration functionality."""

    def test_register_route_valid(self, dispatch_engine: MessageDispatchEngine) -> None:
        """Test successful route registration."""
        route = ModelDispatchRoute(
            route_id="user-events-route",
            topic_pattern="*.user.events.*",
            message_category=EnumMessageCategory.EVENT,
            handler_id="user-handler",
        )

        dispatch_engine.register_route(route)

        assert dispatch_engine.route_count == 1

    def test_register_route_multiple(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test registering multiple routes."""
        routes = [
            ModelDispatchRoute(
                route_id=f"route-{i}",
                topic_pattern=f"*.domain{i}.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id=f"handler-{i}",
            )
            for i in range(5)
        ]

        for route in routes:
            dispatch_engine.register_route(route)

        assert dispatch_engine.route_count == 5

    def test_register_route_duplicate_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that duplicate route_id raises DUPLICATE_REGISTRATION error."""
        route = ModelDispatchRoute(
            route_id="duplicate-route",
            topic_pattern="*.user.events.*",
            message_category=EnumMessageCategory.EVENT,
            handler_id="handler",
        )

        dispatch_engine.register_route(route)

        # Try to register with same route_id
        duplicate = ModelDispatchRoute(
            route_id="duplicate-route",  # Same ID
            topic_pattern="*.order.events.*",  # Different pattern
            message_category=EnumMessageCategory.EVENT,
            handler_id="other-handler",
        )

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_route(duplicate)

        assert exc_info.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
        assert "duplicate-route" in exc_info.value.message

    def test_register_route_none_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that registering None raises INVALID_PARAMETER error."""
        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_route(None)  # type: ignore[arg-type]

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    def test_register_route_after_freeze_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that route registration after freeze raises INVALID_STATE error."""
        dispatch_engine.freeze()

        route = ModelDispatchRoute(
            route_id="late-route",
            topic_pattern="*.user.events.*",
            message_category=EnumMessageCategory.EVENT,
            handler_id="handler",
        )

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_route(route)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "frozen" in exc_info.value.message.lower()


# ============================================================================
# Handler Registration Tests
# ============================================================================


@pytest.mark.unit
class TestHandlerRegistration:
    """Tests for handler registration functionality."""

    def test_register_handler_valid_sync(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test successful sync handler registration."""

        def sync_handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        dispatch_engine.register_handler(
            handler_id="sync-handler",
            handler=sync_handler,
            category=EnumMessageCategory.EVENT,
        )

        assert dispatch_engine.handler_count == 1

    def test_register_handler_valid_async(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test successful async handler registration."""

        async def async_handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        dispatch_engine.register_handler(
            handler_id="async-handler",
            handler=async_handler,
            category=EnumMessageCategory.EVENT,
        )

        assert dispatch_engine.handler_count == 1

    def test_register_handler_with_message_types(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test handler registration with specific message types."""

        def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        dispatch_engine.register_handler(
            handler_id="typed-handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
            message_types={"UserCreatedEvent", "UserUpdatedEvent"},
        )

        assert dispatch_engine.handler_count == 1

    def test_register_handler_multiple_categories(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test registering handlers for different categories."""

        def event_handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "event"

        def command_handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "command"

        def intent_handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "intent"

        dispatch_engine.register_handler(
            handler_id="event-handler",
            handler=event_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_handler(
            handler_id="command-handler",
            handler=command_handler,
            category=EnumMessageCategory.COMMAND,
        )
        dispatch_engine.register_handler(
            handler_id="intent-handler",
            handler=intent_handler,
            category=EnumMessageCategory.INTENT,
        )

        assert dispatch_engine.handler_count == 3

    def test_register_handler_duplicate_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that duplicate handler_id raises DUPLICATE_REGISTRATION error."""

        def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        dispatch_engine.register_handler(
            handler_id="dup-handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_handler(
                handler_id="dup-handler",  # Same ID
                handler=handler,
                category=EnumMessageCategory.COMMAND,  # Different category
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
        assert "dup-handler" in exc_info.value.message

    def test_register_handler_empty_id_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that empty handler_id raises INVALID_PARAMETER error."""

        def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_handler(
                handler_id="",
                handler=handler,
                category=EnumMessageCategory.EVENT,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    def test_register_handler_whitespace_id_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that whitespace-only handler_id raises INVALID_PARAMETER error."""

        def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_handler(
                handler_id="   ",
                handler=handler,
                category=EnumMessageCategory.EVENT,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    def test_register_handler_none_callable_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that non-callable handler raises INVALID_PARAMETER error."""
        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_handler(
                handler_id="bad-handler",
                handler=None,  # type: ignore[arg-type]
                category=EnumMessageCategory.EVENT,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    def test_register_handler_non_callable_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that non-callable object raises INVALID_PARAMETER error."""
        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_handler(
                handler_id="bad-handler",
                handler="not a function",  # type: ignore[arg-type]
                category=EnumMessageCategory.EVENT,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    def test_register_handler_invalid_category_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that invalid category raises INVALID_PARAMETER error."""

        def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_handler(
                handler_id="handler",
                handler=handler,
                category="not_a_category",  # type: ignore[arg-type]
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    def test_register_handler_after_freeze_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that handler registration after freeze raises INVALID_STATE error."""
        dispatch_engine.freeze()

        def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.register_handler(
                handler_id="late-handler",
                handler=handler,
                category=EnumMessageCategory.EVENT,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "frozen" in exc_info.value.message.lower()


# ============================================================================
# Freeze Pattern Tests
# ============================================================================


@pytest.mark.unit
class TestFreezePattern:
    """Tests for the freeze-after-init pattern."""

    def test_freeze_sets_frozen_flag(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that freeze() sets the frozen flag."""
        assert not dispatch_engine.is_frozen

        dispatch_engine.freeze()

        assert dispatch_engine.is_frozen

    def test_freeze_double_freeze_is_idempotent(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that calling freeze() multiple times is idempotent."""
        dispatch_engine.freeze()
        assert dispatch_engine.is_frozen

        # Second freeze should not raise
        dispatch_engine.freeze()
        assert dispatch_engine.is_frozen

    def test_freeze_validates_route_handler_references(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that freeze validates all routes reference existing handlers."""
        # Register a route without a matching handler
        route = ModelDispatchRoute(
            route_id="orphan-route",
            topic_pattern="*.user.events.*",
            message_category=EnumMessageCategory.EVENT,
            handler_id="nonexistent-handler",
        )
        dispatch_engine.register_route(route)

        with pytest.raises(ModelOnexError) as exc_info:
            dispatch_engine.freeze()

        assert exc_info.value.error_code == EnumCoreErrorCode.ITEM_NOT_REGISTERED
        assert "nonexistent-handler" in exc_info.value.message

    def test_freeze_with_valid_configuration(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test successful freeze with valid route-handler configuration."""

        def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        dispatch_engine.register_handler(
            handler_id="user-handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="user-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="user-handler",
            )
        )

        # Should not raise
        dispatch_engine.freeze()

        assert dispatch_engine.is_frozen

    def test_freeze_empty_engine(self, dispatch_engine: MessageDispatchEngine) -> None:
        """Test freeze with no routes or handlers."""
        # Should not raise - empty engine is valid
        dispatch_engine.freeze()

        assert dispatch_engine.is_frozen
        assert dispatch_engine.route_count == 0
        assert dispatch_engine.handler_count == 0


# ============================================================================
# Dispatch Success Tests
# ============================================================================


@pytest.mark.unit
class TestDispatchSuccess:
    """Tests for successful dispatch operations."""

    @pytest.mark.asyncio
    async def test_dispatch_single_handler(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test dispatch with a single matching handler."""
        results: list[str] = []

        async def handler(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("handled")
            return "output.topic.v1"

        dispatch_engine.register_handler(
            handler_id="event-handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="event-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="event-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.SUCCESS
        assert len(results) == 1
        assert result.outputs is not None
        assert "output.topic.v1" in result.outputs

    @pytest.mark.asyncio
    async def test_dispatch_sync_handler(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test dispatch with a sync handler (runs in executor)."""
        results: list[str] = []

        def sync_handler(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("sync_handled")
            return "sync.output.v1"

        dispatch_engine.register_handler(
            handler_id="sync-handler",
            handler=sync_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="sync-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="sync-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.SUCCESS
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_dispatch_multiple_handlers_fan_out(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test fan-out dispatch to multiple handlers via multiple routes."""
        results: list[str] = []

        async def handler1(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("handler1")
            return "output1.v1"

        async def handler2(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("handler2")
            return "output2.v1"

        dispatch_engine.register_handler(
            handler_id="handler-1",
            handler=handler1,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_handler(
            handler_id="handler-2",
            handler=handler2,
            category=EnumMessageCategory.EVENT,
        )

        # Two routes pointing to different handlers, both match the topic
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route-1",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler-1",
            )
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route-2",
                topic_pattern="dev.**",  # Also matches
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler-2",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.SUCCESS
        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results
        assert result.output_count == 2

    @pytest.mark.asyncio
    async def test_dispatch_handler_returning_list_of_outputs(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test handler that returns list of output topics."""

        async def handler(envelope: ModelEventEnvelope[Any]) -> list[str]:
            return ["output1.v1", "output2.v1", "output3.v1"]

        dispatch_engine.register_handler(
            handler_id="multi-output-handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="multi-output-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.SUCCESS
        assert result.output_count == 3
        assert result.outputs is not None
        assert len(result.outputs) == 3

    @pytest.mark.asyncio
    async def test_dispatch_handler_returning_none(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test handler that returns None (no outputs)."""

        async def handler(envelope: ModelEventEnvelope[Any]) -> None:
            pass  # No return value

        dispatch_engine.register_handler(
            handler_id="void-handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="void-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.SUCCESS
        assert result.output_count == 0

    @pytest.mark.asyncio
    async def test_dispatch_with_message_type_filter(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test dispatch with message type filtering."""
        results: list[str] = []

        async def user_created_handler(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("user_created")
            return "created.output"

        async def user_updated_handler(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("user_updated")
            return "updated.output"

        dispatch_engine.register_handler(
            handler_id="created-handler",
            handler=user_created_handler,
            category=EnumMessageCategory.EVENT,
            message_types={"UserCreatedEvent"},  # Only handles UserCreatedEvent
        )
        dispatch_engine.register_handler(
            handler_id="updated-handler",
            handler=user_updated_handler,
            category=EnumMessageCategory.EVENT,
            message_types={"UserUpdatedEvent"},  # Only handles UserUpdatedEvent
        )

        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="created-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="created-handler",
            )
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="updated-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="updated-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        # Only created-handler should be invoked
        assert result.status == EnumDispatchStatus.SUCCESS
        assert len(results) == 1
        assert "user_created" in results

    @pytest.mark.asyncio
    async def test_dispatch_preserves_correlation_id(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test that dispatch result preserves envelope correlation_id."""

        async def handler(envelope: ModelEventEnvelope[Any]) -> None:
            pass

        dispatch_engine.register_handler(
            handler_id="handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.correlation_id == event_envelope.correlation_id


# ============================================================================
# Dispatch Error Tests
# ============================================================================


@pytest.mark.unit
class TestDispatchErrors:
    """Tests for dispatch error scenarios."""

    @pytest.mark.asyncio
    async def test_dispatch_before_freeze_raises_error(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test that dispatch before freeze raises INVALID_STATE error."""
        # Don't call freeze()

        with pytest.raises(ModelOnexError) as exc_info:
            await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "freeze" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_dispatch_empty_topic_raises_error(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test that empty topic raises INVALID_PARAMETER error."""
        dispatch_engine.freeze()

        with pytest.raises(ModelOnexError) as exc_info:
            await dispatch_engine.dispatch("", event_envelope)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    @pytest.mark.asyncio
    async def test_dispatch_whitespace_topic_raises_error(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test that whitespace-only topic raises INVALID_PARAMETER error."""
        dispatch_engine.freeze()

        with pytest.raises(ModelOnexError) as exc_info:
            await dispatch_engine.dispatch("   ", event_envelope)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    @pytest.mark.asyncio
    async def test_dispatch_none_envelope_raises_error(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that None envelope raises INVALID_PARAMETER error."""
        dispatch_engine.freeze()

        with pytest.raises(ModelOnexError) as exc_info:
            await dispatch_engine.dispatch(
                "dev.user.events.v1",
                None,  # type: ignore[arg-type]
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    @pytest.mark.asyncio
    async def test_dispatch_no_handlers_returns_no_handler_status(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test dispatch with no matching handlers returns NO_HANDLER status."""
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.NO_HANDLER
        assert result.error_message is not None
        assert "No handler" in result.error_message

    @pytest.mark.asyncio
    async def test_dispatch_invalid_topic_returns_invalid_message(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test dispatch with invalid topic (no category) returns INVALID_MESSAGE."""
        dispatch_engine.freeze()

        # Topic without events/commands/intents segment
        result = await dispatch_engine.dispatch("invalid.topic.here", event_envelope)

        assert result.status == EnumDispatchStatus.INVALID_MESSAGE
        assert result.error_message is not None
        assert "category" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_dispatch_category_mismatch_returns_invalid_message(
        self,
        dispatch_engine: MessageDispatchEngine,
        command_envelope: ModelEventEnvelope[CreateUserCommand],
    ) -> None:
        """Test dispatch where envelope category doesn't match topic category."""
        dispatch_engine.freeze()

        # Sending a COMMAND envelope to an events topic
        result = await dispatch_engine.dispatch("dev.user.events.v1", command_envelope)

        assert result.status == EnumDispatchStatus.INVALID_MESSAGE
        assert result.error_message is not None
        assert "mismatch" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_dispatch_handler_exception_returns_handler_error(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test that handler exception results in HANDLER_ERROR status."""

        async def failing_handler(envelope: ModelEventEnvelope[Any]) -> None:
            raise ValueError("Something went wrong!")

        dispatch_engine.register_handler(
            handler_id="failing-handler",
            handler=failing_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="failing-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.HANDLER_ERROR
        assert result.error_message is not None
        assert "Something went wrong" in result.error_message

    @pytest.mark.asyncio
    async def test_dispatch_partial_handler_failure(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test dispatch where some handlers succeed and some fail."""
        results: list[str] = []

        async def success_handler(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("success")
            return "success.output"

        async def failing_handler(envelope: ModelEventEnvelope[Any]) -> None:
            results.append("failing")
            raise RuntimeError("Handler failed!")

        dispatch_engine.register_handler(
            handler_id="success-handler",
            handler=success_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_handler(
            handler_id="failing-handler",
            handler=failing_handler,
            category=EnumMessageCategory.EVENT,
        )

        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="success-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="success-handler",
            )
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="failing-route",
                topic_pattern="dev.**",
                message_category=EnumMessageCategory.EVENT,
                handler_id="failing-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        # Both handlers should have been called
        assert len(results) == 2
        assert "success" in results
        assert "failing" in results

        # Status should be HANDLER_ERROR due to partial failure
        assert result.status == EnumDispatchStatus.HANDLER_ERROR
        assert result.error_message is not None
        assert "Handler failed" in result.error_message

        # But we should still have the output from the successful handler
        assert result.outputs is not None
        assert "success.output" in result.outputs

    @pytest.mark.asyncio
    async def test_dispatch_disabled_route_not_matched(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test that disabled routes are not matched."""

        async def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "handled"

        dispatch_engine.register_handler(
            handler_id="handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="disabled-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
                enabled=False,  # Disabled
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        # No handlers should match due to disabled route
        assert result.status == EnumDispatchStatus.NO_HANDLER


# ============================================================================
# Async Handler Tests
# ============================================================================


@pytest.mark.unit
class TestAsyncHandlers:
    """Tests for async handler functionality."""

    @pytest.mark.asyncio
    async def test_async_handler_with_await(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test async handler that uses await."""
        results: list[str] = []

        async def async_handler(envelope: ModelEventEnvelope[Any]) -> str:
            await asyncio.sleep(0.01)  # Simulate async work
            results.append("async_complete")
            return "async.output"

        dispatch_engine.register_handler(
            handler_id="async-handler",
            handler=async_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="async-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        assert result.status == EnumDispatchStatus.SUCCESS
        assert len(results) == 1
        assert results[0] == "async_complete"


# ============================================================================
# Metrics Tests
# ============================================================================


@pytest.mark.unit
class TestMetrics:
    """Tests for metrics collection."""

    def test_initial_metrics(self, dispatch_engine: MessageDispatchEngine) -> None:
        """Test initial metrics values."""
        metrics = dispatch_engine.get_metrics()

        assert metrics["dispatch_count"] == 0
        assert metrics["dispatch_success_count"] == 0
        assert metrics["dispatch_error_count"] == 0
        assert metrics["total_latency_ms"] == 0.0
        assert metrics["handler_execution_count"] == 0
        assert metrics["handler_error_count"] == 0
        assert metrics["routes_matched_count"] == 0
        assert metrics["no_handler_count"] == 0
        assert metrics["category_mismatch_count"] == 0

    @pytest.mark.asyncio
    async def test_metrics_updated_on_success(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test metrics are updated on successful dispatch."""

        async def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "output"

        dispatch_engine.register_handler(
            handler_id="handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
            )
        )
        dispatch_engine.freeze()

        await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        metrics = dispatch_engine.get_metrics()
        assert metrics["dispatch_count"] == 1
        assert metrics["dispatch_success_count"] == 1
        assert metrics["dispatch_error_count"] == 0
        assert metrics["handler_execution_count"] == 1
        assert metrics["total_latency_ms"] > 0
        assert metrics["routes_matched_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_updated_on_handler_error(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test metrics are updated on handler error."""

        async def failing_handler(envelope: ModelEventEnvelope[Any]) -> None:
            raise ValueError("Failure!")

        dispatch_engine.register_handler(
            handler_id="handler",
            handler=failing_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
            )
        )
        dispatch_engine.freeze()

        await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        metrics = dispatch_engine.get_metrics()
        assert metrics["dispatch_count"] == 1
        assert metrics["dispatch_error_count"] == 1
        assert metrics["handler_execution_count"] == 1
        assert metrics["handler_error_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_updated_on_no_handler(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test metrics are updated when no handler is found."""
        dispatch_engine.freeze()

        await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        metrics = dispatch_engine.get_metrics()
        assert metrics["dispatch_count"] == 1
        assert metrics["dispatch_error_count"] == 1
        assert metrics["no_handler_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_updated_on_category_mismatch(
        self,
        dispatch_engine: MessageDispatchEngine,
        command_envelope: ModelEventEnvelope[CreateUserCommand],
    ) -> None:
        """Test metrics are updated on category mismatch."""
        dispatch_engine.freeze()

        # Sending COMMAND envelope to events topic
        await dispatch_engine.dispatch("dev.user.events.v1", command_envelope)

        metrics = dispatch_engine.get_metrics()
        assert metrics["dispatch_count"] == 1
        assert metrics["dispatch_error_count"] == 1
        assert metrics["category_mismatch_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_accumulate_across_dispatches(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test metrics accumulate across multiple dispatches."""

        async def handler(envelope: ModelEventEnvelope[Any]) -> str:
            return "output"

        dispatch_engine.register_handler(
            handler_id="handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
            )
        )
        dispatch_engine.freeze()

        # Dispatch multiple times
        for _ in range(5):
            await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        metrics = dispatch_engine.get_metrics()
        assert metrics["dispatch_count"] == 5
        assert metrics["dispatch_success_count"] == 5
        assert metrics["handler_execution_count"] == 5


# ============================================================================
# Deterministic Routing Tests
# ============================================================================


@pytest.mark.unit
class TestDeterministicRouting:
    """Tests for deterministic routing behavior (same input -> same handlers)."""

    @pytest.mark.asyncio
    async def test_same_input_same_handlers(
        self,
        dispatch_engine: MessageDispatchEngine,
    ) -> None:
        """Test that same input always produces same handler selection."""
        handler_calls: list[list[str]] = []

        async def handler1(envelope: ModelEventEnvelope[Any]) -> None:
            pass

        async def handler2(envelope: ModelEventEnvelope[Any]) -> None:
            pass

        dispatch_engine.register_handler(
            handler_id="handler-1",
            handler=handler1,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_handler(
            handler_id="handler-2",
            handler=handler2,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route-1",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler-1",
            )
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route-2",
                topic_pattern="dev.**",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler-2",
            )
        )
        dispatch_engine.freeze()

        # Dispatch multiple times with same input
        results: list[ModelDispatchResult] = []
        for _ in range(10):
            envelope = ModelEventEnvelope(
                payload=UserCreatedEvent(
                    user_id=UUID("00000000-0000-0000-0000-000000000123"), name="Test"
                )
            )
            result = await dispatch_engine.dispatch("dev.user.events.v1", envelope)
            results.append(result)

        # All results should have the same handler_id
        handler_ids = [r.handler_id for r in results]
        assert len(set(handler_ids)) == 1  # All same
        assert all(r.status == EnumDispatchStatus.SUCCESS for r in results)

    @pytest.mark.asyncio
    async def test_different_topics_different_handlers(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that different topics route to different handlers."""

        async def user_handler(envelope: ModelEventEnvelope[Any]) -> None:
            pass

        async def order_handler(envelope: ModelEventEnvelope[Any]) -> None:
            pass

        dispatch_engine.register_handler(
            handler_id="user-handler",
            handler=user_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_handler(
            handler_id="order-handler",
            handler=order_handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="user-route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="user-handler",
            )
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="order-route",
                topic_pattern="*.order.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="order-handler",
            )
        )
        dispatch_engine.freeze()

        user_envelope = ModelEventEnvelope(
            payload=UserCreatedEvent(
                user_id=UUID("00000000-0000-0000-0000-000000000123"), name="Test"
            )
        )
        order_envelope = ModelEventEnvelope(payload=SomeGenericPayload(data="order"))

        user_result = await dispatch_engine.dispatch(
            "dev.user.events.v1", user_envelope
        )
        order_result = await dispatch_engine.dispatch(
            "dev.order.events.v1", order_envelope
        )

        assert user_result.handler_id == "user-handler"
        assert order_result.handler_id == "order-handler"


# ============================================================================
# Pure Routing Tests (No Workflow Inference)
# ============================================================================


@pytest.mark.unit
class TestPureRouting:
    """Tests verifying the engine performs pure routing without workflow inference."""

    @pytest.mark.asyncio
    async def test_no_workflow_inference_from_payload(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test that routing is based on topic/category, not payload content."""
        handler_calls: list[str] = []

        async def handler(envelope: ModelEventEnvelope[Any]) -> None:
            handler_calls.append(type(envelope.payload).__name__)

        dispatch_engine.register_handler(
            handler_id="generic-handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="generic-handler",
            )
        )
        dispatch_engine.freeze()

        # Different payload types, same topic
        envelope1 = ModelEventEnvelope(
            payload=UserCreatedEvent(
                user_id=UUID("00000000-0000-0000-0000-000000000001"), name="Alice"
            )
        )
        envelope2 = ModelEventEnvelope(payload=SomeGenericPayload(data="test"))

        await dispatch_engine.dispatch("dev.user.events.v1", envelope1)
        await dispatch_engine.dispatch("dev.user.events.v1", envelope2)

        # Both should route to the same handler regardless of payload type
        assert len(handler_calls) == 2
        assert handler_calls[0] == "UserCreatedEvent"
        assert handler_calls[1] == "SomeGenericPayload"

    @pytest.mark.asyncio
    async def test_outputs_are_publishing_only(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """Test that outputs are collected for publishing, not interpreted."""

        # Handler returns various output formats
        async def handler(envelope: ModelEventEnvelope[Any]) -> list[str]:
            return [
                "output.topic.v1",
                "another.output.v1",
                "third.output.commands.v1",  # Note: commands topic
            ]

        dispatch_engine.register_handler(
            handler_id="handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.user.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.events.v1", event_envelope)

        # Outputs should be collected as-is for publishing
        assert result.status == EnumDispatchStatus.SUCCESS
        assert result.outputs is not None
        assert len(result.outputs) == 3
        # The engine doesn't interpret what these topics mean
        assert "output.topic.v1" in result.outputs
        assert "third.output.commands.v1" in result.outputs


# ============================================================================
# String Representation Tests
# ============================================================================


@pytest.mark.unit
class TestStringRepresentation:
    """Tests for __str__ and __repr__ methods."""

    def test_str_representation(self, dispatch_engine: MessageDispatchEngine) -> None:
        """Test __str__ method."""
        result = str(dispatch_engine)
        assert "MessageDispatchEngine" in result
        assert "routes=0" in result
        assert "handlers=0" in result
        assert "frozen=False" in result

    def test_str_representation_with_data(
        self, dispatch_engine: MessageDispatchEngine
    ) -> None:
        """Test __str__ method with routes and handlers."""

        def handler(envelope: ModelEventEnvelope[Any]) -> None:
            pass

        dispatch_engine.register_handler(
            handler_id="handler",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route",
                topic_pattern="*.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
            )
        )
        dispatch_engine.freeze()

        result = str(dispatch_engine)
        assert "routes=1" in result
        assert "handlers=1" in result
        assert "frozen=True" in result

    def test_repr_representation(self, dispatch_engine: MessageDispatchEngine) -> None:
        """Test __repr__ method."""
        result = repr(dispatch_engine)
        assert "MessageDispatchEngine" in result
        assert "frozen=" in result


# ============================================================================
# Properties Tests
# ============================================================================


@pytest.mark.unit
class TestProperties:
    """Tests for engine properties."""

    def test_route_count(self, dispatch_engine: MessageDispatchEngine) -> None:
        """Test route_count property."""
        assert dispatch_engine.route_count == 0

        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route-1",
                topic_pattern="*.events.*",
                message_category=EnumMessageCategory.EVENT,
                handler_id="handler",
            )
        )
        assert dispatch_engine.route_count == 1

        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="route-2",
                topic_pattern="*.commands.*",
                message_category=EnumMessageCategory.COMMAND,
                handler_id="handler",
            )
        )
        assert dispatch_engine.route_count == 2

    def test_handler_count(self, dispatch_engine: MessageDispatchEngine) -> None:
        """Test handler_count property."""

        def handler(envelope: ModelEventEnvelope[Any]) -> None:
            pass

        assert dispatch_engine.handler_count == 0

        dispatch_engine.register_handler(
            handler_id="handler-1",
            handler=handler,
            category=EnumMessageCategory.EVENT,
        )
        assert dispatch_engine.handler_count == 1

        dispatch_engine.register_handler(
            handler_id="handler-2",
            handler=handler,
            category=EnumMessageCategory.COMMAND,
        )
        assert dispatch_engine.handler_count == 2


# ============================================================================
# Command and Intent Dispatch Tests
# ============================================================================


@pytest.mark.unit
class TestCommandAndIntentDispatch:
    """Tests for dispatching commands and intents."""

    @pytest.mark.asyncio
    async def test_dispatch_command(
        self,
        dispatch_engine: MessageDispatchEngine,
        command_envelope: ModelEventEnvelope[CreateUserCommand],
    ) -> None:
        """Test successful command dispatch."""
        results: list[str] = []

        async def command_handler(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("command_handled")
            return "result.events.v1"

        dispatch_engine.register_handler(
            handler_id="command-handler",
            handler=command_handler,
            category=EnumMessageCategory.COMMAND,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="command-route",
                topic_pattern="*.user.commands.*",
                message_category=EnumMessageCategory.COMMAND,
                handler_id="command-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch(
            "dev.user.commands.v1", command_envelope
        )

        assert result.status == EnumDispatchStatus.SUCCESS
        assert len(results) == 1
        assert result.message_category == EnumMessageCategory.COMMAND

    @pytest.mark.asyncio
    async def test_dispatch_intent(
        self,
        dispatch_engine: MessageDispatchEngine,
        intent_envelope: ModelEventEnvelope[ProvisionUserIntent],
    ) -> None:
        """Test successful intent dispatch."""
        results: list[str] = []

        async def intent_handler(envelope: ModelEventEnvelope[Any]) -> str:
            results.append("intent_handled")
            return "user.commands.v1"

        dispatch_engine.register_handler(
            handler_id="intent-handler",
            handler=intent_handler,
            category=EnumMessageCategory.INTENT,
        )
        dispatch_engine.register_route(
            ModelDispatchRoute(
                route_id="intent-route",
                topic_pattern="*.user.intents.*",
                message_category=EnumMessageCategory.INTENT,
                handler_id="intent-handler",
            )
        )
        dispatch_engine.freeze()

        result = await dispatch_engine.dispatch("dev.user.intents.v1", intent_envelope)

        assert result.status == EnumDispatchStatus.SUCCESS
        assert len(results) == 1
        assert result.message_category == EnumMessageCategory.INTENT


# ============================================================================
# Publishing Order Tests (OMN-941)
# ============================================================================


@pytest.mark.unit
class TestPublishingOrder:
    """
    Test causality-correct publishing order per OMN-941.

    The runtime must publish outputs in causality-correct order:
    1. Events (facts about what happened)
    2. Projections (read-optimized state updates)
    3. Intents (requests for future side effects)

    This ordering ensures that:
    - Consumers see events before derived state updates
    - Projections are consistent with event stream
    - Intents are processed after all state is updated
    """

    @pytest.fixture
    def mock_event_bus(self) -> Any:
        """Create a mock event bus with an async publish method."""
        from unittest.mock import AsyncMock

        event_bus = AsyncMock()
        event_bus.publish = AsyncMock()
        return event_bus

    @pytest.fixture
    def sample_event_envelope(self) -> ModelEventEnvelope[UserCreatedEvent]:
        """Create a sample event envelope for testing."""
        return ModelEventEnvelope(
            payload=UserCreatedEvent(
                user_id=UUID("00000000-0000-0000-0000-000000000123"), name="Test User"
            ),
            correlation_id=uuid4(),
        )

    @pytest.fixture
    def sample_projection(self) -> dict[str, Any]:
        """Create a sample projection for testing."""
        return {"type": "UserProjection", "user_id": "user-123", "name": "Test User"}

    @pytest.fixture
    def sample_intent(self) -> dict[str, Any]:
        """Create a sample intent for testing."""
        return {"type": "SendWelcomeEmailIntent", "user_id": "user-123"}

    @pytest.mark.asyncio
    async def test_publish_order_events_first(
        self,
        mock_event_bus: Any,
        sample_event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """
        Events must be published before projections and intents.

        Per OMN-941: Events represent facts about what happened and must
        be published first to maintain causality. Consumers should see
        events before any derived state updates or side-effect requests.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Create handler output with events, projections, and intents
        # (Using ORCHESTRATOR which can emit events and intents)
        event1 = {"type": "Event1", "data": "event_data_1"}
        event2 = {"type": "Event2", "data": "event_data_2"}

        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=uuid4(),
            correlation_id=sample_event_envelope.correlation_id
            if sample_event_envelope.correlation_id
            else uuid4(),
            handler_id="test-orchestrator",
            events=(event1, event2),
            intents=({"type": "SomeIntent"},),
        )

        # Verify event order - events should be before intents
        assert len(output.events) == 2
        assert output.events[0] == event1
        assert output.events[1] == event2
        # Events are listed before intents in the model structure
        assert output.output_count() == 3  # 2 events + 1 intent

    @pytest.mark.asyncio
    async def test_publish_order_projections_second(
        self,
        mock_event_bus: Any,
        sample_projection: dict[str, Any],
    ) -> None:
        """
        Projections must be published after events, before intents.

        Per OMN-941: Projections represent read-optimized state updates
        derived from events. They must be published after events so that
        the state is consistent with the event stream.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Create REDUCER output with projections only
        projection1 = {"type": "Projection1", "state": "updated"}
        projection2 = {"type": "Projection2", "state": "created"}

        output = ModelHandlerOutput.for_reducer(
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="test-reducer",
            projections=(projection1, projection2),
        )

        # Verify projections are properly stored
        assert len(output.projections) == 2
        assert output.projections[0] == projection1
        assert output.projections[1] == projection2
        # Reducer should only have projections, no events or intents
        assert len(output.events) == 0
        assert len(output.intents) == 0

    @pytest.mark.asyncio
    async def test_publish_order_intents_last(
        self,
        mock_event_bus: Any,
        sample_intent: dict[str, Any],
    ) -> None:
        """
        Intents must be published after events and projections.

        Per OMN-941: Intents represent requests for future side effects.
        They must be published last to ensure that all state updates
        (events and projections) are complete before any side effects
        are triggered.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Create ORCHESTRATOR output with events and intents
        event1 = {"type": "Event1"}
        intent1 = {"type": "Intent1", "action": "send_email"}
        intent2 = {"type": "Intent2", "action": "send_notification"}

        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="test-orchestrator",
            events=(event1,),
            intents=(intent1, intent2),
        )

        # Verify intents are stored after events in output model
        assert len(output.events) == 1
        assert len(output.intents) == 2
        assert output.intents[0] == intent1
        assert output.intents[1] == intent2

    @pytest.mark.asyncio
    async def test_handler_order_preserved_within_events(
        self,
        mock_event_bus: Any,
    ) -> None:
        """
        Handler-returned order must be preserved within events category.

        Per OMN-941: When a handler returns multiple events, their relative
        order must be preserved during publishing. This ensures deterministic
        behavior and maintains causality within a handler's output.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Create events in specific order
        events = tuple(
            {"type": f"Event{i}", "sequence": i, "data": f"data_{i}"}
            for i in range(1, 6)
        )

        output = ModelHandlerOutput.for_effect(
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="test-effect",
            events=events,
        )

        # Verify order is preserved
        assert len(output.events) == 5
        for i, event in enumerate(output.events):
            expected_sequence = i + 1
            assert event["sequence"] == expected_sequence
            assert event["type"] == f"Event{expected_sequence}"

    @pytest.mark.asyncio
    async def test_handler_order_preserved_within_projections(
        self,
        mock_event_bus: Any,
    ) -> None:
        """
        Handler-returned order must be preserved within projections category.

        Per OMN-941: When a handler returns multiple projections, their
        relative order must be preserved. This is important for projections
        that may have dependencies on each other.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Create projections in specific order
        projections = tuple(
            {"type": f"Projection{i}", "version": i, "state": f"state_{i}"}
            for i in range(1, 4)
        )

        output = ModelHandlerOutput.for_reducer(
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="test-reducer",
            projections=projections,
        )

        # Verify order is preserved
        assert len(output.projections) == 3
        for i, projection in enumerate(output.projections):
            expected_version = i + 1
            assert projection["version"] == expected_version
            assert projection["type"] == f"Projection{expected_version}"

    @pytest.mark.asyncio
    async def test_handler_order_preserved_within_intents(
        self,
        mock_event_bus: Any,
    ) -> None:
        """
        Handler-returned order must be preserved within intents category.

        Per OMN-941: When a handler returns multiple intents, their
        relative order must be preserved. This is critical when intents
        have sequential dependencies.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Create intents in specific order with dependencies
        intents = tuple(
            {
                "type": f"Intent{i}",
                "priority": i,
                "depends_on": f"Intent{i - 1}" if i > 1 else None,
            }
            for i in range(1, 5)
        )

        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="test-orchestrator",
            intents=intents,
        )

        # Verify order is preserved
        assert len(output.intents) == 4
        for i, intent in enumerate(output.intents):
            expected_priority = i + 1
            assert intent["priority"] == expected_priority
            assert intent["type"] == f"Intent{expected_priority}"

    @pytest.mark.asyncio
    async def test_fanout_multiple_handlers_correct_order(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """
        Multiple handlers (fan-out) outputs must be ordered correctly.

        Per OMN-941: When multiple handlers process the same message,
        the combined outputs must maintain causality order:
        1. All events from all handlers (in handler execution order)
        2. All projections from all handlers
        3. All intents from all handlers

        Within each category, handler-returned order is preserved.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Simulate multiple handler outputs
        handler1_output = ModelHandlerOutput.for_effect(
            input_envelope_id=uuid4(),
            correlation_id=event_envelope.correlation_id or uuid4(),
            handler_id="handler-1",
            events=({"type": "H1Event1"}, {"type": "H1Event2"}),
        )

        handler2_output = ModelHandlerOutput.for_effect(
            input_envelope_id=uuid4(),
            correlation_id=event_envelope.correlation_id or uuid4(),
            handler_id="handler-2",
            events=({"type": "H2Event1"}, {"type": "H2Event2"}),
        )

        # Collect all outputs in fan-out order
        all_outputs = [handler1_output, handler2_output]

        # Verify each handler's events maintain their order
        assert handler1_output.events[0]["type"] == "H1Event1"
        assert handler1_output.events[1]["type"] == "H1Event2"
        assert handler2_output.events[0]["type"] == "H2Event1"
        assert handler2_output.events[1]["type"] == "H2Event2"

        # Combined event count
        total_events = sum(len(output.events) for output in all_outputs)
        assert total_events == 4

    @pytest.mark.asyncio
    async def test_empty_outputs_no_publish(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """
        Empty handler outputs must not cause errors during publish.

        Per OMN-941: Handlers may produce empty outputs (e.g., filtering,
        idempotent duplicate detection). The dispatch engine must handle
        empty outputs gracefully without attempting to publish nothing.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Create empty output
        empty_output = ModelHandlerOutput.empty(
            input_envelope_id=uuid4(),
            correlation_id=event_envelope.correlation_id or uuid4(),
            handler_id="filter-handler",
            node_kind=EnumNodeKind.COMPUTE,
        )

        # Verify empty output state
        assert not empty_output.has_outputs()
        assert empty_output.output_count() == 0
        assert len(empty_output.events) == 0
        assert len(empty_output.projections) == 0
        assert len(empty_output.intents) == 0

    @pytest.mark.asyncio
    async def test_mixed_node_kinds_correct_order(
        self,
        dispatch_engine: MessageDispatchEngine,
        event_envelope: ModelEventEnvelope[UserCreatedEvent],
    ) -> None:
        """
        Mixed ORCHESTRATOR, REDUCER, EFFECT outputs must be ordered correctly.

        Per OMN-941: When handlers of different node kinds process messages,
        their outputs must still follow causality order globally:
        1. All events (from EFFECT, COMPUTE, ORCHESTRATOR)
        2. All projections (from REDUCER only)
        3. All intents (from ORCHESTRATOR only)
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        correlation_id = event_envelope.correlation_id or uuid4()

        # Create outputs from different node kinds
        effect_output = ModelHandlerOutput.for_effect(
            input_envelope_id=uuid4(),
            correlation_id=correlation_id,
            handler_id="effect-handler",
            events=({"type": "EffectEvent", "source": "effect"},),
        )

        reducer_output = ModelHandlerOutput.for_reducer(
            input_envelope_id=uuid4(),
            correlation_id=correlation_id,
            handler_id="reducer-handler",
            projections=({"type": "StateProjection", "source": "reducer"},),
        )

        orchestrator_output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=uuid4(),
            correlation_id=correlation_id,
            handler_id="orchestrator-handler",
            events=({"type": "OrchestratorEvent", "source": "orchestrator"},),
            intents=({"type": "SideEffectIntent", "source": "orchestrator"},),
        )

        # Collect all outputs to verify structure
        all_outputs = [effect_output, reducer_output, orchestrator_output]

        # Collect all events (should be from effect and orchestrator)
        all_events = []
        for output in all_outputs:
            all_events.extend(output.events)
        assert len(all_events) == 2  # 1 from effect, 1 from orchestrator

        # Collect all projections (should be from reducer only)
        all_projections = []
        for output in all_outputs:
            all_projections.extend(output.projections)
        assert len(all_projections) == 1  # 1 from reducer

        # Collect all intents (should be from orchestrator only)
        all_intents = []
        for output in all_outputs:
            all_intents.extend(output.intents)
        assert len(all_intents) == 1  # 1 from orchestrator

        # Verify sources
        assert all_events[0]["source"] == "effect"
        assert all_events[1]["source"] == "orchestrator"
        assert all_projections[0]["source"] == "reducer"
        assert all_intents[0]["source"] == "orchestrator"

    @pytest.mark.asyncio
    async def test_publish_order_with_causality_ids(
        self,
        mock_event_bus: Any,
    ) -> None:
        """
        Verify causality tracking fields are preserved in publishing order.

        Per OMN-941: Every output must include input_envelope_id and
        correlation_id for full causality tracing. These must be
        consistent across all outputs from the same handler invocation.
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        input_envelope_id = uuid4()
        correlation_id = uuid4()

        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="causality-handler",
            events=({"type": "Event1"}, {"type": "Event2"}),
            intents=({"type": "Intent1"},),
        )

        # Verify causality IDs are preserved
        assert output.input_envelope_id == input_envelope_id
        assert output.correlation_id == correlation_id
        # All outputs share the same causality context
        assert output.has_outputs()
        assert output.output_count() == 3

    @pytest.mark.asyncio
    async def test_node_kind_constraints_prevent_invalid_outputs(
        self,
        mock_event_bus: Any,
    ) -> None:
        """
        Verify node kind constraints prevent invalid output combinations.

        Per OMN-941: Each node kind has specific output restrictions:
        - REDUCER: projections only (no events, no intents, no result)
        - EFFECT: events only (no intents, no projections, no result)
        - COMPUTE: result value only (no events, no intents, no projections)
        - ORCHESTRATOR: events and intents only (no projections, no result)
        """
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        # Test REDUCER constraint - cannot emit events
        with pytest.raises(ValueError, match="REDUCER cannot emit events"):
            ModelHandlerOutput(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="bad-reducer",
                node_kind=EnumNodeKind.REDUCER,
                events=({"type": "InvalidEvent"},),
            )

        # Test REDUCER constraint - cannot emit intents
        with pytest.raises(ValueError, match="REDUCER cannot emit intents"):
            ModelHandlerOutput(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="bad-reducer",
                node_kind=EnumNodeKind.REDUCER,
                intents=({"type": "InvalidIntent"},),
            )

        # Test EFFECT constraint - cannot emit intents
        with pytest.raises(ValueError, match="EFFECT cannot emit intents"):
            ModelHandlerOutput(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="bad-effect",
                node_kind=EnumNodeKind.EFFECT,
                intents=({"type": "InvalidIntent"},),
            )

        # Test EFFECT constraint - cannot emit projections
        with pytest.raises(ValueError, match="EFFECT cannot emit projections"):
            ModelHandlerOutput(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="bad-effect",
                node_kind=EnumNodeKind.EFFECT,
                projections=({"type": "InvalidProjection"},),
            )

        # Test ORCHESTRATOR constraint - cannot emit projections
        with pytest.raises(ValueError, match="ORCHESTRATOR cannot emit projections"):
            ModelHandlerOutput(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="bad-orchestrator",
                node_kind=EnumNodeKind.ORCHESTRATOR,
                projections=({"type": "InvalidProjection"},),
            )
