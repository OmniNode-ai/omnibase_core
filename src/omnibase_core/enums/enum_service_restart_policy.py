# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Restart policies supported by declared lane services."""

from enum import StrEnum, unique


@unique
class EnumServiceRestartPolicy(StrEnum):
    """When a deployment should restart a service."""

    NO = "no"
    ALWAYS = "always"
    ON_FAILURE = "on-failure"
    UNLESS_STOPPED = "unless-stopped"


__all__ = ["EnumServiceRestartPolicy"]
