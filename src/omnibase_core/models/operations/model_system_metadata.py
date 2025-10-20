from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.primitives.model_semver import ModelSemVer

"""
Strongly-typed system metadata structure.

Replaces dict[str, Any] usage in system metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel


class ModelSystemMetadata(BaseModel):
    """
    Strongly-typed system metadata.

    Replaces dict[str, Any] with structured system metadata model.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    system_id: UUID = Field(
        default_factory=uuid4,
        description="System identifier (UUID format)",
    )
    system_name: str = Field(default=..., description="System name")
    version: ModelSemVer = Field(
        default=...,
        description="System version in semantic version format",
    )
    deployment_id: UUID | None = Field(
        default=None,
        description="Deployment identifier (UUID format)",
    )

    # System health
    health_status: str = Field(default="unknown", description="System health status")
    last_health_check: datetime = Field(
        default_factory=datetime.now,
        description="Last health check",
    )
    uptime_seconds: int = Field(default=0, description="System uptime in seconds")

    # Configuration
    configuration_version: ModelSemVer = Field(
        default=ModelSemVer(major=1, minor=0, patch=0),
        description="Configuration version in semantic version format",
    )
    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flags",
    )
    environment_config: dict[str, str] = Field(
        default_factory=dict,
        description="Environment configuration",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = ["ModelSystemMetadata"]
