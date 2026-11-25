# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One exposed operation of a node: the typed MCP tool entry (OMN-15920)."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

_DOTTED_PATH = r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$"


class ModelMcpToolEntry(BaseModel):
    """One exposed operation of a node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tool_name: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Snake-case MCP tool identifier presented to callers.",
    )
    description: str = Field(..., min_length=1, description="Tool description.")
    timeout_seconds: int = Field(
        ..., gt=0, description="Wall-clock seconds one call may take."
    )
    input_model: str = Field(
        ...,
        pattern=_DOTTED_PATH,
        description="Dotted path of the input model; its schema is the argument schema.",
    )
    output_model: str = Field(
        ..., pattern=_DOTTED_PATH, description="Dotted path of the output model."
    )
    command_route: str = Field(
        ..., min_length=1, description="Topic the typed command is sent on."
    )
    completed_route: str = Field(
        ...,
        min_length=1,
        description="Topic of the completed reply (typed success or typed refusal).",
    )
    failed_route: str = Field(
        ..., min_length=1, description="Topic of the failed reply (faults only)."
    )

    @model_validator(mode="after")
    def _routes_distinct(self) -> Self:
        routes = (self.command_route, self.completed_route, self.failed_route)
        if len(set(routes)) != len(routes):
            raise ValueError(
                f"tool {self.tool_name!r}: command, completed and failed routes "
                "must be distinct"
            )
        return self
