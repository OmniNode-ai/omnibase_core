"""
MCP Tool Call Parameters Model.

Tool call parameters for MCP requests.
"""

from typing import Any, Dict

from pydantic import Field

from omnibase_core.decorators.pattern_exclusions import allow_dict_str_any
from omnibase_core.model.mcp.model_mcp_request_params import \
    ModelMCPRequestParams


@allow_dict_str_any("mcp_tool_call_arguments_flexible_parameters")
class ModelMCPToolCallParams(ModelMCPRequestParams):
    """
    MCP tool call parameters model.
    """

    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
