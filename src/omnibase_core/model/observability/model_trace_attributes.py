"""ModelTraceAttributes: Strongly typed OpenTelemetry trace attributes"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelTraceAttributes(BaseModel):
    """Strongly typed OpenTelemetry trace attributes"""

    operation_name: str = Field(..., description="Name of the traced operation")
    correlation_id: UUID | None = Field(
        None,
        description="Request correlation identifier",
    )
    event_type: str | None = Field(None, description="Type of event being processed")
    payload_size: int | None = Field(None, description="Size of payload in bytes")
    partition_key: str | None = Field(None, description="Kafka partition key")
    processing_time_ms: int | None = Field(
        None,
        description="Processing time in milliseconds",
    )
    success: bool | None = Field(None, description="Operation success status")
    error_code: str | None = Field(
        None,
        description="Error code if operation failed",
    )
