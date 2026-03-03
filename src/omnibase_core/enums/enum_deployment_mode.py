# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Deployment Mode Enumeration

Defines the deployment modes for services in the OmniNode platform.
Controls whether a service runs locally, in cloud, or is disabled.
"""

import enum

__all__ = ["EnumDeploymentMode"]


@enum.unique
class EnumDeploymentMode(enum.StrEnum):
    """Deployment mode for a service in the topology."""

    LOCAL = "LOCAL"
    CLOUD = "CLOUD"
    DISABLED = "DISABLED"
