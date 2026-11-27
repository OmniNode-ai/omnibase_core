# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-declared MCP (Model Context Protocol) exposure block.

Schema for the top-level ``mcp:`` section of a node ``contract.yaml``: the
``expose`` flag and a list ``tools`` with one entry per exposed operation
(OMN-15920). The old single-tool keys are gone, with no shim.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.contracts.model_contract_mcp_tool import ModelContractMcpTool


class ModelContractMcpConfig(BaseModel):
    """MCP tool exposure declared in a contract YAML ``mcp:`` block."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        json_schema_extra={
            # The schema is generated from the model, so the exposure rule is
            # declared here as well as enforced by the validator below.
            "if": {
                "required": ["expose"],
                "properties": {"expose": {"const": True}},
            },
            "then": {
                "required": ["tools"],
                "properties": {"tools": {"minItems": 1}},
            },
        },
    )

    expose: bool = Field(
        ...,
        description="Whether the MCP adapter exposes this node as tools.",
    )

    tools: list[ModelContractMcpTool] = Field(
        default_factory=list,
        description="One entry per exposed operation; tool names are unique.",
    )

    @model_validator(mode="after")
    def _validate_tools(self) -> Self:
        names = [tool.tool_name for tool in self.tools]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"duplicate tool_name in one contract: {duplicates}")
        if self.expose and not self.tools:
            raise ValueError("expose: true requires at least one entry in tools")
        return self
