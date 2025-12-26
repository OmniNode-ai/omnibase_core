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
    - docs/guides/ISP_PROTOCOL_MIGRATION.md
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import get_type_hints

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
from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
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
                self._unsubscribe: Callable[[], Awaitable[None]] | None = None

            async def start_consuming(self, topic: str) -> None:
                async def handler(msg: ProtocolEventMessage) -> None:
                    pass  # Process message

                self._unsubscribe = await self.subscriber.subscribe(
                    topic, "consumer-group", handler
                )

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
                self._unsubscribe: Callable[[], Awaitable[None]] | None = None

            async def publish_and_subscribe(self, topic: str) -> None:
                async def handler(msg: ProtocolEventMessage) -> None:
                    pass  # Process message

                self._unsubscribe = await self.event_bus.subscribe(
                    topic, "client-group", handler
                )
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
        """Verify I/O methods have proper async-compatible type signatures.

        Publishing and subscribing are I/O operations. We verify they have
        proper return type annotations that indicate async usage (either
        None for void async methods, or Awaitable types).

        Note: Protocol methods cannot be directly introspected for `async def`
        at runtime; async enforcement is done by type checkers (mypy).
        """
        # Import types needed for forward reference resolution
        from omnibase_core.protocols.event_bus.protocol_event_envelope import (
            ProtocolEventEnvelope,
        )

        # Build namespace for resolving forward references
        forward_ref_ns = {
            "ProtocolEventEnvelope": ProtocolEventEnvelope,
        }

        # Define I/O methods with their expected return type patterns
        # (protocol, method_name, is_void_async) - void async methods return None
        io_methods = [
            (ProtocolEventBusPublisher, "publish", True),  # async def -> None
            (ProtocolEventBusPublisher, "publish_envelope", True),  # async def -> None
            (ProtocolEventBusSubscriber, "subscribe", False),  # async def -> Callable
            (ProtocolEventBusLifecycle, "start", True),  # async def -> None
            (ProtocolEventBusLifecycle, "shutdown", True),  # async def -> None
        ]

        for protocol, method_name, is_void_async in io_methods:
            method = getattr(protocol, method_name, None)
            assert method is not None, f"{protocol.__name__}.{method_name} should exist"

            # Get the return type annotation with forward reference resolution
            try:
                hints = get_type_hints(
                    method, globalns=forward_ref_ns, include_extras=True
                )
            except NameError:
                # If we still can't resolve, try with the protocol's module globals
                module = __import__(protocol.__module__, fromlist=[""])
                hints = get_type_hints(
                    method,
                    globalns={**vars(module), **forward_ref_ns},
                    include_extras=True,
                )

            return_type = hints.get("return")

            if is_void_async:
                # Void async methods should return None
                assert return_type is type(None), (
                    f"{protocol.__name__}.{method_name} is a void async method, "
                    f"expected return type None, got: {return_type}"
                )
            else:
                # Non-void async methods should have a specific return type
                # (e.g., subscribe returns Callable[[], Awaitable[None]])
                assert return_type is not None, (
                    f"{protocol.__name__}.{method_name} should have a return type annotation"
                )

    def test_protocol_methods_have_type_hints(self):
        """Verify protocol methods have complete type annotations.

        Type hints enable mypy strict mode compliance and better IDE support.
        """
        # Import types needed for forward reference resolution
        from omnibase_core.protocols.event_bus.protocol_event_envelope import (
            ProtocolEventEnvelope,
        )

        # Build namespace for resolving forward references
        forward_ref_ns = {
            "ProtocolEventEnvelope": ProtocolEventEnvelope,
        }

        # Define required type hints for each protocol method
        # Each tuple: (protocol, method_name, required_params)
        methods_to_check = [
            (ProtocolEventBusPublisher, "publish", ["topic", "key", "value"]),
            (ProtocolEventBusPublisher, "publish_envelope", ["envelope", "topic"]),
            (
                ProtocolEventBusSubscriber,
                "subscribe",
                ["topic", "group_id", "on_message"],
            ),
            (ProtocolEventBusLifecycle, "start", []),
            (ProtocolEventBusLifecycle, "shutdown", []),
        ]

        errors: list[str] = []
        for protocol, method_name, required_params in methods_to_check:
            method = getattr(protocol, method_name, None)
            if method is None:
                errors.append(f"{protocol.__name__}.{method_name} not found")
                continue

            try:
                # Try with forward reference namespace first
                hints = get_type_hints(
                    method, globalns=forward_ref_ns, include_extras=True
                )
            except NameError:
                # If forward refs still can't resolve, try with module globals
                try:
                    module = __import__(protocol.__module__, fromlist=[""])
                    hints = get_type_hints(
                        method,
                        globalns={**vars(module), **forward_ref_ns},
                        include_extras=True,
                    )
                except Exception as e:
                    errors.append(
                        f"{protocol.__name__}.{method_name} type hints not resolvable: {e}"
                    )
                    continue
            except Exception as e:
                errors.append(
                    f"{protocol.__name__}.{method_name} type hints not resolvable: {e}"
                )
                continue

            # Check required parameters have type hints
            for param in required_params:
                if param not in hints:
                    errors.append(
                        f"{protocol.__name__}.{method_name} missing type hint for '{param}'"
                    )

            # Verify return type is annotated
            if "return" not in hints:
                errors.append(
                    f"{protocol.__name__}.{method_name} missing return type annotation"
                )

        assert not errors, "Type hint issues found:\n" + "\n".join(
            f"  - {e}" for e in errors
        )


