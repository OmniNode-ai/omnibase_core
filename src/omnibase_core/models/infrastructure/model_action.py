from __future__ import annotations

"""
Action model for reducer pattern.

Implements ProtocolAction from omnibase_spi.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_action_payload import ModelActionPayload


class ModelAction(BaseModel):
    """
    Action model implementing ProtocolAction protocol.

    Provides structured actions with type, payload, and timestamp.
    """

    type: str = Field(description="Action type")
    payload: ModelActionPayload = Field(default_factory=lambda: ModelActionPayload())
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # ProtocolAction required methods
    async def validate_action(self) -> bool:
        """Validate action structure and payload."""
        return self.is_executable() and await self.payload.validate_payload()

    def is_executable(self) -> bool:
        """Check if action can be executed."""
        return self.type != ""


# Export for use
__all__ = ["ModelAction"]
