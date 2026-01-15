"""
State model for reducer pattern.

Implements ProtocolState from omnibase_spi for proper protocol compliance.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_protocol_metadata import ModelGenericMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelState(BaseModel):
    """
    State model implementing ProtocolState protocol.

    Provides reducer state with metadata, versioning, and validation.

    Thread Safety:
        This model is NOT thread-safe due to mutable fields (version, last_updated)
        and validate_assignment=True which allows field modification after creation.

        - **NOT Safe**: Sharing instances across threads without synchronization
        - **NOT Safe**: Modifying fields from multiple threads concurrently
        - **Safe**: Reading fields after construction (before any modifications)

        For thread-safe state management, create new instances rather than modifying
        existing ones, or use external synchronization. See docs/guides/THREADING.md.
    """

    # ProtocolState required fields
    metadata: ModelGenericMetadata = Field(
        default_factory=lambda: ModelGenericMetadata(
            version=ModelSemVer(major=1, minor=0, patch=0)
        )
    )
    version: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )

    # ProtocolState required methods
    async def validate_state(self) -> bool:
        """Validate state consistency and integrity."""
        return self.is_consistent()

    def is_consistent(self) -> bool:
        """Check if state is internally consistent."""
        return self.version >= 0


# Export for use
__all__ = ["ModelState"]
