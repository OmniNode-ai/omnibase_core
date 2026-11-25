# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed MCP exposure list: one entry per operation of a node (OMN-15920).

A node's contract ``mcp:`` block declares ``expose`` and a ``tools`` list. Each
entry is one operation: tool name, description, timeout, input and output
models, the command route, and the completed and failed reply routes. A typed
refusal is a completed reply; the failed route is for faults only, so the three
routes of an entry must be distinct.

The legacy single-tool block (``tool_name`` beside ``expose``) is not accepted
here; it is refused by name so a declaration cannot be read two ways.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.mcp.model_mcp_tool_entry import ModelMcpToolEntry

_LEGACY_KEYS = frozenset({"tool_name", "description", "timeout_seconds"})


class ModelMcpExposure(BaseModel):
    """The ``mcp:`` block of a contract: ``expose`` and its tool entries."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    expose: bool = Field(..., description="Whether the node is exposed as tools.")
    tools: tuple[ModelMcpToolEntry, ...] = Field(
        default=(), description="One entry per exposed operation."
    )

    @model_validator(mode="after")
    def _names_unique_and_present(self) -> Self:
        seen: set[str] = set()
        for entry in self.tools:
            if entry.tool_name in seen:
                raise ValueError(f"duplicate MCP tool name {entry.tool_name!r}")
            seen.add(entry.tool_name)
        if self.expose and not self.tools:
            raise ValueError("mcp.expose is true but the block has no tool entries")
        return self

    @classmethod
    def from_contract_block(cls, block: object) -> Self:
        """Parse a raw ``mcp:`` mapping; refuse anything else by name."""
        if not isinstance(block, Mapping):
            raise ModelOnexError(
                message="mcp block must be a mapping",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            )
        if _LEGACY_KEYS & block.keys():
            raise ModelOnexError(
                message=(
                    "legacy single-tool mcp block is not accepted; declare a "
                    "'tools' list with one entry per operation"
                ),
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            )
        return cls.model_validate(dict(block))
