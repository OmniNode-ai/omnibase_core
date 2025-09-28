"""
Execution summary model.

Typed execution summary model with result metadata.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Configurable


class ModelExecutionSummary(BaseModel):
    """Execution summary model with typed fields.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    execution_id: UUID = Field(description="Execution identifier")
    success: bool = Field(description="Whether execution was successful")
    duration_ms: int | None = Field(description="Duration in milliseconds")
    warning_count: int = Field(description="Number of warnings")
    has_metadata: bool = Field(description="Whether metadata exists")
    completed: bool = Field(description="Whether execution is completed")

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelExecutionSummary"]
