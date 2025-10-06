from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_health_status_type import EnumHealthStatusType


class ModelHealthCheck(BaseModel):
    """Individual health check result."""

    name: str = Field(description="Name of the health check")
    status: EnumHealthStatusType = Field(description="Status of this health check")
    message: str | None = Field(
        default=None,
        description="Health check message or error details",
    )
    response_time_ms: float = Field(description="Response time in milliseconds")
    last_checked: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of last check",
    )
