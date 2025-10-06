from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlRegistry(BaseModel):
    """Model for YAML files that define registries or lists of items."""

    model_config = ConfigDict(extra="allow")

    # Common registry patterns
    registry: dict[str, Any] | None = Field(None, description="Registry section")
    items: list[dict[str, Any]] | None = Field(None, description="Items list")
    entries: list[dict[str, Any]] | None = Field(None, description="Entries list")
    actions: list[dict[str, Any]] | None = Field(None, description="Actions list")
    commands: list[dict[str, Any]] | None = Field(None, description="Commands list")
