"""GitHubIssueCommentEvent model."""

from pydantic import BaseModel, Field

from .model_git_hub_comment_change import ModelGitHubCommentChange
from .model_git_hub_issue import ModelGitHubIssue
from .model_git_hub_issue_comment import ModelGitHubIssueComment
from .model_git_hub_issue_comment_changes import ModelGitHubIssueCommentChanges
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser

__all__ = [
    "ModelGitHubCommentChange",
    "ModelGitHubIssueCommentChanges",
    "ModelGitHubIssueCommentEvent",
]


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
