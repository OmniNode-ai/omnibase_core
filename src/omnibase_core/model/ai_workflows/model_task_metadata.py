"""Model for agent task metadata."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelTaskMetadata(BaseModel):
    """Strongly-typed metadata for agent tasks."""

    repository_url: Optional[str] = Field(None, description="Repository URL for task")
    branch_name: Optional[str] = Field(None, description="Git branch for task")
    pr_number: Optional[int] = Field(None, description="Pull request number")
    file_paths: List[str] = Field(
        default_factory=list, description="Files to be modified"
    )
    test_requirements: Optional[str] = Field(None, description="Testing requirements")
    review_criteria: Optional[str] = Field(None, description="Review criteria")
    complexity_score: Optional[float] = Field(
        None, description="Task complexity (0.0-1.0)"
    )
    estimated_tokens: Optional[int] = Field(None, description="Estimated token usage")
    requires_human_review: bool = Field(False, description="Requires human review")
