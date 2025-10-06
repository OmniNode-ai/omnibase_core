"""
Tool-Based Transition Model.

Transition that delegates to a tool for state computation.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelToolBasedTransition(BaseModel):
    """Transition that delegates to a tool for state computation."""

    tool_id: UUID = Field(
        ...,
        description="UUID of the tool to invoke",
    )

    tool_display_name: str | None = Field(
        None,
        description="Human-readable name of the tool (e.g., 'State Calculator Tool')",
    )

    tool_params: dict[str, Any] | None = Field(
        None,
        description="Additional parameters to pass to the tool",
    )

    fallback_updates: dict[str, Any] | None = Field(
        None,
        description="Updates to apply if tool invocation fails",
    )

    timeout_ms: int | None = Field(
        5000,
        description="Tool invocation timeout in milliseconds",
    )
