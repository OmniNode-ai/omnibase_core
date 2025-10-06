from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlDictionary(BaseModel):
    """Model for YAML files that are primarily key-value dictionaries."""

    model_config = ConfigDict(extra="allow")

    # Common dictionary patterns in YAML files
    name: str | None = Field(default=None, description="Optional name field")
    version: str | None = Field(default=None, description="Optional version field")
    description: str | None = Field(
        default=None, description="Optional description field"
    )
