"""
Simple Tool Execution Result Model.

Domain-specific result model for tool execution results.
Replaces the generic ModelExecutionResult with a focused tool-specific model.

Strict typing is enforced: No Any types allowed in implementation.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.types.constraints import PrimitiveValueType

# Type aliases for structured data
StructuredData = dict[str, PrimitiveValueType]


class ModelToolExecutionResult(BaseModel):
    """
    Simple tool execution result for ONEX tools.

    Provides tool-specific execution results with success/failure tracking,
    output data, and error handling.

    Strict typing is enforced: No Any types allowed.

    Field Relationships:
        - success: Boolean indicating overall execution success/failure.
          Use for simple conditional logic (if result.success: ...).
        - status_code: Numeric code providing granular error classification.
          0 indicates success, values >0 represent specific error categories.
          Use when you need to distinguish between different failure modes
          (e.g., 1=validation error, 2=timeout, 3=resource not found).

    Both fields are intentionally provided: `success` for simple boolean checks,
    `status_code` for detailed error handling and categorization.
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

    status_code: int = Field(
        default=0,
        description="Tool execution status code (0=success, >0=error codes)",
        ge=0,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


__all__ = ["ModelToolExecutionResult"]
