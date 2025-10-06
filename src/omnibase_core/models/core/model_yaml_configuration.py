from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlConfiguration(BaseModel):
    """Model for YAML configuration files."""

    model_config = ConfigDict(extra="allow")

    # Common configuration patterns
    config: dict[str, Any] | None = Field(
        default=None, description="Configuration section"
    )
    settings: dict[str, Any] | None = Field(
        default=None, description="Settings section"
    )
    options: dict[str, Any] | None = Field(default=None, description="Options section")
    parameters: dict[str, Any] | None = Field(
        default=None, description="Parameters section"
    )
