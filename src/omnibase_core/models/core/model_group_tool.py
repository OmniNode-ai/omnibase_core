from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.enums.enum_group_status import EnumGroupStatus
    from omnibase_core.models.primitives.model_semver import SemVerField


class ModelGroupTool(BaseModel):
    """Tool reference within a group."""

    tool_name: str = Field(description="Name of the tool")
    current_version: "SemVerField" = Field(description="Current active version")
    status: "EnumGroupStatus" = Field(description="Tool status within group")
    description: str = Field(description="Tool purpose and capabilities")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Tool capabilities list",
    )
