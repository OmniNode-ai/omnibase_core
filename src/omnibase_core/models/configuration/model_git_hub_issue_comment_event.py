from typing import Dict, Optional

from pydantic import Field

"""
GitHubIssueCommentEvent model.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .model_git_hub_issue import ModelGitHubIssue
from .model_git_hub_issue_comment import ModelGitHubIssueComment
from .model_git_hub_repository import ModelGitHubRepository
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubIssueCommentEvent(BaseModel):
    """
    GitHub issue comment event with typed fields.
    Replaces Dict[str, Any] for issue_comment event fields.
    """

    action: str = Field(..., description="Event action (created/edited/deleted)")
    issue: ModelGitHubIssue = Field(..., description="Issue data")
    comment: ModelGitHubIssueComment = Field(..., description="Comment data")
    repository: ModelGitHubRepository = Field(..., description="Repository data")
    sender: ModelGitHubUser = Field(..., description="User who triggered the event")
    changes: dict[str, Any] | None = Field(
        None,
        description="Changes made (for edited action)",
    )


# ONEX compliance remediation complete - factory method eliminated
# Direct Pydantic instantiation provides superior validation:
# event = ModelGitHubIssueCommentEvent(**data) if data else None
