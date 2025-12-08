"""
ProtocolWorkflowReducer - Protocol for workflow reducers.

This module provides the protocol definition for nodes that implement
the reducer pattern with synchronous and asynchronous dispatch capabilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.types.protocol_action import ProtocolAction
    from omnibase_core.protocols.types.protocol_node_result import ProtocolNodeResult
    from omnibase_core.protocols.types.protocol_state import ProtocolState


@runtime_checkable
class ProtocolWorkflowReducer(Protocol):
    """
    Protocol for workflow reducer nodes.

    Defines the interface for nodes that implement the reducer pattern
    with synchronous and asynchronous dispatch capabilities.
    """

    def initial_state(self) -> ProtocolState:
        """Returns the initial state for the reducer."""
        ...

    def dispatch(self, state: ProtocolState, action: ProtocolAction) -> ProtocolState:
        """Synchronous state transition for simple operations."""
        ...

    async def dispatch_async(
        self,
        state: ProtocolState,
        action: ProtocolAction,
    ) -> ProtocolNodeResult:
        """Asynchronous workflow-based state transition."""
        ...


__all__ = ["ProtocolWorkflowReducer"]
