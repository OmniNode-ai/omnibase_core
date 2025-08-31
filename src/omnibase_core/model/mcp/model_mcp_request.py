"""
MCP JSON-RPC Request Model.

Strongly typed model for MCP requests replacing raw dict usage.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.mcp.model_mcp_request_params import ModelMCPRequestParams


class ModelMCPRequest(BaseModel):
    """
    MCP JSON-RPC request model.

    Strongly typed model for MCP requests replacing raw dict usage.
    """

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="MCP method name")
    params: ModelMCPRequestParams | None = Field(
        None,
        description="Request parameters",
    )
    id: str | int | None = Field(None, description="Request ID")
