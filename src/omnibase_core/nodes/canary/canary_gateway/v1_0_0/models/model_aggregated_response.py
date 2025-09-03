"""Model for aggregated response data."""

from pydantic import BaseModel, Field


class ModelAggregatedResponse(BaseModel):
    """Model for aggregated response data."""

    operation_type: str = Field(..., description="Type of operation performed")
    correlation_id: str | None = Field(None, description="Correlation ID")
    timestamp: str = Field(..., description="Response timestamp")
    total_responses: int = Field(..., description="Total number of responses")
    successful_responses: int = Field(..., description="Number of successful responses")
    failed_responses: int = Field(..., description="Number of failed responses")
    responses: list[dict[str, str]] = Field(
        default_factory=list,
        description="Successful responses",
    )
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="Error responses",
    )
