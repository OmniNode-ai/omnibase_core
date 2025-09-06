"""
Strongly-typed Pydantic models for service health and status.

Replaces Dict[str, Any] usage with proper type safety.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_health_status import EnumHealthStatus


class ModelServiceHealth(BaseModel):
    """Model for service health status information."""

    service_id: str = Field(..., description="Unique service identifier")
    service_name: str = Field(..., description="Human-readable service name")
    status: EnumHealthStatus = Field(..., description="Current health status")
    message: Optional[str] = Field(None, description="Health status message")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last health check timestamp")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional health metadata")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = False
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            EnumHealthStatus: lambda v: v.value
        }


class ModelServiceHealthCollection(BaseModel):
    """Collection of service health statuses."""
    
    services: list[ModelServiceHealth] = Field(default_factory=list, description="List of service health statuses")
    overall_status: EnumHealthStatus = Field(..., description="Overall system health status")
    check_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    total_services: int = Field(..., description="Total number of services")
    healthy_services: int = Field(0, description="Number of healthy services")
    unhealthy_services: int = Field(0, description="Number of unhealthy services")
    
    def calculate_overall_status(self) -> None:
        """Calculate overall status based on individual service statuses."""
        if not self.services:
            self.overall_status = EnumHealthStatus.UNKNOWN
            return
            
        statuses = [s.status for s in self.services]
        
        if all(s == EnumHealthStatus.HEALTHY for s in statuses):
            self.overall_status = EnumHealthStatus.HEALTHY
        elif any(s in [EnumHealthStatus.CRITICAL, EnumHealthStatus.UNHEALTHY] for s in statuses):
            self.overall_status = EnumHealthStatus.UNHEALTHY
        elif any(s == EnumHealthStatus.DEGRADED for s in statuses):
            self.overall_status = EnumHealthStatus.DEGRADED
        else:
            self.overall_status = EnumHealthStatus.UNKNOWN
            
        self.healthy_services = sum(1 for s in statuses if s == EnumHealthStatus.HEALTHY)
        self.unhealthy_services = sum(1 for s in statuses if s in [EnumHealthStatus.CRITICAL, EnumHealthStatus.UNHEALTHY])
        self.total_services = len(self.services)