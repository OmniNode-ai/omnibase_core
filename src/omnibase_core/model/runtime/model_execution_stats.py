"""
Execution Statistics Model

ONEX-compliant execution statistics model with proper typing for task performance tracking.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelExecutionStats(BaseModel):
    """Execution statistics model with proper typing."""

    start_time: Optional[datetime] = Field(default=None)

    end_time: Optional[datetime] = Field(default=None)

    duration_seconds: float = Field(default=0.0, ge=0.0)

    cpu_time_seconds: float = Field(default=0.0, ge=0.0)

    memory_peak_mb: float = Field(default=0.0, ge=0.0)

    disk_io_bytes: int = Field(default=0, ge=0)

    network_io_bytes: int = Field(default=0, ge=0)

    exit_code: Optional[int] = Field(default=None)
