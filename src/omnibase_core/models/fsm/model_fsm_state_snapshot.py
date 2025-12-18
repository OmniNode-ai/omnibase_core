"""
FSM state snapshot model.

Frozen Pydantic model representation for pure FSM pattern.
Follows ONEX one-model-per-file architecture.

Note:
    The context field uses dict[str, Any] to allow flexible FSM context data.
    This is an intentional design decision since FSM context can contain
    arbitrary runtime state that varies per FSM implementation.

Immutability Considerations:
    This model uses ConfigDict(frozen=True) to prevent field reassignment.
    Python's frozen Pydantic models have inherent limitations with mutable containers:

    1. **history field**: Uses list[str] as the standard Pydantic serializable type.
       While lists are mutable by nature, the frozen model prevents reassignment.
       Callers should treat this as immutable.

       Design Decision (list vs tuple):
       - tuple[str, ...] was considered for stronger immutability guarantees
       - list[str] was chosen because:
         a) Better Pydantic serialization compatibility (native JSON array)
         b) Consistent with existing FSM executor and mixin patterns
         c) Simpler type annotations for callers
         d) The contract-based immutability via frozen=True + documentation
            is sufficient for this use case
       - The correct pattern is: new_history = [*snapshot.history, "new_state"]
         which works identically for both list and tuple types

    2. **context field**: Uses dict[str, Any] which is mutable by Python design.
       The dict container itself cannot be reassigned (frozen), but its contents
       CAN still be modified (e.g., context["key"] = "new_value" will work).

       Alternatives considered but not implemented:
       - types.MappingProxyType: Would provide read-only view but loses dict type
       - frozendict (third-party): Would require additional dependency

       Current contract: Callers MUST NOT mutate context after snapshot creation.
       FSM executors should create new snapshots with new context dicts rather
       than modifying existing context.

    This design balances practical Pydantic usage with documented contracts
    where full immutability would be too restrictive.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_fsm_context import FSMContextType


class ModelFSMStateSnapshot(BaseModel):
    """
    Immutable FSM state snapshot for pure FSM operations.

    This frozen Pydantic model provides an immutable representation of FSM state,
    preventing accidental modifications during FSM execution.

    Attributes:
        current_state: The current state name in the FSM.
        context: Runtime context data for the FSM. Uses dict[str, Any] to support
            flexible context structures that vary per FSM implementation.
            **WARNING**: While the context field cannot be reassigned, the dict
            contents are still mutable. Callers MUST NOT modify context after
            snapshot creation to maintain FSM purity.
        history: List of previously visited state names for debugging/auditing.
            Always initialized to empty list [], never None.

    Immutability Contract:
        - **Guaranteed immutable**: current_state (str)
        - **Contractually immutable**: context (dict), history (list)
        - Field reassignment is blocked by frozen=True
        - FSM executors MUST create new snapshots rather than mutating existing ones
        - Extra fields are rejected (extra="forbid")

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it thread-safe
        for concurrent read access from multiple threads or async tasks. However:

        - **Safe**: Reading any field from multiple threads simultaneously
        - **Safe**: Passing snapshots between threads without synchronization
        - **WARNING**: Do NOT mutate mutable containers (dict/list contents) - this
          violates the immutability contract and could cause race conditions

        For state management in NodeReducer, note that while snapshots themselves
        are thread-safe, the NodeReducer instance that creates/restores them is
        NOT thread-safe. See docs/guides/THREADING.md for details.

    Example:
        >>> snapshot = ModelFSMStateSnapshot(
        ...     current_state="processing",
        ...     context={"request_id": "abc123", "retry_count": 2},
        ...     history=["initial", "validating"],
        ... )
        >>> snapshot.current_state
        'processing'
        >>> snapshot.history  # Always a list, never None
        ['initial', 'validating']

    Warning:
        Do NOT mutate context or history after creation::

            # WRONG - violates immutability contract
            snapshot.context["new_key"] = "value"
            snapshot.history.append("new_state")

            # CORRECT - create new snapshot with updated values
            new_context = {**snapshot.context, "new_key": "value"}
            new_history = [*snapshot.history, "new_state"]
            new_snapshot = ModelFSMStateSnapshot(
                current_state="new_state",
                context=new_context,
                history=new_history,
            )
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    current_state: str = Field(..., description="Current FSM state name")
    context: FSMContextType = Field(
        default_factory=dict,
        description="FSM context data - flexible runtime state storage",
    )
    history: list[str] = Field(
        default_factory=list,
        description="State transition history for debugging/auditing",
    )

    @classmethod
    def create_initial(cls, initial_state: str) -> ModelFSMStateSnapshot:
        """
        Create initial snapshot with given state.

        Factory method for creating a new FSM snapshot at the initial state.
        Context and history are initialized to their defaults (empty dict and
        empty list respectively) via default_factory.

        Args:
            initial_state: The initial state name for the FSM.

        Returns:
            ModelFSMStateSnapshot initialized with the given state and
            default empty context and history.

        Example:
            >>> snapshot = ModelFSMStateSnapshot.create_initial("idle")
            >>> snapshot.current_state
            'idle'
            >>> snapshot.context
            {}
            >>> snapshot.history
            []
        """
        return cls(current_state=initial_state)

    def transition_to(
        self,
        new_state: str,
        *,
        new_context: FSMContextType | None = None,
    ) -> ModelFSMStateSnapshot:
        """
        Create a new snapshot representing a state transition.

        This is the preferred method for FSM state transitions. It creates a new
        immutable snapshot with the updated state, preserving the immutability
        contract by never mutating the existing snapshot.

        Args:
            new_state: The target state name to transition to.
            new_context: Optional new context data. If provided, it is merged
                with the existing context (new values override existing ones).
                If None, the existing context is preserved unchanged.

        Returns:
            A new ModelFSMStateSnapshot with:
            - current_state set to new_state
            - context merged with new_context (if provided)
            - history extended with the previous current_state

        Example:
            >>> snapshot = ModelFSMStateSnapshot.create_initial("idle")
            >>> snapshot = snapshot.transition_to("processing")
            >>> snapshot.current_state
            'processing'
            >>> snapshot.history
            ['idle']
            >>> snapshot = snapshot.transition_to("completed", new_context={"result": "ok"})
            >>> snapshot.current_state
            'completed'
            >>> snapshot.history
            ['idle', 'processing']
            >>> snapshot.context
            {'result': 'ok'}
        """
        # Always create a new dict to prevent aliasing of mutable context
        # Even when new_context is None, we copy self.context to avoid
        # accidental mutations affecting the original snapshot
        updated_context = (
            {**self.context} if new_context is None else {**self.context, **new_context}
        )
        return ModelFSMStateSnapshot(
            current_state=new_state,
            context=updated_context,
            history=[*self.history, self.current_state],
        )


# Export for use
__all__ = ["ModelFSMStateSnapshot"]
