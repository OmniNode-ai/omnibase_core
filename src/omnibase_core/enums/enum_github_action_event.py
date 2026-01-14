# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-10-05T12:36:25.656112'
# description: Stamped by ToolPython
# entrypoint: python://enum_github_action_event
# hash: 0cc69a6dcf3c302e4c7e32953045936f9caad7c2872407b6ad8aebd834515b48
# last_modified_at: '2025-10-05T14:13:58.784305+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: enum_github_action_event.py
# namespace: python://omnibase.enum.enum_github_action_event
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
GitHub Actions trigger events enum.

This enum defines the various GitHub Actions trigger events that can be used
in workflow definitions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumGithubActionEvent(StrValueHelper, str, Enum):
    """GitHub Actions trigger events."""

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    SCHEDULE = "schedule"
    WORKFLOW_DISPATCH = "workflow_dispatch"
    RELEASE = "release"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"


# Deprecated: use EnumGithubActionEvent directly
GitHubActionEvent: type[EnumGithubActionEvent] = EnumGithubActionEvent

__all__ = ["EnumGithubActionEvent", "GitHubActionEvent"]
