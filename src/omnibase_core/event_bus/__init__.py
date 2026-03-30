# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Core event bus implementations.

Provides EventBusInmemory, a zero-dependency in-memory event bus that
conforms to ProtocolEventBus via duck typing. Designed for local
development, testing, and single-process runtimes where a full
Kafka/Redpanda broker is unnecessary.
"""

from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory

__all__ = ["EventBusInmemory"]
