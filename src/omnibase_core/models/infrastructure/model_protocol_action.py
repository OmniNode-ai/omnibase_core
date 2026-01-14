"""
Action model for reducer pattern.

Implements ProtocolAction from omnibase_spi.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_action_payload import ModelActionPayload


class ModelAction(BaseModel):
    """
    Action model implementing ProtocolAction protocol.

    Provides structured actions with type, payload, and timestamp.
    """

    type: str = Field(description="Action type")
    payload: ModelActionPayload | None = Field(
        default=None,
        description="Optional action payload with execution context",
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # ProtocolAction required methods
    async def validate_action(self) -> bool:
        """Validate action structure and payload."""
        # Payload validation is optional if no payload present
        return self.is_executable()

    def is_executable(self) -> bool:
        """Check if action can be executed."""
        return self.type != ""


# Export for use
__all__ = ["ModelAction"]
