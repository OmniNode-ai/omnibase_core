"""ModelTraceContext: Strongly typed trace context extraction result"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelTraceContext(BaseModel):
    """Strongly typed trace context extraction result"""

    trace_id: str | None = Field(None, description="OpenTelemetry trace ID")
    span_id: str | None = Field(None, description="OpenTelemetry span ID")
    trace_flags: str | None = Field(None, description="OpenTelemetry trace flags")
    correlation_id: UUID | None = Field(None, description="ONEX correlation ID")
    extraction_success: bool = Field(
        ...,
        description="Whether context extraction succeeded",
    )
