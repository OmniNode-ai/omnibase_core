"""
Example data model.

Clean, strongly-typed replacement for dict[str, Any] in example input/output data.
Follows ONEX one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field


class ModelExampleInputData(BaseModel):
    """
    Clean model for example input data.

    Replaces dict[str, Any] with structured data model.
    """

    # Core data fields
    data_type: str = Field(default="input", description="Type of input data")
    format: str = Field(default="json", description="Data format")

    # Input parameters
    parameters: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Input parameters with basic types"
    )

    # Configuration settings
    configuration: dict[str, str | int | bool] = Field(
        default_factory=dict, description="Configuration settings for the input"
    )

    # Validation info
    schema_version: str | None = Field(
        None, description="Schema version for validation"
    )
    is_validated: bool = Field(default=False, description="Whether input is validated")


class ModelExampleOutputData(BaseModel):
    """
    Clean model for example output data.

    Replaces dict[str, Any] with structured data model.
    """

    # Core data fields
    data_type: str = Field(default="output", description="Type of output data")
    format: str = Field(default="json", description="Data format")

    # Output results
    results: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Output results with basic types"
    )

    # Status information
    status: str = Field(default="success", description="Output status")

    # Metrics
    processing_time_ms: float | None = Field(
        None, description="Processing time in milliseconds"
    )
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")

    # Validation info
    is_expected: bool = Field(
        default=True, description="Whether output matches expectations"
    )


# Export the models
__all__ = [
    "ModelExampleInputData",
    "ModelExampleOutputData",
]
