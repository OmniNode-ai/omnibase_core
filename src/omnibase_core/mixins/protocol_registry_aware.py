from typing import Protocol

from omnibase_spi.protocols.container import ProtocolRegistry


class ProtocolRegistryAware(Protocol):
    """Protocol for classes that can accept a registry."""

    registry: ProtocolRegistry | None