@pytest.mark.integration
class TestTypedDictEventBusHealth:
    """Test TypedDictEventBusHealth for event bus health check return type.

    The TypedDictEventBusHealth provides typed structure for health check
    results from ProtocolEventBusLifecycle.health_check().
    """

    def test_typed_dict_has_required_fields(self):
        """Verify TypedDictEventBusHealth has required fields.

        Required fields (healthy, connected) must always be present.
        """
        from typing import get_type_hints

        from omnibase_core.types.typed_dict import TypedDictEventBusHealth

        # Verify required keys exist in the TypedDict (resolve forward refs)
        hints = get_type_hints(TypedDictEventBusHealth, include_extras=True)
        assert "healthy" in hints, "healthy is a required field"
        assert "connected" in hints, "connected is a required field"

        # Verify types (get origin for NotRequired wrapper)
        from typing import get_origin

        # Required fields should be plain bool (not wrapped in NotRequired)
        assert hints["healthy"] is bool, "healthy should be bool type"
        assert hints["connected"] is bool, "connected should be bool type"

    def test_typed_dict_has_optional_fields(self):
        """Verify TypedDictEventBusHealth has expected optional fields.

        Optional fields provide additional context about event bus health.
        """
        from typing import get_type_hints

        from omnibase_core.types.typed_dict import TypedDictEventBusHealth

        hints = get_type_hints(TypedDictEventBusHealth, include_extras=True)

        # Check that optional fields are present
        optional_fields = ["latency_ms", "pending_messages", "error", "status"]
        for field in optional_fields:
            assert field in hints, f"{field} should be an optional field"

    def test_typed_dict_usage_example(self):
        """Verify TypedDictEventBusHealth can be used as expected.

        This test documents the correct usage pattern for the TypedDict.
        """
        from omnibase_core.types.typed_dict import TypedDictEventBusHealth

        # Minimal valid health check result (required fields only)
        minimal_result: TypedDictEventBusHealth = {
            "healthy": True,
            "connected": True,
        }
        assert minimal_result["healthy"] is True
        assert minimal_result["connected"] is True

        # Full health check result with optional fields
        full_result: TypedDictEventBusHealth = {
            "healthy": True,
            "connected": True,
            "latency_ms": 5.2,
            "pending_messages": 0,
            "status": "connected",
        }
        assert full_result["latency_ms"] == 5.2
        assert full_result["pending_messages"] == 0

        # Unhealthy result with error
        error_result: TypedDictEventBusHealth = {
            "healthy": False,
            "connected": False,
            "error": "Connection refused",
        }
        assert error_result["healthy"] is False
        assert error_result.get("error") == "Connection refused"

    def test_lifecycle_protocol_uses_typed_dict(self):
        """Verify ProtocolEventBusLifecycle.health_check uses TypedDictEventBusHealth.

        This ensures the protocol method return type is properly typed.
        """
        from typing import get_type_hints

        from omnibase_core.protocols.event_bus import ProtocolEventBusLifecycle
        from omnibase_core.types.typed_dict import TypedDictEventBusHealth

        # Get the health_check method
        health_check = getattr(ProtocolEventBusLifecycle, "health_check", None)
        assert health_check is not None, "health_check method should exist"

        # Resolve type hints with forward reference namespace
        # (TypedDictEventBusHealth is imported under TYPE_CHECKING in the protocol)
        forward_ref_ns = {
            "TypedDictEventBusHealth": TypedDictEventBusHealth,
        }
        hints = get_type_hints(health_check, globalns=forward_ref_ns)
        assert "return" in hints, "health_check should have return type annotation"

        # The return type should be TypedDictEventBusHealth
        return_type = hints["return"]
        assert return_type is TypedDictEventBusHealth, (
            f"health_check should return TypedDictEventBusHealth, got {return_type}"
        )


