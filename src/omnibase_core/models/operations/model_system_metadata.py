"""
Strongly-typed system metadata structure.

Replaces dict[str, Any] usage in system metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.metadata.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)


class ModelSystemMetadata(BaseModel):
    """
    Strongly-typed system metadata.

    Replaces dict[str, Any] with structured system metadata model.
    """

    system_id: UUID = Field(
        default_factory=uuid4, description="System identifier (UUID format)"
    )
    system_name: str = Field(..., description="System name")
    version: ModelSemVer = Field(
        ..., description="System version in semantic version format"
    )
    deployment_id: UUID | None = Field(
        default=None, description="Deployment identifier (UUID format)"
    )

    # System health
    health_status: str = Field(default="unknown", description="System health status")
    last_health_check: datetime = Field(
        default_factory=datetime.now, description="Last health check"
    )
    uptime_seconds: int = Field(default=0, description="System uptime in seconds")

    # Configuration
    configuration_version: ModelSemVer = Field(
        default=ModelSemVer(major=1, minor=0, patch=0),
        description="Configuration version in semantic version format",
    )
    feature_flags: dict[str, bool] = Field(
        default_factory=dict, description="Feature flags"
    )
    environment_config: dict[str, str] = Field(
        default_factory=dict, description="Environment configuration"
    )


# Export for use
__all__ = ["ModelSystemMetadata"]
