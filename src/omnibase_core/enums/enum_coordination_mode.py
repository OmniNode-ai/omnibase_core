#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Coordination Mode Enum.

Strongly-typed enum for hub coordination modes.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumCoordinationMode(UtilStrValueHelper, str, Enum):
    """Hub coordination modes."""

    EVENT_ROUTER = "event_router"
    WORKFLOW_ORCHESTRATOR = "workflow_orchestrator"
    META_HUB_ROUTER = "meta_hub_router"


__all__ = ["EnumCoordinationMode"]
