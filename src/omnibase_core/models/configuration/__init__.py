# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Configuration models for ONEX system components."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_cli_config import (
        ModelAPIConfig,
        ModelCLIConfig,
        ModelDatabaseConfig,
        ModelMonitoringConfig,
        ModelOutputConfig,
    )
    from .model_compute_cache_config import ModelComputeCacheConfig
    from .model_config_types import ScalarConfigValue
    from .model_environment_config_override import ModelEnvironmentConfigOverride
    from .model_environment_override import ModelEnvironmentOverride
    from .model_git_hub_actions_container import ModelGitHubActionsContainer
    from .model_git_hub_actions_workflow import ModelGitHubActionsWorkflow
    from .model_git_hub_comment_change import ModelGitHubCommentChange
    from .model_git_hub_issue_comment_changes import ModelGitHubIssueCommentChanges
    from .model_git_hub_issue_comment_event import ModelGitHubIssueCommentEvent
    from .model_git_hub_workflow_concurrency import ModelGitHubWorkflowConcurrency
    from .model_git_hub_workflow_data import ModelGitHubWorkflowData
    from .model_git_hub_workflow_defaults import ModelGitHubWorkflowDefaults
    from .model_node_config_entry import ModelNodeConfigEntry
    from .model_node_config_value import ModelNodeConfigSchema
    from .model_pool_performance_profile import ModelPoolPerformanceProfile
    from .model_pool_recommendations import ModelPoolRecommendations
    from .model_priority_metadata import ModelPriorityMetadata
    from .model_priority_metadata_summary import ModelPriorityMetadataSummary
    from .model_throttle_response import ModelThrottleResponse
    from .model_throttling_behavior import ModelThrottlingBehavior

__all__ = [
    "ScalarConfigValue",
    "ModelAPIConfig",
    "ModelCLIConfig",
    "ModelComputeCacheConfig",
    "ModelDatabaseConfig",
    "ModelEnvironmentConfigOverride",
    "ModelEnvironmentOverride",
    "ModelGitHubActionsContainer",
    "ModelGitHubActionsWorkflow",
    "ModelGitHubCommentChange",
    "ModelGitHubIssueCommentChanges",
    "ModelGitHubIssueCommentEvent",
    "ModelGitHubWorkflowConcurrency",
    "ModelGitHubWorkflowData",
    "ModelGitHubWorkflowDefaults",
    "ModelMonitoringConfig",
    "ModelNodeConfigEntry",
    "ModelNodeConfigSchema",
    "ModelOutputConfig",
    "ModelPoolPerformanceProfile",
    "ModelPoolRecommendations",
    "ModelPriorityMetadata",
    "ModelPriorityMetadataSummary",
    "ModelThrottleResponse",
    "ModelThrottlingBehavior",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelAPIConfig": (
        "omnibase_core.models.configuration.model_cli_config",
        "ModelAPIConfig",
    ),
    "ModelCLIConfig": (
        "omnibase_core.models.configuration.model_cli_config",
        "ModelCLIConfig",
    ),
    "ModelDatabaseConfig": (
        "omnibase_core.models.configuration.model_cli_config",
        "ModelDatabaseConfig",
    ),
    "ModelMonitoringConfig": (
        "omnibase_core.models.configuration.model_cli_config",
        "ModelMonitoringConfig",
    ),
    "ModelOutputConfig": (
        "omnibase_core.models.configuration.model_cli_config",
        "ModelOutputConfig",
    ),
    "ModelComputeCacheConfig": (
        "omnibase_core.models.configuration.model_compute_cache_config",
        "ModelComputeCacheConfig",
    ),
    "ScalarConfigValue": (
        "omnibase_core.models.configuration.model_config_types",
        "ScalarConfigValue",
    ),
    "ModelEnvironmentConfigOverride": (
        "omnibase_core.models.configuration.model_environment_config_override",
        "ModelEnvironmentConfigOverride",
    ),
    "ModelEnvironmentOverride": (
        "omnibase_core.models.configuration.model_environment_override",
        "ModelEnvironmentOverride",
    ),
    "ModelGitHubActionsContainer": (
        "omnibase_core.models.configuration.model_git_hub_actions_container",
        "ModelGitHubActionsContainer",
    ),
    "ModelGitHubActionsWorkflow": (
        "omnibase_core.models.configuration.model_git_hub_actions_workflow",
        "ModelGitHubActionsWorkflow",
    ),
    "ModelGitHubCommentChange": (
        "omnibase_core.models.configuration.model_git_hub_comment_change",
        "ModelGitHubCommentChange",
    ),
    "ModelGitHubIssueCommentChanges": (
        "omnibase_core.models.configuration.model_git_hub_issue_comment_changes",
        "ModelGitHubIssueCommentChanges",
    ),
    "ModelGitHubIssueCommentEvent": (
        "omnibase_core.models.configuration.model_git_hub_issue_comment_event",
        "ModelGitHubIssueCommentEvent",
    ),
    "ModelGitHubWorkflowConcurrency": (
        "omnibase_core.models.configuration.model_git_hub_workflow_concurrency",
        "ModelGitHubWorkflowConcurrency",
    ),
    "ModelGitHubWorkflowData": (
        "omnibase_core.models.configuration.model_git_hub_workflow_data",
        "ModelGitHubWorkflowData",
    ),
    "ModelGitHubWorkflowDefaults": (
        "omnibase_core.models.configuration.model_git_hub_workflow_defaults",
        "ModelGitHubWorkflowDefaults",
    ),
    "ModelNodeConfigEntry": (
        "omnibase_core.models.configuration.model_node_config_entry",
        "ModelNodeConfigEntry",
    ),
    "ModelNodeConfigSchema": (
        "omnibase_core.models.configuration.model_node_config_value",
        "ModelNodeConfigSchema",
    ),
    "ModelPoolPerformanceProfile": (
        "omnibase_core.models.configuration.model_pool_performance_profile",
        "ModelPoolPerformanceProfile",
    ),
    "ModelPoolRecommendations": (
        "omnibase_core.models.configuration.model_pool_recommendations",
        "ModelPoolRecommendations",
    ),
    "ModelPriorityMetadata": (
        "omnibase_core.models.configuration.model_priority_metadata",
        "ModelPriorityMetadata",
    ),
    "ModelPriorityMetadataSummary": (
        "omnibase_core.models.configuration.model_priority_metadata_summary",
        "ModelPriorityMetadataSummary",
    ),
    "ModelThrottleResponse": (
        "omnibase_core.models.configuration.model_throttle_response",
        "ModelThrottleResponse",
    ),
    "ModelThrottlingBehavior": (
        "omnibase_core.models.configuration.model_throttling_behavior",
        "ModelThrottlingBehavior",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
