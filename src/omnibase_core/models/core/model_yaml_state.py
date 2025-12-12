from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlState(BaseModel):
    """Model for YAML state files."""

    model_config = ConfigDict(extra="allow")

    # Common state patterns
    state: dict[str, Any] | None = Field(default=None, description="State section")
    status: str | None = Field(default=None, description="Status field")
    data: dict[str, Any] | None = Field(default=None, description="Data section")
