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

from omnibase_core.enums.enum_github_action_event import EnumGithubActionEvent
from omnibase_core.enums.enum_github_runner_os import EnumGithubRunnerOs

from .model_git_hub_actions_workflow import ModelGitHubActionsWorkflow
from .model_job import ModelJob
from .model_pull_request_trigger import ModelPullRequestTrigger

# Import separated models
from .model_push_trigger import ModelPushTrigger
from .model_schedule_trigger import ModelScheduleTrigger
from .model_step import ModelStep
from .model_step_with import ModelStepWith
from .model_workflow_triggers import ModelWorkflowTriggers

# Compatibility aliases
GitHubActionsWorkflow = ModelGitHubActionsWorkflow
PushTrigger = ModelPushTrigger
PullRequestTrigger = ModelPullRequestTrigger
ScheduleTrigger = ModelScheduleTrigger
WorkflowTriggers = ModelWorkflowTriggers
StepWith = ModelStepWith
Step = ModelStep
Job = ModelJob

# Re-export
__all__ = [
    "EnumGithubActionEvent",
    "ModelGitHubActionsWorkflow",
    "EnumGithubRunnerOs",
    "ModelJob",
    "ModelPullRequestTrigger",
    "ModelPushTrigger",
    "ModelScheduleTrigger",
    "ModelStep",
    "ModelStepWith",
    "ModelWorkflowTriggers",
]
