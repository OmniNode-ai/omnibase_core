from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelYamlDictionary(BaseModel):
    """Model for YAML files that are primarily key-value dictionaries."""

    model_config = ConfigDict(extra="allow")
    name: str | None = Field(default=None, description="Optional name field")
    version: ModelSemVer | None = Field(
        default=None, description="Optional version field"
    )
    description: str | None = Field(
        default=None, description="Optional description field"
    )
