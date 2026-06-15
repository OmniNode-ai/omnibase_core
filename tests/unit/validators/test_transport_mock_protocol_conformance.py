# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocol-conformance tests for transport-surface mock specs (OMN-13026).

For each Protocol defined on EventBus / transport surfaces, verify:
1. The Protocol class is importable from its canonical path.
2. AsyncMock(spec=<Protocol>) creates a valid spec-bound mock — the mock
   constructor does not raise.
3. The spec-bound mock *rejects* access to attributes that don't exist on the
   Protocol (spec enforcement in action).
4. The spec-bound mock *permits* calling methods that do exist on the Protocol.

These tests serve the DoD requirement: "one protocol-conformance test per
Protocol defined."  They are a guard against renaming / deleting Protocol
methods without updating callers' mocks, and they prove each Protocol is
suitable as an AsyncMock spec.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# ProtocolEventBusBase
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolEventBusBaseConformance:
    """ProtocolEventBusBase — publish surface spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_base import (  # noqa: F401
            ProtocolEventBusBase,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_base import (
            ProtocolEventBusBase,
        )

        mock = AsyncMock(spec=ProtocolEventBusBase)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_base import (
            ProtocolEventBusBase,
        )

        mock = AsyncMock(spec=ProtocolEventBusBase)
        with pytest.raises(AttributeError):
            _ = mock.this_method_does_not_exist_on_the_protocol  # type: ignore[attr-defined]

    def test_spec_permits_publish_method(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_base import (
            ProtocolEventBusBase,
        )

        mock = AsyncMock(spec=ProtocolEventBusBase)
        # 'publish' must exist on the protocol — accessing it must not raise.
        assert hasattr(mock, "publish")


# ---------------------------------------------------------------------------
# ProtocolEventBus
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolEventBusConformance:
    """ProtocolEventBus — composite bus spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus import (  # noqa: F401
            ProtocolEventBus,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus import (
            ProtocolEventBus,
        )

        mock = AsyncMock(spec=ProtocolEventBus)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus import (
            ProtocolEventBus,
        )

        mock = AsyncMock(spec=ProtocolEventBus)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_bus_method  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# ProtocolAsyncEventBus
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolAsyncEventBusConformance:
    """ProtocolAsyncEventBus — async publish surface spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_async_event_bus import (  # noqa: F401
            ProtocolAsyncEventBus,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_async_event_bus import (
            ProtocolAsyncEventBus,
        )

        mock = AsyncMock(spec=ProtocolAsyncEventBus)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_async_event_bus import (
            ProtocolAsyncEventBus,
        )

        mock = AsyncMock(spec=ProtocolAsyncEventBus)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_async_bus_method  # type: ignore[attr-defined]

    def test_spec_permits_publish_method(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_async_event_bus import (
            ProtocolAsyncEventBus,
        )

        mock = AsyncMock(spec=ProtocolAsyncEventBus)
        assert hasattr(mock, "publish")


# ---------------------------------------------------------------------------
# ProtocolEventBusPublisher
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolEventBusPublisherConformance:
    """ProtocolEventBusPublisher — publisher surface spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (  # noqa: F401
            ProtocolEventBusPublisher,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (
            ProtocolEventBusPublisher,
        )

        mock = AsyncMock(spec=ProtocolEventBusPublisher)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (
            ProtocolEventBusPublisher,
        )

        mock = AsyncMock(spec=ProtocolEventBusPublisher)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_publisher_method  # type: ignore[attr-defined]

    def test_spec_permits_publish_method(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (
            ProtocolEventBusPublisher,
        )

        mock = AsyncMock(spec=ProtocolEventBusPublisher)
        assert hasattr(mock, "publish")


# ---------------------------------------------------------------------------
# ProtocolEventBusSubscriber
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolEventBusSubscriberConformance:
    """ProtocolEventBusSubscriber — subscriber surface spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_subscriber import (  # noqa: F401
            ProtocolEventBusSubscriber,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_subscriber import (
            ProtocolEventBusSubscriber,
        )

        mock = AsyncMock(spec=ProtocolEventBusSubscriber)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_subscriber import (
            ProtocolEventBusSubscriber,
        )

        mock = AsyncMock(spec=ProtocolEventBusSubscriber)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_subscriber_method  # type: ignore[attr-defined]

    def test_spec_permits_subscribe_method(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_subscriber import (
            ProtocolEventBusSubscriber,
        )

        mock = AsyncMock(spec=ProtocolEventBusSubscriber)
        assert hasattr(mock, "subscribe")


# ---------------------------------------------------------------------------
# ProtocolEventBusLifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolEventBusLifecycleConformance:
    """ProtocolEventBusLifecycle — lifecycle surface spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (  # noqa: F401
            ProtocolEventBusLifecycle,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (
            ProtocolEventBusLifecycle,
        )

        mock = AsyncMock(spec=ProtocolEventBusLifecycle)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (
            ProtocolEventBusLifecycle,
        )

        mock = AsyncMock(spec=ProtocolEventBusLifecycle)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_lifecycle_method  # type: ignore[attr-defined]

    def test_spec_permits_start_method(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (
            ProtocolEventBusLifecycle,
        )

        mock = AsyncMock(spec=ProtocolEventBusLifecycle)
        assert hasattr(mock, "start")

    def test_spec_permits_shutdown_method(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_lifecycle import (
            ProtocolEventBusLifecycle,
        )

        mock = AsyncMock(spec=ProtocolEventBusLifecycle)
        assert hasattr(mock, "shutdown")


# ---------------------------------------------------------------------------
# ProtocolKafkaClient
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolKafkaClientConformance:
    """ProtocolKafkaClient — Kafka transport surface spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_kafka_client import (  # noqa: F401
            ProtocolKafkaClient,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_kafka_client import (
            ProtocolKafkaClient,
        )

        mock = AsyncMock(spec=ProtocolKafkaClient)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_kafka_client import (
            ProtocolKafkaClient,
        )

        mock = AsyncMock(spec=ProtocolKafkaClient)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_kafka_method  # type: ignore[attr-defined]

    def test_spec_permits_publish_method(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_kafka_client import (
            ProtocolKafkaClient,
        )

        mock = AsyncMock(spec=ProtocolKafkaClient)
        assert hasattr(mock, "publish")


# ---------------------------------------------------------------------------
# ProtocolDispatchBusClientTransport
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProtocolDispatchBusClientTransportConformance:
    """ProtocolDispatchBusClientTransport — dispatch transport surface spec conformance."""

    def test_importable(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_dispatch_bus_client_transport import (  # noqa: F401
            ProtocolDispatchBusClientTransport,
        )

    def test_asyncmock_spec_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_dispatch_bus_client_transport import (
            ProtocolDispatchBusClientTransport,
        )

        mock = AsyncMock(spec=ProtocolDispatchBusClientTransport)
        assert mock is not None

    def test_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_dispatch_bus_client_transport import (
            ProtocolDispatchBusClientTransport,
        )

        mock = AsyncMock(spec=ProtocolDispatchBusClientTransport)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_transport_method  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# MagicMock spec= smoke (ensures MagicMock also works for sync surfaces)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMagicMockSpecConformance:
    """Verify MagicMock(spec=) works on sync-capable transport protocols."""

    def test_magicmock_spec_event_bus_base_constructs(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_base import (
            ProtocolEventBusBase,
        )

        mock = MagicMock(spec=ProtocolEventBusBase)
        assert mock is not None

    def test_magicmock_spec_rejects_nonexistent_attribute(self) -> None:
        from omnibase_core.protocols.event_bus.protocol_event_bus_base import (
            ProtocolEventBusBase,
        )

        mock = MagicMock(spec=ProtocolEventBusBase)
        with pytest.raises(AttributeError):
            _ = mock.not_a_real_method_at_all  # type: ignore[attr-defined]
