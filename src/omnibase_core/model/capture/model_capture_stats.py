"""Strongly typed model for overall capture statistics."""

from typing import Dict

from pydantic import BaseModel, Field

from omnibase_core.model.capture.model_tool_stats import ModelToolStats


class ModelCaptureStats(BaseModel):
    """Model for overall capture statistics."""

    total_captures: int = Field(0, description="Total number of captures", ge=0)
    total_calls: int = Field(0, description="Total tool calls", ge=0)
    total_errors: int = Field(0, description="Total errors across all tools", ge=0)
    error_rate: float = Field(
        0.0, description="Error rate percentage", ge=0.0, le=100.0
    )
    active_sessions: int = Field(0, description="Number of active sessions", ge=0)
    storage_path: str = Field(..., description="Path to capture storage")
    tool_stats: Dict[str, ModelToolStats] = Field(
        default_factory=dict, description="Per-tool statistics"
    )
