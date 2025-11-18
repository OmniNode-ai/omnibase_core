"""FSM transition result model."""

from datetime import datetime
from typing import Any

from omnibase_core.models.model_intent import ModelIntent


class ModelFSMTransitionResult:
    """
    Result of FSM transition execution.

    Pure data structure containing transition outcome and intents for side effects.
    """

    def __init__(
        self,
        success: bool,
        new_state: str,
        old_state: str,
        transition_name: str | None,
        intents: list[ModelIntent],
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        """
        Initialize FSM transition result.

        Args:
            success: Whether transition succeeded
            new_state: Resulting state name
            old_state: Previous state name
            transition_name: Name of transition executed (or None if failed)
            intents: List of intents for side effects
            metadata: Optional metadata about execution
            error: Optional error message if failed
        """
        self.success = success
        self.new_state = new_state
        self.old_state = old_state
        self.transition_name = transition_name
        self.intents = intents
        self.metadata = metadata or {}
        self.error = error
        self.timestamp = datetime.now().isoformat()


__all__ = ["ModelFSMTransitionResult"]
