"""
Model for MCP echo test response.
"""

from pydantic import BaseModel, Field


class ModelMCPEcho(BaseModel):
    """Model for MCP echo test response."""

    echo: str = Field(description="Echoed message")
    timestamp: float = Field(description="Unix timestamp")
    service: str = Field(description="Service name")
