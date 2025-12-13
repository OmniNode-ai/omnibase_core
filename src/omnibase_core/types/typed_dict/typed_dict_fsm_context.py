"""TypedDict for FSM execution context (all fields optional)."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictFSMContext(TypedDict, total=False):
    """TypedDict for FSM execution context (all fields optional)."""

    current_state: str
    previous_state: str | None
    transition_count: int
    last_transition_time: datetime | None


__all__ = ["TypedDictFSMContext"]
