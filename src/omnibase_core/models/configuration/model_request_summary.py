"""Clean request configuration summary model.

Provides a summary view of request configuration without sensitive data.
"""

from pydantic import BaseModel, Field


class ModelRequestSummary(BaseModel):
    """Clean request configuration summary.

    Attributes:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers_count: Number of headers
        params_count: Number of query parameters
        has_json_data: Whether JSON body data is present
        has_form_data: Whether form data is present
        has_files: Whether files to upload are present
        has_auth: Whether authentication is configured
        connect_timeout: Connection timeout in seconds
        read_timeout: Read timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        follow_redirects: Whether to follow HTTP redirects
        max_redirects: Maximum number of redirects to follow
        stream: Whether to stream response content
    """

    method: str = Field(default="GET", description="HTTP method")
    url: str = Field(default="", description="Request URL")
    headers_count: int = Field(default=0, description="Number of headers")
    params_count: int = Field(default=0, description="Number of query parameters")
    has_json_data: bool = Field(default=False, description="Has JSON body data")
    has_form_data: bool = Field(default=False, description="Has form data")
    has_files: bool = Field(default=False, description="Has files to upload")
    has_auth: bool = Field(default=False, description="Has authentication")
    connect_timeout: float = Field(
        default=10.0, description="Connection timeout in seconds"
    )
    read_timeout: float = Field(default=30.0, description="Read timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    follow_redirects: bool = Field(default=True, description="Follow HTTP redirects")
    max_redirects: int = Field(default=10, description="Maximum number of redirects")
    stream: bool = Field(default=False, description="Stream response content")


__all__ = ["ModelRequestSummary"]
