# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EnumCloudRoutingPolicy: controls when a task class may route to cloud LLM endpoints (OMN-10614)."""

from __future__ import annotations

from enum import Enum


class EnumCloudRoutingPolicy(str, Enum):
    """Controls when a task class may be routed to cloud LLM endpoints."""

    OPT_IN = "opt_in"
    ALLOWED = "allowed"
    BLOCKED = "blocked"


__all__ = ["EnumCloudRoutingPolicy"]
