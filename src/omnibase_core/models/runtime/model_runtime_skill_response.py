# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical host-local runtime skill response model."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dispatch.model_dispatch_bus_terminal_result import (
    ModelDispatchBusTerminalResult,
)
from omnibase_core.models.runtime.model_runtime_skill_error import (
    ModelRuntimeSkillError,
)
from omnibase_core.types import JsonType


class ModelRuntimeSkillResponse(BaseModel):
    """Typed response returned by the canonical runtime skill path."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    ok: bool = Field(..., description="Whether runtime execution completed cleanly.")
    command_name: str = Field(..., min_length=1, description="Resolved command name.")
    node_alias: str | None = Field(
        default=None,
        min_length=1,
        description="Deprecated compatibility alias echoed by the runtime.",
    )
    resolved_node_name: str | None = Field(
        default=None,
        description="Resolved node directory name when routable.",
    )
    contract_name: str | None = Field(
        default=None,
        description="Resolved contract name when routable.",
    )
    command_topic: str | None = Field(
        default=None,
        description="Resolved command topic used for runtime dispatch.",
    )
    terminal_event: str | None = Field(
        default=None,
        description="Declared terminal event for the resolved route.",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Resolved correlation identifier.",
    )
    dispatch_result: ModelDispatchBusTerminalResult | None = Field(
        default=None,
        description="Terminal broker result for runtime execution.",
    )
    output_payloads: list[dict[str, JsonType]] | None = Field(
        default=None,
        description="Typed dict payloads extracted from successful terminal results.",
    )
    error: ModelRuntimeSkillError | None = Field(
        default=None,
        description="Structured runtime transport or execution error.",
    )

    @model_validator(mode="after")
    def _validate_shape(self) -> ModelRuntimeSkillResponse:
        if self.ok and self.dispatch_result is None:
            raise ValueError("ok responses must include dispatch_result")
        if not self.ok and self.error is None:
            raise ValueError("non-ok responses must include error")
        return self


__all__ = ["ModelRuntimeSkillResponse"]
