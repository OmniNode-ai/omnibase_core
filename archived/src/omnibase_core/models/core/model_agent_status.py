"""
Model for Claude Code agent status.

This model represents the current status and state of a Claude Code agent,
including activity state, resource usage, and health metrics.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AgentStatusType(str, Enum):
    """Agent status enumeration."""

    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    TERMINATING = "terminating"
    STARTING = "starting"
    SUSPENDED = "suspended"


class ModelResourceMetrics(BaseModel):
    """Resource usage metrics for an agent."""

    cpu_percent: float = Field(description="CPU usage percentage (0-100)")
    memory_mb: float = Field(description="Memory usage in megabytes")
    disk_usage_mb: float = Field(description="Disk usage in megabytes")
    network_bytes_sent: int = Field(description="Network bytes sent since start")
    network_bytes_received: int = Field(
        description="Network bytes received since start",
    )
    api_requests_count: int = Field(description="Number of API requests made")
    api_tokens_used: int = Field(description="Total API tokens consumed")


class ModelAgentActivity(BaseModel):
    """Current agent activity information."""

    current_task_id: str | None = Field(
        default=None,
        description="ID of the currently executing task",
    )
    current_operation: str | None = Field(
        default=None,
        description="Description of current operation",
    )
    progress_percent: float = Field(
        default=0.0,
        description="Progress percentage of current task (0-100)",
    )
    estimated_completion: datetime | None = Field(
        default=None,
        description="Estimated completion time for current task",
    )
    last_activity: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of last activity",
    )


class ModelAgentStatus(BaseModel):
    """Complete agent status information."""

    agent_id: str = Field(description="Unique identifier of the agent")
    status: AgentStatusType = Field(description="Current status of the agent")
    activity: ModelAgentActivity = Field(description="Current activity information")
    resource_usage: ModelResourceMetrics = Field(description="Resource usage metrics")
    health_score: float = Field(description="Health score from 0.0 to 1.0")
    error_count: int = Field(default=0, description="Number of errors since last reset")
    last_error: str | None = Field(
        default=None,
        description="Description of last error",
    )
    uptime_seconds: int = Field(description="Agent uptime in seconds")
    tasks_completed: int = Field(
        default=0,
        description="Number of tasks completed since start",
    )
    tasks_failed: int = Field(
        default=0,
        description="Number of tasks failed since start",
    )
    started_at: datetime = Field(description="Agent start timestamp")
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Status last update timestamp",
    )
