from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelYamlRegistry(BaseModel):
    """Model for YAML files that define registries or lists of items."""

    model_config = ConfigDict(extra="allow")

    # Common registry patterns
    registry: "SerializedDict | None" = Field(
        default=None, description="Registry section"
    )
    items: "list[SerializedDict] | None" = Field(default=None, description="Items list")
    entries: "list[SerializedDict] | None" = Field(
        default=None, description="Entries list"
    )
    actions: "list[SerializedDict] | None" = Field(
        default=None, description="Actions list"
    )
    commands: "list[SerializedDict] | None" = Field(
        default=None, description="Commands list"
    )
