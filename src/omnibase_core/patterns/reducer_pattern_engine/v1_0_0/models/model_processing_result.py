"""Processing result model for Reducer Pattern Engine."""

from pydantic import BaseModel, Field


class ModelProcessingResult(BaseModel):
    """Common strongly typed processing result model."""

    success: bool = Field(..., description="Whether processing succeeded")
    data: str = Field("", description="Processing result data")
    status_code: str = Field("", description="Status code for the processing")
    message: str = Field("", description="Processing status message")
