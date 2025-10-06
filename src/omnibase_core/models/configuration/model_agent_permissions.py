from pydantic import BaseModel, Field


class ModelAgentPermissions(BaseModel):
    """Agent permission configuration."""

    tools: dict[str, bool] = Field(
        description="Tool access permissions (tool_name -> enabled)",
    )
    file_system: dict[str, list[str]] = Field(
        description="File system access permissions (read/write/execute -> paths)",
    )
    git: dict[str, bool] = Field(description="Git operation permissions")
    event_bus: dict[str, list[str]] = Field(
        description="Event bus permissions (publish/subscribe -> event_types)",
    )
