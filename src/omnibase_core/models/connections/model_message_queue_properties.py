"""
Message queue connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ModelMessageQueueProperties(BaseModel):
    """Message queue/broker-specific connection properties."""

    # Entity references with UUID + display name pattern
    queue_id: UUID | None = Field(default=None, description="Queue UUID reference")
    queue_display_name: str | None = Field(
        default=None,
        description="Queue display name",
    )
    exchange_id: UUID | None = Field(
        default=None,
        description="Exchange UUID reference",
    )
    exchange_display_name: str | None = Field(
        default=None,
        description="Exchange display name",
    )

    # Queue configuration
    routing_key: str | None = Field(default=None, description="Routing key")
    durable: bool | None = Field(default=None, description="Durable queue/exchange")

    def get_queue_identifier(self) -> str | None:
        """Get queue identifier for display purposes."""
        if self.queue_display_name:
            return self.queue_display_name
        if self.queue_id:
            return str(self.queue_id)
        return None

    def get_exchange_identifier(self) -> str | None:
        """Get exchange identifier for display purposes."""
        if self.exchange_display_name:
            return self.exchange_display_name
        if self.exchange_id:
            return str(self.exchange_id)
        return None


# Export the model
__all__ = ["ModelMessageQueueProperties"]
