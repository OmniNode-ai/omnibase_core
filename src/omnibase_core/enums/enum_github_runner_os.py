# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-10-05T12:36:25.656112'
# description: Stamped by ToolPython
# entrypoint: python://enum_github_runner_os
# hash: 0cc69a6dcf3c302e4c7e32953045936f9caad7c2872407b6ad8aebd834515b48
# last_modified_at: '2025-10-05T14:13:58.784305+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: enum_github_runner_os.py
# namespace: python://omnibase.enum.enum_github_runner_os
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
GitHub Actions runner operating systems enum.

This enum defines the various GitHub Actions runner operating systems that can be used
in workflow definitions.
"""

from enum import Enum


class EnumGithubRunnerOs(str, Enum):
    """GitHub Actions runner operating systems."""

    UBUNTU_LATEST = "ubuntu-latest"
    UBUNTU_20_04 = "ubuntu-20.04"
    UBUNTU_22_04 = "ubuntu-22-04"
    WINDOWS_LATEST = "windows-latest"
    WINDOWS_2019 = "windows-2019"
    WINDOWS_2022 = "windows-2022"
    MACOS_LATEST = "macos-latest"
    MACOS_11 = "macos-11"
    MACOS_12 = "macos-12"


# Compatibility alias
GitHubRunnerOS = EnumGithubRunnerOs

__all__ = ["EnumGithubRunnerOs", "GitHubRunnerOS"]
