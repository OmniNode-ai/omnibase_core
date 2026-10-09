# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
FSM (Finite State Machine) models for strongly-typed data structures.

Typed models to replace dict[str, Any] usage in FSM operations.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_fsm_data import ModelFsmData, ModelFsmState, ModelFsmTransition
    from .model_fsm_operation import ModelFSMOperation
    from .model_fsm_state_snapshot import ModelFSMStateSnapshot
    from .model_fsm_transition_action import ModelFSMTransitionAction
    from .model_fsm_transition_condition import ModelFSMTransitionCondition
    from .model_fsm_transition_result import ModelFSMTransitionResult

__all__ = [
    "ModelFsmData",
    "ModelFsmState",
    "ModelFsmTransition",
    "ModelFSMOperation",
    "ModelFSMStateSnapshot",
    "ModelFSMTransitionAction",
    "ModelFSMTransitionCondition",
    "ModelFSMTransitionResult",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelFsmData": ("omnibase_core.models.fsm.model_fsm_data", "ModelFsmData"),
    "ModelFsmState": ("omnibase_core.models.fsm.model_fsm_data", "ModelFsmState"),
    "ModelFsmTransition": (
        "omnibase_core.models.fsm.model_fsm_data",
        "ModelFsmTransition",
    ),
    "ModelFSMOperation": (
        "omnibase_core.models.fsm.model_fsm_operation",
        "ModelFSMOperation",
    ),
    "ModelFSMStateSnapshot": (
        "omnibase_core.models.fsm.model_fsm_state_snapshot",
        "ModelFSMStateSnapshot",
    ),
    "ModelFSMTransitionAction": (
        "omnibase_core.models.fsm.model_fsm_transition_action",
        "ModelFSMTransitionAction",
    ),
    "ModelFSMTransitionCondition": (
        "omnibase_core.models.fsm.model_fsm_transition_condition",
        "ModelFSMTransitionCondition",
    ),
    "ModelFSMTransitionResult": (
        "omnibase_core.models.fsm.model_fsm_transition_result",
        "ModelFSMTransitionResult",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
