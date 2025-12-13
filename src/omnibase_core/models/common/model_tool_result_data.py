"""
Typed result data model for tool responses.

This module provides strongly-typed result data for tool response patterns.
"""

from pydantic import BaseModel, Field


class ModelToolResultData(BaseModel):
    """
    Typed result data for tool responses.

    Replaces dict[str, Any] result field in ModelToolResponseEvent
    with explicit typed fields for tool execution results.
    """

    output: str | None = Field(
        default=None,
        description="Tool output content",
    )
    status: str | None = Field(
        default=None,
        description="Execution status",
    )
    artifacts: list[str] = Field(
        default_factory=list,
        description="Generated artifact paths or IDs",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings during execution",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Execution metrics",
    )
    data_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Additional result data as key-value pairs",
    )


__all__ = ["ModelToolResultData"]
