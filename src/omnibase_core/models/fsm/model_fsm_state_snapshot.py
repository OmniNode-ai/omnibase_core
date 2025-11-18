"""
FSM state snapshot model.

Frozen state representation for pure FSM pattern.
Follows ONEX one-model-per-file architecture.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelFSMStateSnapshot:
    """
    Current FSM state snapshot.

    Frozen dataclass preventing field reassignment (e.g., cannot do state.current_state = "x").

    Warning: context (dict) and history (list) are mutable containers.
    Avoid modifying these after creation to maintain FSM purity.
    FSM executor creates new snapshots rather than mutating existing ones.
    """

    current_state: str
    context: dict[str, Any]
    history: list[str] = field(default_factory=list)


# Export for use
__all__ = ["ModelFSMStateSnapshot"]
