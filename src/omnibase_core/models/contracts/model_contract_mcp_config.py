# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-declared MCP (Model Context Protocol) exposure block.

Schema for the top-level ``mcp:`` section of a node ``contract.yaml``. The
MCP adapter reads exactly these four keys when it decides whether, and how,
to expose a node as an AI-invocable tool.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractMcpConfig(BaseModel):
    """MCP tool exposure declared in a contract YAML ``mcp:`` block.

    Every field is required: a contract that opts into MCP exposure must
    say what the tool is called, what it does, and how long it may run.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    expose: bool = Field(
        ...,
        description="Whether the MCP adapter exposes this node as a tool.",
    )

    tool_name: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Snake-case MCP tool identifier presented to callers.",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Tool description presented to the MCP client.",
    )

    timeout_seconds: int = Field(
        ...,
        gt=0,
        description="Maximum wall-clock seconds a single tool invocation may take.",
    )
