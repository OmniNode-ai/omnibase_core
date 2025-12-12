from pydantic import Field

"""
GitHubIssueCommentEvent model.
"""

from pydantic import BaseModel

from .model_git_hub_issue import ModelGitHubIssue
from .model_git_hub_issue_comment import ModelGitHubIssueComment
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubCommentChange(BaseModel):
    """Represents a change to a GitHub comment field."""

    from_: str | None = Field(default=None, alias="from", description="Previous value")


class ModelGitHubIssueCommentChanges(BaseModel):
    """Changes made to a GitHub issue comment (for edited action)."""

    body: ModelGitHubCommentChange | None = Field(
        default=None, description="Body content change"
    )


class ModelGitHubIssueCommentEvent(BaseModel):
    """
    GitHub issue comment event with typed fields.
    Replaces Dict[str, Any] for issue_comment event fields.
    """

    action: str = Field(
        default=..., description="Event action (created/edited/deleted)"
    )
    issue: ModelGitHubIssue = Field(default=..., description="Issue data")
    comment: ModelGitHubIssueComment = Field(default=..., description="Comment data")
    repository: ModelGitHubRepository = Field(
        default=..., description="Repository data"
    )
    sender: ModelGitHubUser = Field(
        default=..., description="User who triggered the event"
    )
    changes: ModelGitHubIssueCommentChanges | None = Field(
        default=None,
        description="Changes made (for edited action)",
    )


# ONEX compliance remediation complete - factory method eliminated
# Direct Pydantic instantiation provides superior validation:
# event = ModelGitHubIssueCommentEvent(**data) if data else None
