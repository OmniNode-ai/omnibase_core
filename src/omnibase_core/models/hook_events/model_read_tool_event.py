"""Model for Read tool hook event."""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelReadToolEvent(BaseModel):
    """Event for Read tool execution."""

    tool_name: str = Field(..., description="Tool name (Read)")
    file_path: str = Field(..., description="Path to file being read")
    limit: int | None = Field(None, description="Number of lines to read")
    offset: int | None = Field(None, description="Line number to start reading from")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str | None = Field(
        None,
        description="Correlated conversation ID",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hook_version: str = Field("1.0.0", description="Hook system version")


class ModelWriteToolEvent(BaseModel):
    """Event for Write tool execution."""

    tool_name: str = Field(..., description="Tool name (Write)")
    file_path: str = Field(..., description="Path to file being written")
    content: str = Field(..., description="Content being written")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str | None = Field(
        None,
        description="Correlated conversation ID",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hook_version: str = Field("1.0.0", description="Hook system version")


class ModelEditToolEvent(BaseModel):
    """Event for Edit tool execution."""

    tool_name: str = Field(..., description="Tool name (Edit)")
    file_path: str = Field(..., description="Path to file being edited")
    old_string: str = Field(..., description="Text being replaced")
    new_string: str = Field(..., description="Replacement text")
    replace_all: bool | None = Field(False, description="Replace all occurrences")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str | None = Field(
        None,
        description="Correlated conversation ID",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hook_version: str = Field("1.0.0", description="Hook system version")


class ModelBashToolEvent(BaseModel):
    """Event for Bash tool execution."""

    tool_name: str = Field(..., description="Tool name (Bash)")
    command: str = Field(..., description="Command being executed")
    timeout: int | None = Field(None, description="Timeout in milliseconds")
    description: str | None = Field(None, description="Command description")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str | None = Field(
        None,
        description="Correlated conversation ID",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hook_version: str = Field("1.0.0", description="Hook system version")


class ModelGrepToolEvent(BaseModel):
    """Event for Grep tool execution."""

    tool_name: str = Field(..., description="Tool name (Grep)")
    pattern: str = Field(..., description="Search pattern")
    path: str | None = Field(None, description="Path to search")
    glob: str | None = Field(None, description="Glob pattern to filter files")
    case_insensitive: bool | None = Field(
        False,
        description="Case insensitive search",
    )
    output_mode: str | None = Field("files_with_matches", description="Output mode")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str | None = Field(
        None,
        description="Correlated conversation ID",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hook_version: str = Field("1.0.0", description="Hook system version")
