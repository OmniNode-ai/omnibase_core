"""Model for tool parameters in hook events."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelToolParameters(BaseModel):
    """Structured model for tool parameters captured in hook events.

    This model handles the common parameter patterns found in Claude Code tools
    while maintaining strong typing and ONEX standards compliance.
    """

    # Common file operations
    file_path: Optional[str] = Field(None, description="File path parameter")
    content: Optional[str] = Field(
        None, description="Content parameter for write operations"
    )

    # Common query parameters
    pattern: Optional[str] = Field(None, description="Search pattern or regex")
    query: Optional[str] = Field(None, description="Query string parameter")

    # Common numeric parameters
    limit: Optional[int] = Field(None, description="Limit parameter for pagination")
    offset: Optional[int] = Field(None, description="Offset parameter for pagination")
    timeout: Optional[int] = Field(None, description="Timeout parameter in seconds")

    # Common boolean parameters
    recursive: Optional[bool] = Field(None, description="Recursive operation flag")
    force: Optional[bool] = Field(None, description="Force operation flag")
    verbose: Optional[bool] = Field(None, description="Verbose output flag")

    # Common list parameters
    files: Optional[List[str]] = Field(None, description="List of file paths")
    args: Optional[List[str]] = Field(None, description="Command arguments list")

    # Common configuration parameters
    host: Optional[str] = Field(None, description="Host parameter")
    port: Optional[int] = Field(None, description="Port parameter")
    url: Optional[str] = Field(None, description="URL parameter")

    # Extension point for additional parameters
    raw_parameters: Optional[str] = Field(
        None, description="JSON string of additional parameters not captured above"
    )
