"""
Worker Thread Info Models

ONEX-compliant models for worker thread information with strong typing.
"""

from typing import Optional

from pydantic import BaseModel


class ModelWorkerThreadInfo(BaseModel):
    """Worker thread information with strong typing."""

    thread_id: str
    current_task: Optional[str]
    tasks_executed: int
    status: str
    uptime_seconds: float
