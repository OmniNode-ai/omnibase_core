"""ModelTraceHeaders: Strongly typed W3C trace context headers"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelTraceHeaders(BaseModel):
    """Strongly typed W3C trace context headers"""

    traceparent: str | None = Field(None, description="W3C traceparent header")
    tracestate: str | None = Field(None, description="W3C tracestate header")
    correlation_id: UUID | None = Field(
        None,
        description="ONEX correlation ID header",
    )
    user_agent: str | None = Field(None, description="Client user agent")
    request_id: UUID | None = Field(None, description="Request identifier")
