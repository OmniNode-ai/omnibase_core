"""ModelTraceContext: Strongly typed trace context extraction result"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelTraceContext(BaseModel):
    """Strongly typed trace context extraction result"""

    trace_id: Optional[str] = Field(None, description="OpenTelemetry trace ID")
    span_id: Optional[str] = Field(None, description="OpenTelemetry span ID")
    trace_flags: Optional[str] = Field(None, description="OpenTelemetry trace flags")
    correlation_id: Optional[UUID] = Field(None, description="ONEX correlation ID")
    extraction_success: bool = Field(
        ..., description="Whether context extraction succeeded"
    )
