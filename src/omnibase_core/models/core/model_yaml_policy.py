from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlPolicy(BaseModel):
    """Model for YAML policy files."""

    model_config = ConfigDict(extra="allow")

    # Common policy patterns
    policy: dict[str, Any] | None = Field(default=None, description="Policy definition")
    rules: list[dict[str, Any]] | None = Field(default=None, description="Policy rules")
    permissions: dict[str, Any] | None = Field(default=None, description="Permissions")
    restrictions: dict[str, Any] | None = Field(
        default=None, description="Restrictions"
    )
