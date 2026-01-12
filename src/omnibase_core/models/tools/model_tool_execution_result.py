from pydantic import Field

"""
Simple Tool Execution Result Model.

Domain-specific result model for tool execution results.
Replaces the generic ModelExecutionResult with a focused tool-specific model.

Strict typing is enforced: No Any types allowed in implementation.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from omnibase_core.types.type_constraints import PrimitiveValueType

# Type aliases for structured data
StructuredData = dict[str, PrimitiveValueType]


class ModelToolExecutionResult(BaseModel):
    """
    Simple tool execution result for ONEX tools.

    Provides tool-specific execution results with success/failure tracking,
    output data, and error handling.

    Strict typing is enforced: No Any types allowed.
    """

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution identifier",
    )

    tool_name: str = Field(default=..., description="Name of the executed tool")

    success: bool = Field(
        default=..., description="Whether the tool execution succeeded"
    )

    output: StructuredData = Field(
        default_factory=dict,
        description="Tool execution output data",
    )

    error: str | None = Field(
        default=None,
        description="Error message if tool execution failed",
    )

    execution_time_ms: int = Field(
        default=0,
        description="Execution duration in milliseconds",
        ge=0,
    )

    status_code: int = Field(default=0, description="Tool execution status code")

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelToolExecutionResult"]