@pytest.mark.integration
class TestISPIndependentImplementation:
    """Test that ISP-split protocols can be implemented independently.

    This verifies the Interface Segregation Principle is correctly applied:
    each split protocol can be implemented without implementing the others.
    """

    def test_can_implement_publisher_only(self):
        """Verify a class can implement only ProtocolEventBusPublisher.

        This pattern is common for Effect nodes that emit events but
        don't consume them.
        """
        from collections.abc import Awaitable, Callable

        from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher
        from omnibase_core.protocols.event_bus.protocol_event_envelope import (
            ProtocolEventEnvelope,
        )

        class PublisherOnlyImpl:
            """Implementation that only publishes events."""

            async def publish(
                self, topic: str, key: bytes | None, value: bytes
            ) -> None:
                pass

            async def publish_envelope(
                self, envelope: ProtocolEventEnvelope, topic: str | None = None
            ) -> None:
                pass

            async def broadcast_to_environment(
                self, topic: str, key: bytes | None, value: bytes
            ) -> None:
                pass

            async def send_to_group(
                self, group: str, topic: str, key: bytes | None, value: bytes
            ) -> None:
                pass

        # Verify it's a valid ProtocolEventBusPublisher
        instance = PublisherOnlyImpl()
        assert isinstance(instance, ProtocolEventBusPublisher)

    def test_can_implement_subscriber_only(self):
        """Verify a class can implement only ProtocolEventBusSubscriber.

        This pattern is common for consumer nodes that only receive events.
        """
        from collections.abc import Awaitable, Callable

        from omnibase_core.protocols.event_bus import ProtocolEventBusSubscriber
        from omnibase_core.protocols.event_bus.protocol_event_message import (
            ProtocolEventMessage,
        )

        class SubscriberOnlyImpl:
            """Implementation that only subscribes to events."""

            async def subscribe(
                self,
                topic: str,
                group_id: str,
                on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
            ) -> Callable[[], Awaitable[None]]:
                async def unsubscribe() -> None:
                    pass

                return unsubscribe

            async def start_consuming(self) -> None:
                pass

        # Verify it's a valid ProtocolEventBusSubscriber
        instance = SubscriberOnlyImpl()
        assert isinstance(instance, ProtocolEventBusSubscriber)

    def test_can_implement_lifecycle_only(self):
        """Verify a class can implement only ProtocolEventBusLifecycle.

        This pattern is common for lifecycle managers and health checkers.
        """
        from omnibase_core.protocols.event_bus import ProtocolEventBusLifecycle
        from omnibase_core.types.typed_dict import TypedDictEventBusHealth

        class LifecycleOnlyImpl:
            """Implementation that only manages lifecycle."""

            async def start(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

            async def close(self) -> None:
                pass

            async def health_check(self) -> TypedDictEventBusHealth:
                return {"healthy": True, "connected": True}

        # Verify it's a valid ProtocolEventBusLifecycle
        instance = LifecycleOnlyImpl()
        assert isinstance(instance, ProtocolEventBusLifecycle)
