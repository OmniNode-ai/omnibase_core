"""
Node workflow result model for reducer dispatch_async operations.

Implements ProtocolNodeResult from omnibase_spi for workflow state transitions.
"""

from dataclasses import dataclass
from typing import Any

from omnibase_spi.protocols.types.protocol_core_types import ContextValue


@dataclass
class ModelNodeWorkflowResult:
    """
    Result wrapper for node workflow state transitions.

    Implements ProtocolNodeResult protocol for dispatch_async operations.
    """

    value: ContextValue | None
    is_success: bool
    is_failure: bool
    error: Any | None
    trust_score: float
    provenance: list[str]
    metadata: dict[str, ContextValue]
    events: list[Any]
    state_delta: dict[str, ContextValue]

    async def validate_result(self) -> bool:
        """Validate result structure."""
        return self.is_success

    def is_successful(self) -> bool:
        """Check if result represents success."""
        return self.is_success
