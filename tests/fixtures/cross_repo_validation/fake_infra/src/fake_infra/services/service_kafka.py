"""Internal service - NOT for cross-repo import.

This is allowed to import from fake_core (infra depends on core).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fake_core.protocols.protocol_foo import ProtocolFoo


class ServiceKafka:
    """Internal Kafka service."""

    def __init__(self, foo: ProtocolFoo) -> None:
        self.foo = foo

    def publish(self, message: str) -> bool:
        """Publish message to Kafka."""
        return True
