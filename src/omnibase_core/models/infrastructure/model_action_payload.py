from __future__ import annotations

"""
Action payload model for reducer pattern.

Implements ProtocolActionPayload from omnibase_spi.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelActionPayload(BaseModel):
    """
    Action payload implementing ProtocolActionPayload protocol.

    Provides structured payload with target, operation, and parameters.
    """

    target_id: UUID = Field(
        default_factory=uuid4, description="Target entity identifier"
    )
    operation: str = Field(default="", description="Operation to perform")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Operation parameters"
    )

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # ProtocolActionPayload required methods
    async def validate_payload(self) -> bool:
        """Validate payload structure and parameters."""
        return self.has_valid_parameters()

    def has_valid_parameters(self) -> bool:
        """Check if parameters are valid."""
        return self.target_id != "" and self.operation != ""


# Export for use
__all__ = ["ModelActionPayload"]
