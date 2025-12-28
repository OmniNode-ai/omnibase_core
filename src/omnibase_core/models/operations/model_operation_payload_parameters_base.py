"""
Structured base operation parameters.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS


class ModelOperationParametersBase(BaseModel):
    """Structured base operation parameters."""

    execution_timeout: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Execution timeout in milliseconds",
    )
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    priority_level: str = Field(
        default="normal",
        description="Operation priority level",
    )
    async_execution: bool = Field(
        default=False,
        description="Whether operation executes asynchronously",
    )
    validation_enabled: bool = Field(
        default=True,
        description="Whether input validation is enabled",
    )
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")
    trace_execution: bool = Field(
        default=False,
        description="Whether to trace execution steps",
    )
    resource_limits: dict[str, str] = Field(
        default_factory=dict,
        description="Resource limit specifications",
    )
    custom_settings: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom settings",
    )


__all__ = ["ModelOperationParametersBase"]
