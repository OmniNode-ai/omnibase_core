from typing import Protocol, TypeVar, runtime_checkable

from omnibase_core.models.configuration.model_event_bus_config import (
    ModelModelEventBusConfig,
)
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus

TEventBus = TypeVar("TEventBus", bound=ProtocolEventBus)


@runtime_checkable
class ProtocolEventBusContextManager(Protocol[TEventBus]):
    """
    Protocol for async context managers that yield a ProtocolEventBus-compatible object.
    Used to abstract lifecycle management for event bus resources (e.g., Kafka).
    Implementations must support async context management and return a ProtocolEventBus on enter.
    """

    def __init__(self, config: ModelModelEventBusConfig): ...

    async def __aenter__(self) -> TEventBus: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...
