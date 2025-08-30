"""
ONEX-compliant model for generation hub status information.

Replaces Dict[str, Any] with strongly typed Pydantic model following ONEX standards.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class ModelHubStatus(BaseModel):
    """
    Hub status model for generation hub state reporting.

    Replaces Dict[str, Any] usage with strongly typed ONEX-compliant structure.
    """

    hub_id: str = Field(..., description="Unique hub identifier")
    status: EnumOnexStatus = Field(..., description="Current hub operational status")
    uptime_seconds: float = Field(..., description="Hub uptime in seconds")
    tools_loaded: int = Field(..., description="Number of currently loaded tools")
    tools_available: int = Field(..., description="Total number of available tools")
    active_sessions: int = Field(
        default=0, description="Number of active processing sessions"
    )
    last_health_check: datetime = Field(
        ..., description="Timestamp of last health check"
    )
    memory_usage_mb: Optional[float] = Field(
        None, description="Current memory usage in MB"
    )
    cpu_usage_percent: Optional[float] = Field(
        None, description="Current CPU usage percentage"
    )
    error_count: int = Field(default=0, description="Number of errors since startup")
    version: str = Field(..., description="Hub service version")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "hub_id": "generation_hub_001",
                "status": "active",
                "uptime_seconds": 3600.5,
                "tools_loaded": 15,
                "tools_available": 23,
                "active_sessions": 3,
                "last_health_check": "2025-07-30T12:00:00Z",
                "memory_usage_mb": 256.5,
                "cpu_usage_percent": 12.3,
                "error_count": 0,
                "version": "1.0.0",
            }
        }
