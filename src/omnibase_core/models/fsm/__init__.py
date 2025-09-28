"""
FSM (Finite State Machine) models for strongly-typed data structures.

This module provides typed models to replace dict[str, Any] usage in FSM operations.
"""

from typing import Any

from .model_fsm_data import ModelFsmData, ModelFsmState, ModelFsmTransition

__all__ = [
    "ModelFsmData",
    "ModelFsmState",
    "ModelFsmTransition",
]
