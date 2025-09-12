"""
MCP JSON-RPC Response Model.

Strongly typed model for MCP responses replacing raw dict usage.
"""

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.mcp.model_mcp_error import ModelMCPError


class ModelMCPResponse(BaseModel):
    """
    MCP JSON-RPC response model.

    Strongly typed model for MCP responses replacing raw dict usage.
    """

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: str | int | None = Field(None, description="Request ID")
    result: BaseModel | None = Field(None, description="Success result")
    error: Optional["ModelMCPError"] = Field(None, description="Error details")
