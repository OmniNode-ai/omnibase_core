"""
Enum for agent operational states.

Defines the possible states for an automation agent.
"""

from enum import Enum


class EnumAgentState(str, Enum):
    """Agent operational states."""

    RUNNING = "running"
    IDLE = "idle"
    FAILED = "failed"
    RECOVERING = "recovering"
    STOPPED = "stopped"
    STARTING = "starting"
