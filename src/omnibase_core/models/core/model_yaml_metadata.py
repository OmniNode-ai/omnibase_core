from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelYamlMetadata(BaseModel):
    """Model for YAML files containing metadata."""

    model_config = ConfigDict(extra="allow")

    # Common metadata patterns
    metadata: dict[str, Any] | None = Field(
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
