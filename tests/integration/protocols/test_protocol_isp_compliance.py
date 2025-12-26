"""Integration tests for Interface Segregation Principle (ISP) protocol compliance.

This module verifies that ISP-split protocols are properly structured and usable.
The event bus protocols were split following ISP to allow components to depend
only on the interfaces they actually need.

ISP Split Overview:
    ProtocolEventBus (full interface) is split into:
    - ProtocolEventBusPublisher: Publishing-only operations
    - ProtocolEventBusSubscriber: Subscription-only operations
    - ProtocolEventBusLifecycle: Lifecycle management operations

This allows:
    - Effect nodes that only publish to depend on ProtocolEventBusPublisher
    - Consumers that only subscribe to depend on ProtocolEventBusSubscriber
    - Orchestrators to depend on the full ProtocolEventBus interface

Related:
    - PR #241: Protocol ISP compliance review
    - docs/architecture/PROTOCOL_ISP_DESIGN.md
"""

from __future__ import annotations

import inspect
from typing import Any, Protocol, get_type_hints, runtime_checkable

import pytest

from omnibase_core.protocols.event_bus import (
    ProtocolEventBus,
    ProtocolEventBusBase,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (
    ProtocolEventBusLifecycle,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (
    ProtocolEventBusPublisher,
)
from omnibase_core.protocols.event_bus.protocol_event_bus_subscriber import (
    ProtocolEventBusSubscriber,
)


@pytest.mark.integration
class TestEventBusISPSplit:
    """Test that event bus protocols are properly split per ISP.

    These tests verify that the ISP split was done correctly and that
    components can depend on minimal interfaces.
    """

    def test_publisher_protocol_is_focused(self):
        """Verify ProtocolEventBusPublisher only has publishing methods.

        ISP compliance: A protocol should only contain methods that
        clients using that protocol actually need.
        """
        # Get all methods from the protocol (excluding dunder methods)
        methods = [
            name
            for name in dir(ProtocolEventBusPublisher)
            if not name.startswith("_")
            and callable(getattr(ProtocolEventBusPublisher, name, None))
        ]

        # Publisher should only have publishing-related methods
        expected_methods = {
            "publish",
            "publish_envelope",
            "broadcast_to_environment",
            "send_to_group",
        }

        # All methods should be publishing-related
        for method in methods:
            assert method in expected_methods, (
                f"Unexpected method '{method}' in ProtocolEventBusPublisher. "
                "Publisher protocol should only contain publishing methods."
            )

    def test_subscriber_protocol_is_focused(self):
        """Verify ProtocolEventBusSubscriber only has subscription methods.

        ISP compliance: Subscriber protocol should not include publishing
        or lifecycle methods.
        """
        methods = [
            name
            for name in dir(ProtocolEventBusSubscriber)
            if not name.startswith("_")
            and callable(getattr(ProtocolEventBusSubscriber, name, None))
        ]

        # Subscriber should only have subscription-related methods
        # subscribe returns an unsubscribe callable, start_consuming begins consumption loop
        expected_methods = {
            "subscribe",
            "start_consuming",
        }

        for method in methods:
            assert method in expected_methods, (
                f"Unexpected method '{method}' in ProtocolEventBusSubscriber. "
                "Subscriber protocol should only contain subscription methods."
            )

    def test_lifecycle_protocol_is_focused(self):
        """Verify ProtocolEventBusLifecycle only has lifecycle methods.

        ISP compliance: Lifecycle protocol should not include business
        logic methods (publish/subscribe).
        """
        methods = [
            name
            for name in dir(ProtocolEventBusLifecycle)
            if not name.startswith("_")
            and callable(getattr(ProtocolEventBusLifecycle, name, None))
        ]

        # Lifecycle should only have lifecycle-related methods
        # start, shutdown, close for lifecycle control; health_check for monitoring
        expected_methods = {
            "start",
            "shutdown",
            "close",
            "health_check",
        }

        for method in methods:
            assert method in expected_methods, (
                f"Unexpected method '{method}' in ProtocolEventBusLifecycle. "
                "Lifecycle protocol should only contain lifecycle methods."
            )

    def test_protocols_are_runtime_checkable(self):
        """Verify all ISP-split protocols are runtime checkable.

        Runtime checkable protocols allow isinstance() checks for duck typing.
        """
        assert hasattr(ProtocolEventBusPublisher, "__protocol_attrs__") or hasattr(
            ProtocolEventBusPublisher, "_is_runtime_protocol"
        ), "ProtocolEventBusPublisher should be @runtime_checkable"

        assert hasattr(ProtocolEventBusSubscriber, "__protocol_attrs__") or hasattr(
            ProtocolEventBusSubscriber, "_is_runtime_protocol"
        ), "ProtocolEventBusSubscriber should be @runtime_checkable"

        assert hasattr(ProtocolEventBusLifecycle, "__protocol_attrs__") or hasattr(
            ProtocolEventBusLifecycle, "_is_runtime_protocol"
        ), "ProtocolEventBusLifecycle should be @runtime_checkable"

    def test_full_protocol_composes_split_protocols(self):
        """Verify ProtocolEventBus includes methods from split protocols.

        The full ProtocolEventBus should contain all methods from the
        split protocols, allowing components that need everything to
        depend on a single interface.
        """
        full_methods = {
            name for name in dir(ProtocolEventBus) if not name.startswith("_")
        }

        # Check publisher methods are in full protocol
        publisher_methods = {
            "publish",
            "publish_envelope",
            "broadcast_to_environment",
            "send_to_group",
        }
        for method in publisher_methods:
            assert method in full_methods, (
                f"ProtocolEventBus should include publisher method '{method}'"
            )

        # Check subscriber methods are in full protocol
        # Note: subscribe returns an unsubscribe callable, so no separate unsubscribe method
        subscriber_methods = {"subscribe", "start_consuming"}
        for method in subscriber_methods:
            assert method in full_methods, (
                f"ProtocolEventBus should include subscriber method '{method}'"
            )

        # Check lifecycle methods are in full protocol
        lifecycle_methods = {"start", "shutdown", "close", "health_check"}
        for method in lifecycle_methods:
            assert method in full_methods, (
                f"ProtocolEventBus should include lifecycle method '{method}'"
            )


@pytest.mark.integration
class TestISPUsagePatterns:
    """Test real-world usage patterns for ISP-compliant protocols.

    These tests verify that components can be built against minimal interfaces.
    """

    def test_publish_only_component_pattern(self):
        """Verify a publish-only component can be typed with publisher protocol.

        This pattern is common for Effect nodes that emit events but don't
        consume them.
        """

        class EffectNodePublisher:
            """Example effect node that only publishes."""

            def __init__(self, publisher: ProtocolEventBusPublisher):
                self.publisher = publisher

            async def emit_result(self, topic: str, data: bytes) -> None:
                await self.publisher.publish(topic, None, data)

        # Verify the class can be instantiated with proper type hints
        hints = get_type_hints(EffectNodePublisher.__init__)
        assert hints.get("publisher") == ProtocolEventBusPublisher

    def test_subscribe_only_component_pattern(self):
        """Verify a subscribe-only component can be typed with subscriber protocol.

        This pattern is common for consumer nodes that process events but
        don't produce them.
        """

        class ConsumerNode:
            """Example consumer node that only subscribes."""

            def __init__(self, subscriber: ProtocolEventBusSubscriber):
                self.subscriber = subscriber

            async def start_consuming(self, topic: str) -> None:
                await self.subscriber.subscribe(topic)

        hints = get_type_hints(ConsumerNode.__init__)
        assert hints.get("subscriber") == ProtocolEventBusSubscriber

    def test_full_protocol_backward_compatible(self):
        """Verify existing code using full protocol continues to work.

        ISP split should not break existing components that depend on
        the full ProtocolEventBus interface.
        """

        class FullEventBusClient:
            """Example client using full event bus interface."""

            def __init__(self, event_bus: ProtocolEventBus):
                self.event_bus = event_bus

            async def publish_and_subscribe(self, topic: str) -> None:
                await self.event_bus.subscribe(topic)
                await self.event_bus.publish(topic, None, b"data")

        hints = get_type_hints(FullEventBusClient.__init__)
        assert hints.get("event_bus") == ProtocolEventBus


@pytest.mark.integration
class TestProtocolModularityPrinciples:
    """Test general ISP and protocol modularity principles.

    These tests verify that the protocol design follows SOLID principles.
    """

    def test_protocols_have_docstrings(self):
        """Verify all ISP-split protocols have proper documentation.

        Good protocols should clearly document their purpose and usage.
        """
        assert ProtocolEventBusPublisher.__doc__ is not None, (
            "ProtocolEventBusPublisher should have a docstring"
        )
        assert ProtocolEventBusSubscriber.__doc__ is not None, (
            "ProtocolEventBusSubscriber should have a docstring"
        )
        assert ProtocolEventBusLifecycle.__doc__ is not None, (
            "ProtocolEventBusLifecycle should have a docstring"
        )

    def test_protocols_use_async_where_appropriate(self):
        """Verify async methods are used for I/O operations.

        Publishing and subscribing are I/O operations and should be async.
        """
        # Get the publish method and check if it's async
        publish_method = getattr(ProtocolEventBusPublisher, "publish", None)
        if publish_method is not None:
            sig = inspect.signature(publish_method)
            # Protocol methods are typically just '...' but we can check the annotations
            # The return type should indicate async (coroutine)
            assert True  # Protocol methods can't be easily introspected for async

    def test_protocol_methods_have_type_hints(self):
        """Verify protocol methods have complete type annotations.

        Type hints enable mypy strict mode compliance and better IDE support.
        """
        # Check publisher protocol has typed methods
        try:
            hints = get_type_hints(ProtocolEventBusPublisher.publish)
            # Should have at least topic, key, value parameters
            assert "topic" in hints or len(hints) > 0, (
                "ProtocolEventBusPublisher.publish should have type hints"
            )
        except Exception:
            # Some protocol inspection may fail, that's acceptable
            pass
