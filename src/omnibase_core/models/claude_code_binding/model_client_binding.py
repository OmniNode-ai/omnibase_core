# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One row of the adapter contract's client_bindings.claude_code section (OMN-18531; relocated by OMN-21093)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_binding_kind import (
    EnumBindingKind,
)
from omnibase_core.enums.enum_client_verdict_action import (
    EnumClientVerdictAction,
)
from omnibase_core.models.claude_code_binding.model_client_argument import (
    ModelClientArgument,
)

__all__ = ["ModelClientBinding"]


class ModelClientBinding(BaseModel):
    """What one hook builds, publishes, awaits and returns; pure data, never code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        description="Binding name; the only value the rendered argv carries."
    )
    kind: EnumBindingKind = Field(default=EnumBindingKind.REPLACING)
    hook_event: str = Field(
        description="Mod event (tool.call) or Claude Code hook event (SessionStart)."
    )
    matcher_tool: str | None = Field(
        default=None, description="Tool the hook matches, if any."
    )
    command_topic: str = Field(description="Topic the typed command is published to.")
    command_type: str = Field(
        description="Name of the typed command built from the hook input."
    )
    arguments: tuple[ModelClientArgument, ...] = Field(default=())
    awaited_events: tuple[str, ...] = Field(
        default=(), description="Terminal events awaited."
    )
    verdict_compute: str = Field(
        description="Name of the pure verdict compute called on the events."
    )
    deadline_ms: int = Field(
        gt=0, description="Process deadline of the adapter, in ms."
    )
    probe_rows: tuple[str, ...] = Field(
        default=(),
        description="Capability-report rows that must be supported to install the row.",
    )
    unverified_action: EnumClientVerdictAction = Field(
        default=EnumClientVerdictAction.NATIVE,
        description="Verdict when a reply fails reassembly or its hash check: native or refuse.",
    )
    deny_text: str = Field(
        default="delegation adapter unavailable",
        description="Text of the fixed {deny} failure.",
    )
    never_started_pattern: str = Field(
        default="ENOENT|not found|cannot start|spawn",
        description="Regular-expression source (rendered as a string) telling never-started from a timeout.",
    )
