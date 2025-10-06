from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlMetadata(BaseModel):
    """Model for YAML files containing metadata."""

    model_config = ConfigDict(extra="allow")

    # Common metadata patterns
    metadata: dict[str, Any] | None = Field(None, description="Metadata section")
    title: str | None = Field(None, description="Optional title")
    description: str | None = Field(None, description="Optional description")
    author: str | None = Field(None, description="Optional author")
    version: str | None = Field(None, description="Optional version")
    created_at: str | None = Field(None, description="Optional creation timestamp")
    updated_at: str | None = Field(None, description="Optional update timestamp")
