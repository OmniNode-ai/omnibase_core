"""
Hybrid Event Bus Factory

Creates event bus instances with Kafka-first, EventBus-fallback strategy.
Supports both standalone creation and dependency injection integration.
"""

import os
from typing import Optional


def create_hybrid_event_bus() -> Optional[object]:
    """
    Create hybrid event bus with Kafka primary, EventBus fallback.

    Priority order:
    1. HybridEventRouter (if available) - handles Kafka/EventBus switching
    2. KafkaEventBusAdapter (if Kafka configured) - direct Kafka wrapper
    3. EventBusClient (fallback) - HTTP-based event bus
    4. None (both failed) - triggers error upstream

    Returns:
        Event bus implementation or None if all methods fail
    """
    # Check if Kafka is available via environment variables
    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if kafka_servers:
        # Kafka is configured - try to create KafkaProducer
        try:
            from omnibase_core.routers.hybrid_event_router import \
                HybridEventRouter

            # Use existing HybridEventRouter which implements proper fallback logic
            return HybridEventRouter()
        except ImportError:
            # HybridEventRouter not available - create simple Kafka wrapper
            try:
                from kafka import KafkaProducer

                from omnibase_core.adapters.kafka_event_bus_adapter import \
                    KafkaEventBusAdapter

                producer = KafkaProducer(
                    bootstrap_servers=kafka_servers,
                    value_serializer=lambda v: str(v).encode("utf-8"),
                )
                return KafkaEventBusAdapter(producer)
            except Exception:
                # Kafka creation failed - fall back to EventBus
                pass

    # Fallback to EventBusClient only when Kafka is not available
    try:
        from omnibase_core.services.event_bus_client import EventBusClient

        event_bus_url = os.getenv("EVENT_BUS_URL", "http://onex-event-bus:8080")
        return EventBusClient(base_url=event_bus_url)
    except Exception:
        # Both Kafka and EventBus failed - return None to trigger error
        return None


def get_event_bus_type_info(event_bus: object) -> dict:
    """
    Get diagnostic information about event bus instance.

    Args:
        event_bus: Event bus instance to analyze

    Returns:
        Dictionary with type information and capabilities
    """
    if event_bus is None:
        return {"type": "None", "module": None, "capabilities": []}

    info = {
        "type": type(event_bus).__name__,
        "module": getattr(event_bus, "__module__", "unknown"),
        "capabilities": [],
    }

    # Check for common event bus capabilities
    if hasattr(event_bus, "publish_event"):
        info["capabilities"].append("publish_event")
    if hasattr(event_bus, "subscribe"):
        info["capabilities"].append("subscribe")
    if hasattr(event_bus, "kafka_producer"):
        info["capabilities"].append("kafka_producer")
    if hasattr(event_bus, "hybrid_publisher_context"):
        info["capabilities"].append("hybrid_publishing")

    return info


def create_hybrid_event_bus_standalone() -> Optional[object]:
    """
    Standalone wrapper for create_hybrid_event_bus.

    Provides identical functionality to create_hybrid_event_bus with explicit
    standalone naming for container usage patterns.

    Returns:
        Event bus implementation or None if all methods fail
    """
    return create_hybrid_event_bus()
