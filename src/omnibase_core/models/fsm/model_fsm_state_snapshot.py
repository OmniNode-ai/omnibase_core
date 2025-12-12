"""
FSM state snapshot model.

Frozen state representation for pure FSM pattern.
Follows ONEX one-model-per-file architecture.

Note:
    The context field uses dict[str, Any] to allow flexible FSM context data.
    This is an intentional design decision since FSM context can contain
    arbitrary runtime state that varies per FSM implementation.
"""

from dataclasses import dataclass, field

from omnibase_core.types.type_fsm_context import FSMContextType


@dataclass(frozen=True)
class ModelFSMStateSnapshot:
    """
    Immutable FSM state snapshot for pure FSM operations.

    This frozen dataclass provides an immutable representation of FSM state,
    preventing accidental modifications during FSM execution.

    Attributes:
        current_state: The current state name in the FSM.
        context: Runtime context data for the FSM. Uses dict[str, Any] to support
            flexible context structures that vary per FSM implementation.
        history: List of previously visited state names for debugging/auditing.

    Design Notes:
        - Frozen dataclass prevents field reassignment (e.g., cannot do state.current_state = "x")
        - The context dict and history list are mutable containers by Python design
        - Callers should avoid modifying these after creation to maintain FSM purity
        - FSM executors should create new snapshots rather than mutating existing ones

    Example:
        >>> snapshot = ModelFSMStateSnapshot(
        ...     current_state="processing",
        ...     context={"request_id": "abc123", "retry_count": 2},
        ...     history=["initial", "validating"],
        ... )
        >>> snapshot.current_state
        'processing'
    """

    current_state: str
    context: FSMContextType
    history: list[str] = field(default_factory=list)


# Export for use
__all__ = ["ModelFSMStateSnapshot"]
