from uuid import UUID

from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = [
    "ModelExecutionData",
    "ModelNodeExecutionResult",
]

"""
Pydantic model for node execution results.

Defines the structured result model for node execution operations
within the ONEX architecture.
"""


from omnibase_core.models.core.model_base_result import ModelBaseResult
from omnibase_core.models.core.model_execution_data import ModelExecutionData


class ModelNodeExecutionResult(ModelBaseResult):
    """
    Structured result model for node execution operations.

    Contains the results of executing ONEX nodes through the CLI
    or other execution mechanisms.
    """

    node_name: str = Field(default=..., description="Name of the executed node")
    node_version: ModelSemVer | None = Field(
        default=None,
        description="Version of the executed node",
    )
    execution_data: ModelExecutionData = Field(
        default_factory=lambda: ModelExecutionData(),
        description="Execution output data",
    )
    execution_time_ms: float | None = Field(
        default=None,
        description="Execution time in milliseconds",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracking",
    )
    output_format: str = Field(
        default="dict[str, Any]",
        description="Format of the execution output",
    )
