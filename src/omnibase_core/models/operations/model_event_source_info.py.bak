from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEventSourceInfo(BaseModel):
    """Structured event source information."""

    service_name: str = Field(default="", description="Source service name")
    service_version: ModelSemVer | None = Field(
        default=None,
        description="Source service version",
    )
    host_name: str = Field(default="", description="Source host name")
    instance_id: UUID | None = Field(
        default=None,
        description="Source instance identifier",
    )
    request_id: UUID | None = Field(
        default=None,
        description="Originating request identifier",
    )
    user_agent: str = Field(default="", description="User agent information")
