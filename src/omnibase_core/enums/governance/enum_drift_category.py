# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Drift Category Enum.

Categories for drift detection in daily close reports.
"""

from enum import Enum, unique


@unique
class EnumDriftCategory(str, Enum):
    """Categories of drift detected in daily reconciliation.

    Drift categories classify the type of deviation from planned work:
    - scope: Work scope changed (added/removed features)
    - architecture: Architectural decisions changed
    - interfaces: Interface surfaces changed (events, topics, protocols)
    - dependencies: Dependency versions or relationships changed
    - infra: Infrastructure or environment assumptions changed
    - process: Process or workflow changes
    """

    SCOPE = "scope"
    """Work scope changed (added/removed features)."""

    ARCHITECTURE = "architecture"
    """Architectural decisions changed."""

    INTERFACES = "interfaces"
    """Interface surfaces changed (events, topics, protocols)."""

    DEPENDENCIES = "dependencies"
    """Dependency versions or relationships changed."""

    INFRA = "infra"
    """Infrastructure or environment assumptions changed."""

    PROCESS = "process"
    """Process or workflow changes."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
