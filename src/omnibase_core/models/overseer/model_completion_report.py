# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCompletionReport — final outcome report for the overseer performance ledger (OMN-10251)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.overseer.enum_completion_outcome import EnumCompletionOutcome
from omnibase_core.utils.util_decorators import allow_dict_str_any, allow_string_id


@allow_string_id(
    reason=(
        "task_id and runner_id are overseer wire IDs (correlation strings), "
        "not system UUIDs. Overseer state machine uses string-keyed tasks."
    )
)
@allow_dict_str_any(
    reason=(
        "metadata is a heterogeneous performance ledger payload "
        "with varying value types per domain."
    )
)
class ModelCompletionReport(BaseModel, frozen=True, extra="forbid"):
    """Final outcome report written to the overseer performance ledger.

    Emitted once per task lifecycle when the task reaches a terminal state.
    Carries cost, timing, and outcome data for observability and routing
    feedback.
    """

    task_id: str  # string-id-ok: overseer correlation string, not a UUID
    domain: str
    node_id: str
    outcome: EnumCompletionOutcome
    total_cost: float = Field(default=0.0, ge=0.0)
    total_duration_seconds: float = Field(default=0.0, ge=0.0)
    attempts_used: int = Field(default=1, ge=1)
    runner_id: str | None = None  # string-id-ok: overseer runner correlation string
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)  # ONEX_EXCLUDE: dict_str_any
    started_at: datetime | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # string-version-ok: wire type in overseer performance ledger, serialized to JSON
    schema_version: str = "1.0"


__all__ = ["ModelCompletionReport"]
