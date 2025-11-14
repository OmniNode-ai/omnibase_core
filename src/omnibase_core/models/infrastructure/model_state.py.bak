from __future__ import annotations

"""
State model for reducer pattern.

Implements ProtocolState from omnibase_spi for proper protocol compliance.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_protocol_metadata import ModelGenericMetadata


class ModelState(BaseModel):
    """
    State model implementing ProtocolState protocol.

    Provides reducer state with metadata, versioning, and validation.
    """

    # ProtocolState required fields
    metadata: ModelGenericMetadata = Field(default_factory=ModelGenericMetadata)
    version: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.now)

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # ProtocolState required methods
    async def validate_state(self) -> bool:
        """Validate state consistency and integrity."""
        return self.is_consistent()

    def is_consistent(self) -> bool:
        """Check if state is internally consistent."""
        return self.version >= 0


# Export for use
__all__ = ["ModelState"]
