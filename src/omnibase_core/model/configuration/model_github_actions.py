# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.656112'
# description: Stamped by ToolPython
# entrypoint: python://model_github_actions
# hash: 0cc69a6dcf3c302e4c7e32953045936f9caad7c2872407b6ad8aebd834515b48
# last_modified_at: '2025-05-29T14:13:58.784305+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_github_actions.py
# namespace: python://omnibase.model.model_github_actions
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 06be48d3-474c-46df-b39b-407300cf8758
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Pydantic models for GitHub Actions workflows.

This module defines the structure for GitHub Actions workflow files (.github/workflows/*.yml)
to enable proper validation, serialization, and formatting.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from enum import Enum

from .model_git_hub_actions_workflow import ModelGitHubActionsWorkflow
from .model_job import ModelJob
from .model_pull_request_trigger import ModelPullRequestTrigger
# Import separated models
from .model_push_trigger import ModelPushTrigger
from .model_schedule_trigger import ModelScheduleTrigger
from .model_step import ModelStep
from .model_step_with import ModelStepWith
from .model_workflow_triggers import ModelWorkflowTriggers


class ModelGitHubActionEvent(str, Enum):
    """GitHub Actions trigger events."""

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    SCHEDULE = "schedule"
    WORKFLOW_DISPATCH = "workflow_dispatch"
    RELEASE = "release"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"


class ModelGitHubRunnerOS(str, Enum):
    """GitHub Actions runner operating systems."""

    UBUNTU_LATEST = "ubuntu-latest"
    UBUNTU_20_04 = "ubuntu-20.04"
    UBUNTU_22_04 = "ubuntu-22.04"
    WINDOWS_LATEST = "windows-latest"
    WINDOWS_2019 = "windows-2019"
    WINDOWS_2022 = "windows-2022"
    MACOS_LATEST = "macos-latest"
    MACOS_11 = "macos-11"
    MACOS_12 = "macos-12"


# Backward compatibility aliases
GitHubActionsWorkflow = ModelGitHubActionsWorkflow
GitHubActionEvent = ModelGitHubActionEvent
GitHubRunnerOS = ModelGitHubRunnerOS
PushTrigger = ModelPushTrigger
PullRequestTrigger = ModelPullRequestTrigger
ScheduleTrigger = ModelScheduleTrigger
WorkflowTriggers = ModelWorkflowTriggers
StepWith = ModelStepWith
Step = ModelStep
Job = ModelJob

# Re-export for backward compatibility
__all__ = [
    "ModelPushTrigger",
    "ModelPullRequestTrigger",
    "ModelScheduleTrigger",
    "ModelWorkflowTriggers",
    "ModelStepWith",
    "ModelStep",
    "ModelJob",
    "ModelGitHubActionsWorkflow",
    "ModelGitHubActionEvent",
    "ModelGitHubRunnerOS",
    # Backward compatibility
    "GitHubActionsWorkflow",
    "GitHubActionEvent",
    "GitHubRunnerOS",
    "PushTrigger",
    "PullRequestTrigger",
    "ScheduleTrigger",
    "WorkflowTriggers",
    "StepWith",
    "Step",
    "Job",
]
