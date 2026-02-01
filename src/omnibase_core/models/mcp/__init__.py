"""MCP (Model Context Protocol) models for ONEX integration.

This module provides models for exposing ONEX nodes as MCP tools,
enabling AI agents to discover and invoke platform capabilities.

Models:
    ModelMCPParameterMapping: Maps ONEX fields to MCP parameters.
    ModelMCPToolConfig: Contract `mcp:` block configuration.
    ModelMCPInvocationRequest: Tool call request envelope.
    ModelMCPInvocationResponse: Tool call response wrapper.
    ModelMCPToolDescriptor: Complete tool definition for registration.
"""

from omnibase_core.models.mcp.model_mcp_invocation_request import (
    ModelMCPInvocationRequest,
)
from omnibase_core.models.mcp.model_mcp_invocation_response import (
    ModelMCPInvocationResponse,
)
from omnibase_core.models.mcp.model_mcp_parameter_mapping import (
    ModelMCPParameterMapping,
)
from omnibase_core.models.mcp.model_mcp_tool_config import ModelMCPToolConfig
from omnibase_core.models.mcp.model_mcp_tool_descriptor import ModelMCPToolDescriptor

__all__ = [
    "ModelMCPInvocationRequest",
    "ModelMCPInvocationResponse",
    "ModelMCPParameterMapping",
    "ModelMCPToolConfig",
    "ModelMCPToolDescriptor",
]
