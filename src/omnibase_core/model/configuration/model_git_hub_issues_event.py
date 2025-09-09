"""
GitHubIssuesEvent model.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from .model_git_hub_issue import ModelGitHubIssue
from .model_git_hub_label import ModelGitHubLabel
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser

class ModelGitHubIssuesEvent(BaseModel):
    """
    GitHub issues event with typed fields.
    Replaces Dict[str, Any] for issues event fields.
    """

    action: str = Field(
        ...,
        description="Event action (opened/edited/deleted/transferred/pinned/unpinned/closed/reopened/assigned/unassigned/labeled/unlabeled/locked/unlocked/milestoned/demilestoned)",
    )
    issue: ModelGitHubIssue = Field(..., description="Issue data")
    repository: ModelGitHubRepository = Field(..., description="Repository data")
    sender: ModelGitHubUser = Field(..., description="User who triggered the event")
    label: ModelGitHubLabel | None = Field(
        None,
        description="Label data (for labeled/unlabeled)",
    )
    assignee: ModelGitHubUser | None = Field(
        None,
        description="Assignee data (for assigned/unassigned)",
    )
    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelGitHubIssuesEvent"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)
