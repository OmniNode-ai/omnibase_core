"""Control flow details model."""

from pydantic import BaseModel, Field


class ModelControlFlowDetails(BaseModel):
    """Detailed control flow execution information."""

    retry_attempts: int = Field(default=0, description="Total retry attempts")
    conditional_evaluations: int = Field(
        default=0,
        description="Number of conditional evaluations",
    )
    loop_iterations: int = Field(default=0, description="Total loop iterations")
    notifications_sent: int = Field(
        default=0,
        description="Number of notifications sent",
    )
    execution_path: list[str] | None = Field(
        default=None,
        description="Execution path taken",
    )
    performance_metrics: str | None = Field(
        default=None,
        description="Performance metrics data",
    )
