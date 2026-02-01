#!/usr/bin/env python3
"""
Coordination Mode Enum.

Strongly-typed enum for hub coordination modes.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCoordinationMode(StrValueHelper, str, Enum):
    """Hub coordination modes."""

    EVENT_ROUTER = "event_router"
    WORKFLOW_ORCHESTRATOR = "workflow_orchestrator"
    META_HUB_ROUTER = "meta_hub_router"


__all__ = ["EnumCoordinationMode"]
