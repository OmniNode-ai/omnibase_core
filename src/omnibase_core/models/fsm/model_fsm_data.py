"""
Strongly-typed FSM (Finite State Machine) data models.

Replaces dict[str, Any] usage in FSM operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from .model_fsm_data_primary import ModelFsmData
from .model_fsm_state import ModelFsmState
from .model_fsm_transition import ModelFsmTransition

# Export all models
__all__ = ["ModelFsmData", "ModelFsmState", "ModelFsmTransition"]
