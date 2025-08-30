"""
Pydantic model for LangExtract health status.

This module defines the Model*HealthStatus class used by the LangExtract
Intelligence Service for ONEX standards compliance.
"""

from datetime import datetime
from typing import Dict, Union

from pydantic import BaseModel, Field


class ModelLangextractHealthStatus(BaseModel):
    """Model for health status of LangExtract service."""

    status: str = Field(..., description="Health status (healthy/unhealthy/degraded)")
    service: str = Field(..., description="Service identifier")
    metrics: Dict[str, int] = Field(default_factory=dict, description="Service metrics")
    timestamp: datetime = Field(..., description="Timestamp of health check")
