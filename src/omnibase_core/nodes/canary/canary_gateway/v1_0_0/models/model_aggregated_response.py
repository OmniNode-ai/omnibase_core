"""Model for aggregated response data."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelAggregatedResponse(BaseModel):
    """Model for aggregated response data."""

    operation_type: str = Field(..., description="Type of operation performed")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    timestamp: str = Field(..., description="Response timestamp")
    total_responses: int = Field(..., description="Total number of responses")
    successful_responses: int = Field(..., description="Number of successful responses")
    failed_responses: int = Field(..., description="Number of failed responses")
    responses: List[Dict[str, str]] = Field(
        default_factory=list, description="Successful responses"
    )
    errors: List[Dict[str, str]] = Field(
        default_factory=list, description="Error responses"
    )
