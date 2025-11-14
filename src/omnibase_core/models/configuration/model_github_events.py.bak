"""
GitHub event models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from .model_git_hub_issue import ModelGitHubIssue
from .model_git_hub_issue_comment import ModelGitHubIssueComment
from .model_git_hub_issue_comment_event import ModelGitHubIssueCommentEvent
from .model_git_hub_issues_event import ModelGitHubIssuesEvent
from .model_git_hub_release import ModelGitHubRelease
from .model_git_hub_release_event import ModelGitHubReleaseEvent
from .model_git_hub_repository import ModelGitHubRepository

# Import separated models
from .model_git_hub_user import ModelGitHubUser

# Compatibility aliases
GitHubUser = ModelGitHubUser
GitHubRepository = ModelGitHubRepository
GitHubRelease = ModelGitHubRelease
GitHubIssue = ModelGitHubIssue
GitHubIssueComment = ModelGitHubIssueComment
GitHubIssuesEvent = ModelGitHubIssuesEvent
GitHubIssueCommentEvent = ModelGitHubIssueCommentEvent
GitHubReleaseEvent = ModelGitHubReleaseEvent

# Re-export
__all__ = [
    "ModelGitHubIssue",
    "ModelGitHubIssueComment",
    "ModelGitHubIssueCommentEvent",
    "ModelGitHubIssuesEvent",
    "ModelGitHubRelease",
    "ModelGitHubReleaseEvent",
    "ModelGitHubRepository",
    "ModelGitHubUser",
]
