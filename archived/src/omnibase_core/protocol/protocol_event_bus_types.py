from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_onex_event import OnexEvent


class EventBusCredentialsModel(BaseModel):
    """
    Canonical credentials model for event bus authentication/authorization.
    Supports token, username/password, and TLS certs for future event bus support.
    """

    token: str | None = Field(None, description="Bearer token or NATS token")
    username: str | None = Field(None, description="Username for authentication")
    password: str | None = Field(None, description="Password for authentication")
    cert: str | None = Field(None, description="PEM-encoded client certificate")
    key: str | None = Field(None, description="PEM-encoded client private key")
    ca: str | None = Field(None, description="PEM-encoded CA certificate")
    extra: dict[str, Any] | None = Field(
        None,
        description="Additional credentials or options",
    )


@runtime_checkable
class ProtocolEventBus(Protocol):
    """
    Canonical protocol for ONEX event bus (runtime/ placement).
    Defines publish/subscribe interface for event emission and handling.
    All event bus implementations must conform to this interface.
    Supports both synchronous and asynchronous methods for maximum flexibility.
    Implementations may provide either or both, as appropriate.
    Optionally supports clear() for test/lifecycle management.
    All event bus implementations must expose a unique, stable bus_id (str) for diagnostics, registry, and introspection.
    """

    def __init__(
        self,
        credentials: EventBusCredentialsModel | None = None,
        **kwargs,
    ): ...

    def publish(self, event: OnexEvent) -> None: ...

    async def publish_async(self, event: OnexEvent) -> None: ...

    def subscribe(self, callback: Callable[[OnexEvent], None]) -> None: ...

    async def subscribe_async(self, callback: Callable[[OnexEvent], None]) -> None: ...

    def unsubscribe(self, callback: Callable[[OnexEvent], None]) -> None: ...

    async def unsubscribe_async(
        self,
        callback: Callable[[OnexEvent], None],
    ) -> None: ...

    def clear(self) -> None: ...

    @property
    def bus_id(self) -> str:
        """
        Unique, stable identifier for this event bus instance (MUST be unique per bus, stable for its lifetime).
        """
        ...
