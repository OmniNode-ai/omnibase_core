"""
MCP JSON-RPC Error Model.

Strongly typed model for MCP error responses.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelMCPError(BaseModel):
    """
    MCP JSON-RPC error model.

    Strongly typed model for MCP error responses.
    """

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[BaseModel] = Field(None, description="Additional error data")
