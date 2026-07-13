# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""MCP contract configuration model for enabling nodes as MCP tools.

This model defines the `mcp` field that can be added to ONEX contracts to expose
orchestrator nodes as MCP tools for AI agent integration.

Example contract.yaml:
    node_type: ORCHESTRATOR_GENERIC
    mcp:
      expose: true
      tool_name: "workflow_execute"
      description: "Execute a workflow"
      timeout_seconds: 30

Enforcement Rule:
    The `mcp.expose` field is ONLY valid for ORCHESTRATOR_GENERIC nodes.
    Non-orchestrator nodes with `mcp.expose: true` will be ignored during
    registration - the MCP tags will not be added to the registry.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelMCPContractConfig(BaseModel):
    """MCP configuration for exposing a node as an MCP tool.

    This configuration is embedded in a node's contract.yaml to enable
    AI agents to discover and invoke the node as an MCP tool.

    Attributes:
        expose: Whether to expose this node as an MCP tool. When True and
            the node is an orchestrator, it will be registered with
            MCP-specific tags for tool discovery.
        tool_name: Optional stable name for the MCP tool. If not provided,
            defaults to the node's name. Use this to provide a consistent
            tool name across node version changes.
        description: Optional AI-friendly description of what this tool does.
            If not provided, the node's description from the contract is used.
        timeout_seconds: Optional execution timeout in seconds. Defaults to 30.
            This is enforced when AI agents invoke the tool.

    Example:
        >>> config = ModelMCPContractConfig(
        ...     expose=True,
        ...     tool_name="my_workflow",
        ...     description="Execute my custom workflow",
        ...     timeout_seconds=60,
        ... )
        >>> config.expose
        True
    """

    expose: bool = Field(
        default=False,
        description="Whether to expose this node as an MCP tool. "
        "Only valid for ORCHESTRATOR_GENERIC nodes.",
    )
    tool_name: str | None = Field(
        default=None,
        description="Optional stable name for the MCP tool. "
        "Defaults to the node's name if not specified.",
    )
    description: str | None = Field(
        default=None,
        description="Optional AI-friendly description of what this tool does. "
        "If not provided, the node's description from the contract is used.",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Execution timeout in seconds for tool invocations. "
        "Minimum: 1, Maximum: 300 (5 minutes).",
    )


__all__ = ["ModelMCPContractConfig"]
