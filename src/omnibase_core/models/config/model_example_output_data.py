"""
Example output data model.

This module provides the ModelExampleOutputData class for clean,
strongly-typed replacement for dict[str, Any] in example output data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...enums.enum_cli_status import EnumCliStatus
from ...enums.enum_data_type import EnumDataType
from ...enums.enum_io_type import EnumIOType


class ModelExampleOutputData(BaseModel):
    """
    Clean model for example output data.

    Replaces dict[str, Any] with structured data model.
    """

    # Core data fields
    data_type: EnumIOType = Field(
        default=EnumIOType.OUTPUT, description="Type of output data"
    )
    format: EnumDataType = Field(default=EnumDataType.JSON, description="Data format")

    # Output results
    results: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Output results with basic types"
    )

    # Status information
    status: EnumCliStatus = Field(
        default=EnumCliStatus.SUCCESS, description="Output status"
    )

    # Metrics
    processing_time_ms: float | None = Field(
        None, description="Processing time in milliseconds"
    )
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")

    # Validation info
    is_expected: bool = Field(
        default=True, description="Whether output matches expectations"
    )


# Export the model
__all__ = ["ModelExampleOutputData"]
