"""
Model for LLM endpoint configuration with environment variable support.

Provides endpoint configuration for LLM services with proper ONEX compliance.
"""

from pydantic import BaseModel, Field


class ModelLLMEndpoint(BaseModel):
    """Configuration for an LLM endpoint with environment variable support."""

    host: str = Field(
        ...,
        description="Host address - supports env vars like ${MAC_STUDIO_HOST}",
    )
    port: int = Field(..., description="Port number for the LLM service")
    protocol: str = Field("http", description="Protocol to use (http/https)")
    verify_ssl: bool = Field(True, description="Whether to verify SSL certificates")

    @property
    def base_url(self) -> str:
        """Get the base URL for the endpoint."""
        return f"{self.protocol}://{self.host}:{self.port}"
