from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_yaml_section import ModelYamlSection


class ModelYamlConfiguration(BaseModel):
    """Model for YAML configuration files."""

    model_config = ConfigDict(extra="allow")

    # Common configuration patterns - use typed sections
    config: ModelYamlSection | None = Field(
        default=None, description="Configuration section"
    )
    settings: ModelYamlSection | None = Field(
        default=None, description="Settings section"
    )
    options: ModelYamlSection | None = Field(
        default=None, description="Options section"
    )
    parameters: ModelYamlSection | None = Field(
        default=None, description="Parameters section"
    )
