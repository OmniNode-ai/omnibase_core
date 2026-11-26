# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One MCP tool entry of the contract ``mcp:`` block (OMN-15920).

A contract exposes one MCP tool per operation. Each entry names the tool,
the input and output model it moves, and the three bus topic suffixes the
transport uses: the command, and the completed and failed replies.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from pydantic.config import JsonDict

_DOTTED_PATH_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$"
_DOTTED_PATH = re.compile(_DOTTED_PATH_PATTERN)
# The model check runs after pydantic's own validation so its message names the
# dotted-path rule; the pattern rides in the JSON schema so the committed schema
# refuses the same values.
_DOTTED_PATH_SCHEMA: JsonDict = {"pattern": _DOTTED_PATH_PATTERN}


class ModelContractMcpTool(BaseModel):
    """One operation exposed as an MCP tool; every field is required."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tool_name: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Snake-case MCP tool identifier presented to callers.",
    )
    description: str = Field(
        ..., min_length=1, description="Tool description presented to the MCP client."
    )
    timeout_seconds: int = Field(
        ...,
        gt=0,
        description="Maximum wall-clock seconds a single tool invocation may take.",
    )
    input_model: str = Field(
        ...,
        description="Dotted path (module path, then class) of the tool input model.",
        json_schema_extra=_DOTTED_PATH_SCHEMA,
    )
    output_model: str = Field(
        ...,
        description="Dotted path (module path, then class) of the tool output model.",
        json_schema_extra=_DOTTED_PATH_SCHEMA,
    )
    command_topic: str = Field(
        ..., description="Canonical topic suffix the tool command is published on."
    )
    completed_topic: str = Field(
        ..., description="Canonical topic suffix of the completed reply."
    )
    failed_topic: str = Field(
        ...,
        description="Canonical topic suffix of the failed reply; must differ from "
        "the completed one.",
    )

    @field_validator("input_model", "output_model", mode="after")
    @classmethod
    def _validate_model_path(cls, value: str) -> str:
        if not _DOTTED_PATH.fullmatch(value):
            raise ValueError(
                f"'{value}' must be a dotted path of identifiers with at least one "
                "dot (module path, then class)"
            )
        return value

    @field_validator("command_topic", "completed_topic", "failed_topic", mode="after")
    @classmethod
    def _validate_topic(cls, value: str) -> str:
        from omnibase_core.utils.util_topic_suffix import check_topic_suffix

        result = check_topic_suffix(value)
        if not result.is_valid:
            raise ValueError(f"Invalid topic suffix '{value}': {result.error}")
        if result.normalized_suffix != value:
            raise ValueError(
                f"Topic suffix '{value}' must be canonical: equal to its stripped "
                f"form '{result.normalized_suffix}'"
            )
        return value

    @model_validator(mode="after")
    def _validate_reply_topics_differ(self) -> Self:
        # The reply waiter tells a failure from a completion by equality with
        # the failed topic, so equal suffixes would make every reply a failure.
        if self.completed_topic == self.failed_topic:
            raise ValueError("completed_topic and failed_topic must differ")
        return self
