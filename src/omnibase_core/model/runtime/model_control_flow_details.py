"""Control flow details model."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelControlFlowDetails(BaseModel):
    """Detailed control flow execution information."""

    retry_attempts: int = Field(default=0, description="Total retry attempts")
    conditional_evaluations: int = Field(
        default=0, description="Number of conditional evaluations"
    )
    loop_iterations: int = Field(default=0, description="Total loop iterations")
    notifications_sent: int = Field(
        default=0, description="Number of notifications sent"
    )
    execution_path: Optional[List[str]] = Field(
        default=None, description="Execution path taken"
    )
    performance_metrics: Optional[str] = Field(
        default=None, description="Performance metrics data"
    )
