"""ModelGitHubIssueCommentChanges model."""

from pydantic import BaseModel, Field

from .model_git_hub_comment_change import ModelGitHubCommentChange


class ModelGitHubIssueCommentChanges(BaseModel):
    """Changes made to a GitHub issue comment (for edited action)."""

    body: ModelGitHubCommentChange | None = Field(
        default=None, description="Body content change"
    )
