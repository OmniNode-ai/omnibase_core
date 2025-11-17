"""
FSM state snapshot model.

Immutable state representation for pure FSM pattern.
Follows ONEX one-model-per-file architecture.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelFSMStateSnapshot:
    """
    Current FSM state snapshot.

    Immutable state representation for pure FSM pattern.
    """

    current_state: str
    context: dict[str, Any]
    history: list[str] = field(default_factory=list)


# Export for use
__all__ = ["ModelFSMStateSnapshot"]
