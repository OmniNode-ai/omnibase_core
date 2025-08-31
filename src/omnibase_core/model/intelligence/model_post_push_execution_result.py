"""
Post-Push Hook Execution Result Model for Intelligence System.

Represents the results of post-push hook execution.
"""

from pydantic import BaseModel, Field


class model_post_push_execution_result(BaseModel):
    """
    Model representing post-push hook execution results.

    Contains information about actions performed and any errors encountered
    during post-push hook execution.
    """

    success: bool = Field(
        ...,
        description="Whether the overall execution was successful",
    )

    actions_performed: list[str] = Field(
        default_factory=list,
        description="List of actions that were performed",
    )

    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages encountered",
    )

    refs_processed: int = Field(..., description="Number of git references processed")
