"""TypedDict for node state information."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictNodeState(TypedDict, total=False):
    """
    TypedDict for node state tracking.

    Represents the internal state of a node in the ONEX architecture.
    All fields are optional since state evolves during the node lifecycle.

    Attributes:
        status: Current lifecycle status (e.g., "initialized", "ready", "processing")
        error_message: Error message if node is in error state
        last_operation: Name of the last operation performed
    """

    status: str
    error_message: NotRequired[str]
    last_operation: NotRequired[str]


__all__ = ["TypedDictNodeState"]
