from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelMessageHeaders(BaseModel):
    """Structured message headers."""

    content_type: str = Field(
        default="application/json",
        description="Message content type",
    )
    content_encoding: str = Field(default="utf-8", description="Content encoding")
    correlation_id: UUID | None = Field(
        default=None,
        description="Message correlation identifier",
    )
    reply_to: str = Field(default="", description="Reply destination")
    message_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Message schema version",
    )
    source_system: str = Field(default="", description="Source system identifier")
    destination_system: str = Field(
        default="",
        description="Destination system identifier",
    )
    security_token: str = Field(default="", description="Security authorization token")
    compression: str = Field(default="none", description="Message compression type")
    custom_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom headers",
    )
