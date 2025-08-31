"""
MCP JSON-RPC Error Model.

Strongly typed model for MCP error responses.
"""

from pydantic import BaseModel, Field


class ModelMCPError(BaseModel):
    """
    MCP JSON-RPC error model.

    Strongly typed model for MCP error responses.
    """

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: BaseModel | None = Field(None, description="Additional error data")
