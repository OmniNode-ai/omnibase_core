"""
Workflow triggers model.
"""

from typing import List, Optional

from pydantic import BaseModel

from omnibase_core.model.configuration.model_github_events import (
    ModelGitHubIssueCommentEvent, ModelGitHubIssuesEvent,
    ModelGitHubReleaseEvent)
from omnibase_core.model.configuration.model_workflow_configuration import \
    WorkflowDispatch

from .model_pull_request_trigger import ModelPullRequestTrigger
from .model_push_trigger import ModelPushTrigger
from .model_schedule_trigger import ModelScheduleTrigger


class ModelWorkflowTriggers(BaseModel):
    """Workflow trigger configuration."""

    push: Optional[ModelPushTrigger] = None
    pull_request: Optional[ModelPullRequestTrigger] = None
    schedule: Optional[List[ModelScheduleTrigger]] = None
    workflow_dispatch: Optional[WorkflowDispatch] = None
    release: Optional[ModelGitHubReleaseEvent] = None
    issues: Optional[ModelGitHubIssuesEvent] = None
    issue_comment: Optional[ModelGitHubIssueCommentEvent] = None
