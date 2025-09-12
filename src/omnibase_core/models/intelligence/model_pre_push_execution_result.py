"""
Pre-Push Hook Execution Result Model for Intelligence System.

Represents the results of pre-push hook execution.
"""

from pydantic import BaseModel, Field


class model_pre_push_execution_result(BaseModel):
    """
    Model representing pre-push hook execution results.

    Contains information about actions performed and any errors encountered
    during pre-push hook execution.
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

    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning messages",
    )

    files_validated: int = Field(
        ...,
        description="Number of files validated during execution",
    )
