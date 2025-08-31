"""Model for agent task metadata."""

from pydantic import BaseModel, Field


class ModelTaskMetadata(BaseModel):
    """Strongly-typed metadata for agent tasks."""

    repository_url: str | None = Field(None, description="Repository URL for task")
    branch_name: str | None = Field(None, description="Git branch for task")
    pr_number: int | None = Field(None, description="Pull request number")
    file_paths: list[str] = Field(
        default_factory=list,
        description="Files to be modified",
    )
    test_requirements: str | None = Field(None, description="Testing requirements")
    review_criteria: str | None = Field(None, description="Review criteria")
    complexity_score: float | None = Field(
        None,
        description="Task complexity (0.0-1.0)",
    )
    estimated_tokens: int | None = Field(None, description="Estimated token usage")
    requires_human_review: bool = Field(False, description="Requires human review")
