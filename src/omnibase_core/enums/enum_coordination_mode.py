#!/usr/bin/env python3
"""
Coordination Mode Enum.

Strongly-typed enum for hub coordination modes.
"""

from enum import Enum


class EnumCoordinationMode(str, Enum):
    """Hub coordination modes."""

    EVENT_ROUTER = "event_router"
    WORKFLOW_ORCHESTRATOR = "workflow_orchestrator"
    META_HUB_ROUTER = "meta_hub_router"
