"""ModelTraceAttributes: Strongly typed OpenTelemetry trace attributes"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelTraceAttributes(BaseModel):
    """Strongly typed OpenTelemetry trace attributes"""

    operation_name: str = Field(..., description="Name of the traced operation")
    correlation_id: Optional[UUID] = Field(
        None, description="Request correlation identifier"
    )
    event_type: Optional[str] = Field(None, description="Type of event being processed")
    payload_size: Optional[int] = Field(None, description="Size of payload in bytes")
    partition_key: Optional[str] = Field(None, description="Kafka partition key")
    processing_time_ms: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )
    success: Optional[bool] = Field(None, description="Operation success status")
    error_code: Optional[str] = Field(
        None, description="Error code if operation failed"
    )
