"""
Model for operational time window.

Defines an operational time window for automation scheduling.
"""

from datetime import time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.automation.model_window_metadata import ModelWindowMetadata


class EnumWindowPriority(str, Enum):
    """Priority levels for operational windows."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnumWorkRiskLevel(str, Enum):
    """Risk levels for autonomous work execution."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModelOperationalWindow(BaseModel):
    """Defines an operational time window for automation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    window_id: str = Field(..., description="Unique identifier for the window")
    name: str = Field(..., description="Human-readable name (e.g., 'Prime Time')")
    start_time: time = Field(..., description="Window start time")
    end_time: time = Field(..., description="Window end time")
    quota_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of daily quota",
    )
    max_agents: int = Field(..., ge=1, description="Maximum concurrent agents")
    min_agents: int = Field(1, ge=1, description="Minimum concurrent agents")
    priority: EnumWindowPriority = Field(..., description="Window priority level")
    risk_threshold: EnumWorkRiskLevel = Field(
        ...,
        description="Maximum risk level allowed",
    )
    enabled: bool = Field(True, description="Whether window is currently active")

    work_types: list[str] = Field(
        default_factory=list,
        description="Types of work allowed in this window",
    )
    excluded_work_types: list[str] = Field(
        default_factory=list,
        description="Types of work explicitly excluded",
    )

    metadata: ModelWindowMetadata | None = Field(
        default=None,
        description="Additional window configuration",
    )
