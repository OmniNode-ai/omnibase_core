"""
Model for agent task result data.

Provides strongly-typed structure for agent task results with proper ONEX compliance.
"""

from pydantic import BaseModel, Field


class ModelAgentTaskResultData(BaseModel):
    """
    Structured result data from agent task execution.

    Replaces Dict[str, Any] usage for ONEX compliance.
    """

    execution_time_ms: int | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    tokens_used: int | None = Field(None, description="Number of tokens consumed")
    model_name: str | None = Field(None, description="Model used for task execution")
    output_files: list[str] = Field(
        default_factory=list,
        description="Files created/modified",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
