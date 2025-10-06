from __future__ import annotations

"""
Protocol for synchronous event bus.
"""


from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.core.model_onex_event import ModelOnexEvent
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


@runtime_checkable
class ProtocolEventBus(Protocol):
    """Protocol for synchronous event bus."""

    def publish(self, event: "ModelOnexEvent") -> None: ...

    def publish_async(self, envelope: "ModelEventEnvelope") -> None: ...
