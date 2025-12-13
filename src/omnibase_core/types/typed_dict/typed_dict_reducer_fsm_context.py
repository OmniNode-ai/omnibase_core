"""TypedDict for FSM execution context in reducer nodes."""

from __future__ import annotations

from typing import TypedDict


class TypedDictReducerFSMContext(TypedDict, total=False):
    """TypedDict for FSM execution context in reducer nodes."""

    input_data: object
    reduction_type: str
    operation_id: str


__all__ = ["TypedDictReducerFSMContext"]
