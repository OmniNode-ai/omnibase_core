"""Session information model for Claude Code events."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelSessionInfo(BaseModel):
    """Session information extracted from hook events."""

    model_config = ConfigDict()

    session_id: str = Field(description="Generated session identifier")
    working_directory: Optional[str] = Field(description="Working directory path")
    hostname: str = Field(description="System hostname")
    session_key: str = Field(description="Raw session key used for ID generation")
