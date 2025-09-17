"""Model for tool parameters in hook events."""

from pydantic import BaseModel, Field


class ModelToolParameters(BaseModel):
    """Structured model for tool parameters captured in hook events.

    This model handles the common parameter patterns found in Claude Code tools
    while maintaining strong typing and ONEX standards compliance.
    """

    # Common file operations
    file_path: str | None = Field(None, description="File path parameter")
    content: str | None = Field(
        None,
        description="Content parameter for write operations",
    )

    # Common query parameters
    pattern: str | None = Field(None, description="Search pattern or regex")
    query: str | None = Field(None, description="Query string parameter")

    # Common numeric parameters
    limit: int | None = Field(None, description="Limit parameter for pagination")
    offset: int | None = Field(None, description="Offset parameter for pagination")
    timeout: int | None = Field(None, description="Timeout parameter in seconds")

    # Common boolean parameters
    recursive: bool | None = Field(None, description="Recursive operation flag")
    force: bool | None = Field(None, description="Force operation flag")
    verbose: bool | None = Field(None, description="Verbose output flag")

    # Common list parameters
    files: list[str] | None = Field(None, description="List of file paths")
    args: list[str] | None = Field(None, description="Command arguments list")

    # Common configuration parameters
    host: str | None = Field(None, description="Host parameter")
    port: int | None = Field(None, description="Port parameter")
    url: str | None = Field(None, description="URL parameter")

    # Extension point for additional parameters
    raw_parameters: str | None = Field(
        None,
        description="JSON string of additional parameters not captured above",
    )
