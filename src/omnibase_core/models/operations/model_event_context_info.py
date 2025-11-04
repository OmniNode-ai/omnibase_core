from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEventContextInfo(BaseModel):
    """Structured event context information."""

    correlation_id: UUID | None = Field(
        default=None,
        description="Event correlation identifier",
    )
    causation_id: UUID | None = Field(
        default=None,
        description="Event causation identifier",
    )
    session_id: UUID | None = Field(default=None, description="Session identifier")
    tenant_id: UUID | None = Field(default=None, description="Tenant identifier")
    environment: str = Field(default="", description="Environment context")
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Event schema version",
    )
