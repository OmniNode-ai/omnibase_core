"""
MCP Request Models Import Module.

Imports all MCP request/response models and updates forward references.
"""

from omnibase_core.models.mcp.model_mcp_capabilities import ModelMCPCapabilities
from omnibase_core.models.mcp.model_mcp_content_item import ModelMCPContentItem
from omnibase_core.models.mcp.model_mcp_error import ModelMCPError
from omnibase_core.models.mcp.model_mcp_initialize_result import (
    ModelMCPInitializeResult,
)
from omnibase_core.models.mcp.model_mcp_request import ModelMCPRequest

# Import all models
from omnibase_core.models.mcp.model_mcp_request_params import ModelMCPRequestParams
from omnibase_core.models.mcp.model_mcp_response import ModelMCPResponse
from omnibase_core.models.mcp.model_mcp_server_info import ModelMCPServerInfo
from omnibase_core.models.mcp.model_mcp_tool_call_params import ModelMCPToolCallParams
from omnibase_core.models.mcp.model_mcp_tool_call_result import ModelMCPToolCallResult
from omnibase_core.models.mcp.model_mcp_tool_input_schema import ModelMCPToolInputSchema
from omnibase_core.models.mcp.model_mcp_tool_schema import ModelMCPToolSchema
from omnibase_core.models.mcp.model_mcp_tools_capability import ModelMCPToolsCapability
from omnibase_core.models.mcp.model_mcp_tools_list_result import ModelMCPToolsListResult

# Update forward references
ModelMCPResponse.model_rebuild()
ModelMCPInitializeResult.model_rebuild()
ModelMCPCapabilities.model_rebuild()
ModelMCPToolsCapability.model_rebuild()
ModelMCPServerInfo.model_rebuild()
ModelMCPToolsListResult.model_rebuild()
ModelMCPToolSchema.model_rebuild()
ModelMCPToolInputSchema.model_rebuild()
ModelMCPToolCallResult.model_rebuild()
ModelMCPContentItem.model_rebuild()

# Export all models
__all__ = [
    "ModelMCPCapabilities",
    "ModelMCPContentItem",
    "ModelMCPError",
    "ModelMCPInitializeResult",
    "ModelMCPRequest",
    "ModelMCPRequestParams",
    "ModelMCPResponse",
    "ModelMCPServerInfo",
    "ModelMCPToolCallParams",
    "ModelMCPToolCallResult",
    "ModelMCPToolInputSchema",
    "ModelMCPToolSchema",
    "ModelMCPToolsCapability",
    "ModelMCPToolsListResult",
]
