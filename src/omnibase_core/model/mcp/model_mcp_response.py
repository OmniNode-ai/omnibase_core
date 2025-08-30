"""
MCP JSON-RPC Response Model.

Strongly typed model for MCP responses replacing raw dict usage.
"""

from typing import Optional, Union

from pydantic import BaseModel, Field


class ModelMCPResponse(BaseModel):
    """
    MCP JSON-RPC response model.

    Strongly typed model for MCP responses replacing raw dict usage.
    """

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(None, description="Request ID")
    result: Optional[BaseModel] = Field(None, description="Success result")
    error: Optional["ModelMCPError"] = Field(None, description="Error details")
