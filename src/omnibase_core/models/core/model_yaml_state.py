from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelYamlState(BaseModel):
    """Model for YAML state files."""

    model_config = ConfigDict(extra="allow")

    # Common state patterns
    state: "SerializedDict | None" = Field(default=None, description="State section")
    status: str | None = Field(default=None, description="Status field")
    data: "SerializedDict | None" = Field(default=None, description="Data section")
