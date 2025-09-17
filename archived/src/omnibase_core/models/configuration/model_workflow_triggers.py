"""
Workflow triggers model.
"""

from pydantic import BaseModel

from omnibase_core.models.configuration.model_github_events import (
    ModelGitHubIssueCommentEvent,
    ModelGitHubIssuesEvent,
    ModelGitHubReleaseEvent,
)
from omnibase_core.models.configuration.model_workflow_configuration import (
    WorkflowDispatch,
)

from .model_pull_request_trigger import ModelPullRequestTrigger
from .model_push_trigger import ModelPushTrigger
from .model_schedule_trigger import ModelScheduleTrigger


class ModelWorkflowTriggers(BaseModel):
    """Workflow trigger configuration."""

    push: ModelPushTrigger | None = None
    pull_request: ModelPullRequestTrigger | None = None
    schedule: list[ModelScheduleTrigger] | None = None
    workflow_dispatch: WorkflowDispatch | None = None
    release: ModelGitHubReleaseEvent | None = None
    issues: ModelGitHubIssuesEvent | None = None
    issue_comment: ModelGitHubIssueCommentEvent | None = None
