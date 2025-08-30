# Generated from contract: tool_claude_code_response_models v1.0.0

from pydantic import BaseModel, Field


class ModelWebFetchToolResponse(BaseModel):
    """Structured response from WebFetch tool execution."""

    url: str = Field(..., description="URL that was fetched")
    content: str = Field(..., description="Fetched content")
    content_type: str = Field(..., description="MIME type of fetched content")
    status_code: int = Field(..., description="HTTP status code", ge=100, le=599)
    success: bool = Field(..., description="Whether fetch was successful")
    content_length: int = Field(..., description="Content length in bytes", ge=0)
    response_headers: dict[str, str] | None = Field(
        None,
        description="HTTP response headers",
    )
    redirect_url: str | None = Field(None, description="Final URL after redirects")
    redirect_count: int = Field(
        default=0,
        description="Number of redirects followed",
        ge=0,
    )
    fetch_time_ms: int | None = Field(
        None,
        description="Time taken to fetch content",
        ge=0,
    )
    cached: bool = Field(default=False, description="Whether response was cached")
    parsed_content: str | None = Field(
        None,
        description="Content converted to markdown if HTML",
    )
