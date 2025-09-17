"""
Model for similar task outcomes in debug intelligence system.

This model represents the outcome of a similar task that can provide
context for new task execution.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelSimilarTaskOutcome(BaseModel):
    """Model for similar task outcome."""

    task_id: str = Field(description="Unique identifier for the similar task")
    task_description: str = Field(description="Description of the similar task")
    outcome: str = Field(description="Outcome of the task (success/failure)")
    approach_used: str = Field(description="Approach that was used")
    execution_time_seconds: float | None = Field(
        default=None,
        description="Time taken to complete the task",
    )
    tools_used: list[str] = Field(
        default_factory=list,
        description="Tools used in the task execution",
    )
    files_modified: list[str] = Field(
        default_factory=list,
        description="Files that were modified",
    )
    similarity_score: float = Field(
        description="Similarity score to current task (0.0 to 1.0)",
    )
    completed_at: datetime = Field(description="When the task was completed")
    lessons_learned: str | None = Field(
        default=None,
        description="Key lessons learned from this task",
    )
