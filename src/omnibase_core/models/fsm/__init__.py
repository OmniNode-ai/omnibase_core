"""
FSM (Finite State Machine) models for strongly-typed data structures.

This module provides typed models to replace dict[str, Any] usage in FSM operations.
"""

from .model_fsm_data import ModelFsmData, ModelFsmState, ModelFsmTransition
from .model_fsm_state_snapshot import ModelFSMStateSnapshot
from .model_fsm_transition_result import ModelFSMTransitionResult

# MVP FSM Contract Models (OMN-578, OMN-579, OMN-580)
from .model_mvp_fsm_operation import ModelMvpFSMOperation
from .model_mvp_fsm_transition_action import (
    ActionConfigValue,
    ModelMvpFSMTransitionAction,
)
from .model_mvp_fsm_transition_condition import ModelMvpFSMTransitionCondition

__all__ = [
    # Core FSM models
    "ModelFsmData",
    "ModelFsmState",
    "ModelFsmTransition",
    "ModelFSMStateSnapshot",
    "ModelFSMTransitionResult",
    # MVP FSM Contract Models
    "ActionConfigValue",
    "ModelMvpFSMOperation",
    "ModelMvpFSMTransitionAction",
    "ModelMvpFSMTransitionCondition",
]
