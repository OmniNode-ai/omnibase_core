"""
Pydantic model for node execution results.

Defines the structured result model for node execution operations
within the ONEX architecture with strongly typed enums.
"""

from pydantic import Field

from omnibase_core.enums.nodes.enum_execution_output_format import (
    EnumExecutionOutputFormat,
)
from omnibase_core.models.core.model_base_result import ModelBaseResult

from .model_execution_data_individual import ModelExecutionData


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
        default_factory=lambda: ModelExecutionData(
            result_type=None,
            result_code=None,
            result_message=None,
            output_text=None,
            output_json=None,
            error_type=None,
            error_details=None,
            stack_trace=None,
            steps_completed=0,
            steps_total=None,
            memory_used_mb=None,
            custom_results=None,
            custom_metrics=None,
        ),
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
    output_format: EnumExecutionOutputFormat = Field(
        default=EnumExecutionOutputFormat.DICT,
        description="Format of the execution output",
    )
