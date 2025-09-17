"""
Statistics model for automation schedules.

Provides strongly typed statistics structure for schedules.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelScheduleStatistics(BaseModel):
    """Statistics for automation schedules."""

    total_runtime_hours: float = Field(
        default=0.0,
        description="Total hours schedule has been active",
    )
    total_agents_spawned: int = Field(
        default=0,
        description="Total number of agents spawned",
    )
    total_tasks_completed: int = Field(
        default=0,
        description="Total tasks completed across all windows",
    )
    total_tokens_consumed: int = Field(default=0, description="Total tokens consumed")
    total_errors_encountered: int = Field(
        default=0,
        description="Total errors across all agents",
    )
    average_agent_efficiency: float = Field(
        default=0.0,
        description="Average efficiency score across all agents",
    )
    successful_transitions: int = Field(
        default=0,
        description="Number of successful window transitions",
    )
    failed_transitions: int = Field(
        default=0,
        description="Number of failed window transitions",
    )
    last_optimization: datetime | None = Field(
        None,
        description="Last time schedule was optimized",
    )
    optimization_count: int = Field(
        default=0,
        description="Number of times schedule has been optimized",
    )
