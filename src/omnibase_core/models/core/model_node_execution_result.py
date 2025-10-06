from pydantic import Field

"""
Pydantic model for node execution results.

Defines the structured result model for node execution operations
within the ONEX architecture.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_base_result import ModelBaseResult
from omnibase_core.models.core.model_execution_data import ModelExecutionData


class ModelNodeExecutionResult(ModelBaseResult):
    """
    Structured result model for node execution operations.

    Contains the results of executing ONEX nodes through the CLI
    or other execution mechanisms.
    """

    node_name: str = Field(..., description="Name of the executed node")
    node_version: str | None = Field(
        None,
        description="Version of the executed node",
    )
    execution_data: ModelExecutionData = Field(
        default_factory=ModelExecutionData,
        description="Execution output data",
    )
    execution_time_ms: float | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    correlation_id: str | None = Field(
        None,
        description="Correlation ID for tracking",
    )
    output_format: str = Field(
        default="dict[str, Any]",
        description="Format of the execution output",
    )
