"""
FSM state snapshot model.

Frozen state representation for pure FSM pattern.
Follows ONEX one-model-per-file architecture.

Note:
    The context field uses dict[str, Any] to allow flexible FSM context data.
    This is an intentional design decision since FSM context can contain
    arbitrary runtime state that varies per FSM implementation.

Immutability Considerations:
    While this dataclass uses frozen=True to prevent field reassignment,
    Python's frozen dataclasses have inherent limitations with mutable containers:

    1. **history field**: Changed to tuple[str, ...] for true immutability.
       Tuples are immutable and cannot be modified after creation.

    2. **context field**: Uses dict[str, Any] which is mutable by Python design.
       The dict container itself cannot be reassigned (frozen), but its contents
       CAN still be modified (e.g., context["key"] = "new_value" will work).

       Alternatives considered but not implemented:
       - types.MappingProxyType: Would provide read-only view but loses dict type
       - frozendict (third-party): Would require additional dependency
       - Pydantic model with frozen=True: Would change the class structure

       Current contract: Callers MUST NOT mutate context after snapshot creation.
       FSM executors should create new snapshots with new context dicts rather
       than modifying existing context.

    This design balances true immutability where practical (history) with
    documented contracts where full immutability would be too restrictive (context).
"""

from dataclasses import dataclass

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
            **WARNING**: While the context field cannot be reassigned, the dict
            contents are still mutable. Callers MUST NOT modify context after
            snapshot creation to maintain FSM purity.
        history: Tuple of previously visited state names for debugging/auditing.
            Uses tuple instead of list for true immutability.

    Immutability Contract:
        - **Guaranteed immutable**: current_state (str), history (tuple)
        - **Contractually immutable**: context (dict - do not modify after creation)
        - Field reassignment is blocked by frozen=True (e.g., snapshot.current_state = "x" raises)
        - FSM executors MUST create new snapshots rather than mutating existing ones

    Example:
        >>> snapshot = ModelFSMStateSnapshot(
        ...     current_state="processing",
        ...     context={"request_id": "abc123", "retry_count": 2},
        ...     history=("initial", "validating"),
        ... )
        >>> snapshot.current_state
        'processing'
        >>> snapshot.history  # Immutable tuple
        ('initial', 'validating')

    Warning:
        Do NOT mutate context after creation::

            # WRONG - violates immutability contract
            snapshot.context["new_key"] = "value"

            # CORRECT - create new snapshot with updated context
            new_context = {**snapshot.context, "new_key": "value"}
            new_snapshot = ModelFSMStateSnapshot(
                current_state=snapshot.current_state,
                context=new_context,
                history=snapshot.history + ("new_state",),
            )
    """

    current_state: str
    context: FSMContextType
    history: tuple[str, ...] = ()


# Export for use
__all__ = ["ModelFSMStateSnapshot"]
