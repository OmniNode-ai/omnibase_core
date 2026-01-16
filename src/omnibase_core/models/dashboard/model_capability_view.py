"""Capability view model for dashboard UI projection."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ("ModelCapabilityView",)


class ModelCapabilityView(BaseModel):
    """UI projection of capability data.

    Thin view model containing only fields needed for dashboard rendering.
    References canonical ModelCapability by ID.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    capability_id: UUID = Field(..., description="Unique capability identifier")
    name: str = Field(..., description="Capability name")
    namespace: str | None = Field(default=None, description="Capability namespace")
    display_name: str | None = Field(default=None, description="Human-readable name")
    version: str | None = Field(default=None, description="Version string")
    description: str | None = Field(default=None, description="Short description")
    category: str | None = Field(default=None, description="Capability category")
    is_deprecated: bool = Field(default=False, description="Deprecation status")
    tags: tuple[str, ...] = Field(default=(), description="Associated tags")
