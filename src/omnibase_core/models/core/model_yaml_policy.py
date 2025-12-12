from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelYamlPolicy(BaseModel):
    """Model for YAML policy files."""

    model_config = ConfigDict(extra="allow")

    # Common policy patterns
    policy: "SerializedDict | None" = Field(
        default=None, description="Policy definition"
    )
    rules: "list[SerializedDict] | None" = Field(
        default=None, description="Policy rules"
    )
    permissions: "SerializedDict | None" = Field(
        default=None, description="Permissions"
    )
    restrictions: "SerializedDict | None" = Field(
        default=None, description="Restrictions"
    )
