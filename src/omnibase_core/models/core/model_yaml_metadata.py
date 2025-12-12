from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelYamlMetadata(BaseModel):
    """Model for YAML files containing metadata."""

    model_config = ConfigDict(extra="allow")

    # Common metadata patterns
    metadata: "SerializedDict | None" = Field(
        default=None, description="Metadata section"
    )
    title: str | None = Field(default=None, description="Optional title")
    description: str | None = Field(default=None, description="Optional description")
    author: str | None = Field(default=None, description="Optional author")
    version: ModelSemVer | None = Field(default=None, description="Optional version")
    created_at: str | None = Field(
        default=None, description="Optional creation timestamp"
    )
    updated_at: str | None = Field(
        default=None, description="Optional update timestamp"
    )
