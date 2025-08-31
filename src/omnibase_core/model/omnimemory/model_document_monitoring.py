"""
Model definitions for Document Monitoring in OmniMemory.

This module contains Pydantic models for document monitoring status
and related data structures.
"""

from pydantic import BaseModel, Field


class ModelMonitoringStatus(BaseModel):
    """Represents the current status of document monitoring."""

    active: bool = Field(..., description="Whether monitoring is currently active")
    monitored_files: int = Field(
        ...,
        description="Number of files currently being monitored",
    )
    pending_changes: int = Field(
        ...,
        description="Number of pending changes in the queue",
    )
    scan_interval: int = Field(..., description="Scan interval in seconds")
