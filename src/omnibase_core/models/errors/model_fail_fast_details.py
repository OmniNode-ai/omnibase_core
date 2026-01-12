"""Model for fail-fast error details."""

from pydantic import BaseModel, ConfigDict, Field


class ModelFailFastDetails(BaseModel):
    """
    Strongly-typed model for fail-fast error details.

    This model represents the error details attached to ExceptionFailFastError
    instances, providing structured context for debugging and error handling.

    Attributes:
        context: Additional context about where the error occurred
        source: Source component or module that raised the error
        recoverable: Whether the error might be recoverable
        additional_info: Any additional structured information
    """

    context: str = Field(
        default="",
        description="Additional context about where the error occurred",
    )
    source: str = Field(
        default="",
        description="Source component or module that raised the error",
    )
    recoverable: bool = Field(
        default=False,
        description="Whether the error might be recoverable",
    )
    additional_info: str = Field(
        default="",
        description="Any additional structured information as string",
    )

    model_config = ConfigDict(extra="allow")
