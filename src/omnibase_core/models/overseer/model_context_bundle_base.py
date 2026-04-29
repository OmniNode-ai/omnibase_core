# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""_ContextBundleBase — shared non-discriminated fields for all context bundle levels (OMN-10251)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "task_id is an overseer wire correlation string, not a system UUID. "
        "Overseer state machine uses string-keyed tasks."
    )
)
class _ContextBundleBase(BaseModel, frozen=True, extra="forbid"):
    """Shared non-discriminated fields for all bundle levels."""

    run_id: str = Field(  # string-id-ok: overseer correlation string
        ..., description="Pipeline or session run identifier."
    )
    task_id: str = Field(  # string-id-ok: overseer correlation string
        ..., description="Task identifier within the run."
    )
    role: str = Field(..., description="Agent role for this invocation.")
    fsm_state: str = Field(..., description="Current finite-state-machine state.")


__all__ = ["_ContextBundleBase"]
