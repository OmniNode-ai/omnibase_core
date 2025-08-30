"""ModelTraceHeaders: Strongly typed W3C trace context headers"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelTraceHeaders(BaseModel):
    """Strongly typed W3C trace context headers"""

    traceparent: Optional[str] = Field(None, description="W3C traceparent header")
    tracestate: Optional[str] = Field(None, description="W3C tracestate header")
    correlation_id: Optional[UUID] = Field(
        None, description="ONEX correlation ID header"
    )
    user_agent: Optional[str] = Field(None, description="Client user agent")
    request_id: Optional[UUID] = Field(None, description="Request identifier")
