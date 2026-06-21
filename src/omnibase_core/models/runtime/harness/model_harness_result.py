# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelHarnessResult: outcome of one in-process harness run (OMN-13420)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelHarnessResult(BaseModel):
    """Outcome of a single in-process harness run."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(..., description="Run correlation ID.")
    terminal_topic: str | None = Field(
        default=None, description="Topic of the terminal event, or None on no-terminal."
    )
    terminal_payload: dict[str, object] | None = Field(  # dict-str-any-ok: JSON payload
        default=None, description="Decoded terminal-event payload, or None."
    )
    status: str = Field(
        ..., description="Terminal status: success | failure | no_terminal."
    )
    emitted_topics: tuple[str, ...] = Field(
        default=(), description="Topics emitted during the run, in order."
    )
    exit_code: int = Field(
        ..., description="Process-style exit code: 0 success, 2 no terminal, 3 failure."
    )

    @property
    def reached_terminal(self) -> bool:
        """True when a terminal event was observed."""
        return self.terminal_topic is not None


__all__ = ["ModelHarnessResult"]
