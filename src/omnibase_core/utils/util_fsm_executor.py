"""
FSM execution utilities for declarative state machines.

Pure functions for executing FSM transitions from ModelFSMSubcontract.
No side effects - returns results and intents.

Typing: Strongly typed with FSMContextType for runtime context flexibility.
Context dictionaries use FSMContextType (dict[str, object]) to allow dynamic execution data
while maintaining type clarity for FSM-specific usage.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, cast
from uuid import UUID

if TYPE_CHECKING:
    from typing import SupportsFloat

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.fsm import ModelFSMStateSnapshot as FSMState
from omnibase_core.models.fsm.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.fsm.model_fsm_transition_result import (
    ModelFSMTransitionResult as FSMTransitionResult,
)
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.payloads import (
    ModelPayloadFSMStateAction,
    ModelPayloadFSMTransitionAction,
    ModelPayloadLogEvent,
    ModelPayloadMetric,
    ModelPayloadPersistState,
)
from omnibase_core.types.type_fsm_context import FSMContextType
from omnibase_core.utils.util_fsm_expression_parser import parse_expression
from omnibase_core.utils.util_fsm_operators import evaluate_equals, evaluate_not_equals


async def execute_transition(
    fsm: ModelFSMSubcontract,
    current_state: str,
    trigger: str,
    context: FSMContextType,
) -> FSMTransitionResult:
    """
    Execute FSM transition declaratively from YAML contract.

    Pure function: (fsm_contract, state, trigger, context) → (result, intents)

    Args:
        fsm: FSM subcontract definition (from YAML)
        current_state: Current state name
        trigger: Trigger event name
        context: Execution context data

    Returns:
        FSMTransitionResult with new state and intents for side effects

    Raises:
        ModelOnexError: If transition is invalid or execution fails

    Example:
        Execute a transition in a data pipeline FSM::

            # Load FSM contract from YAML
            fsm = ModelFSMSubcontract(
                state_machine_name="data_pipeline",
                initial_state="idle",
                states=[...],
                transitions=[...],
            )

            # Execute transition from "idle" to "processing"
            result = await execute_transition(
                fsm=fsm,
                current_state="idle",
                trigger="start_processing",
                context={"data_sources": ["api", "db"], "batch_size": 100},
            )

            # Check result
            if result.success:
                print(f"Transitioned to: {result.new_state}")
                # Process intents for side effects
                for intent in result.intents:
                    await handle_intent(intent)
            else:
                print(f"Transition failed: {result.error}")
    """
    intents: list[ModelIntent] = []

    # 1. Validate current state exists
    state_def = _get_state_definition(fsm, current_state)
    if not state_def:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid current state: {current_state}",
            context={"fsm": fsm.state_machine_name, "state": current_state},
        )

    # 2. Find valid transition
    transition = _find_transition(fsm, current_state, trigger)
    if not transition:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"No transition for trigger '{trigger}' from state '{current_state}'",
            context={
                "fsm": fsm.state_machine_name,
                "state": current_state,
                "trigger": trigger,
            },
        )

    # 3. Evaluate transition conditions
    conditions_met = await _evaluate_conditions(transition, context)
    if not conditions_met:
        # Create intent to log condition failure
        intents.append(
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload=ModelPayloadLogEvent(
                    level="WARNING",
                    message=f"FSM transition conditions not met: {transition.transition_name}",
                    context={
                        "fsm": fsm.state_machine_name,
                        "from_state": current_state,
                        "to_state": transition.to_state,
                    },
                ),
                priority=3,
            )
        )

        return FSMTransitionResult(
            success=False,
            new_state=current_state,  # Stay in current state
            old_state=current_state,
            transition_name=transition.transition_name,
            intents=tuple(intents),  # Convert to tuple for immutability
            error="Transition conditions not met",
        )

    # 4. Execute exit actions from current state
    exit_intents = await _execute_state_actions(fsm, state_def, "exit", context)
    intents.extend(exit_intents)

    # 5. Execute transition actions
    transition_intents = await _execute_transition_actions(
        transition, context, correlation_id=fsm.correlation_id
    )
    intents.extend(transition_intents)

    # 6. Get target state definition
    target_state_def = _get_state_definition(fsm, transition.to_state)
    if not target_state_def:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid target state: {transition.to_state}",
            context={"fsm": fsm.state_machine_name, "state": transition.to_state},
        )

    # 7. Execute entry actions for new state
    entry_intents = await _execute_state_actions(
        fsm, target_state_def, "entry", context
    )
    intents.extend(entry_intents)

    # 8. Create persistence intent if enabled
    if fsm.persistence_enabled:
        intents.append(
            ModelIntent(
                intent_type="persist_state",
                target="state_persistence",
                payload=ModelPayloadPersistState(
                    state_key=f"fsm:{fsm.state_machine_name}:state",
                    state_data={
                        "fsm_name": fsm.state_machine_name,
                        "state": transition.to_state,
                        "previous_state": current_state,
                        "context": context,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    correlation_id=fsm.correlation_id,
                ),
                priority=1,  # High priority for persistence
            )
        )

    # 9. Create monitoring intent
    intents.append(
        ModelIntent(
            intent_type="record_metric",
            target="metrics_service",
            payload=ModelPayloadMetric(
                name="fsm.transition",
                value=1.0,
                metric_type="counter",
                labels={
                    "fsm": fsm.state_machine_name,
                    "from_state": current_state,
                    "to_state": transition.to_state,
                    "trigger": trigger,
                },
            ),
            priority=3,
        )
    )

    return FSMTransitionResult(
        success=True,
        new_state=transition.to_state,
        old_state=current_state,
        transition_name=transition.transition_name,
        intents=tuple(intents),  # Convert to tuple for immutability
        metadata=(
            ("conditions_evaluated", len(transition.conditions or [])),
            ("actions_executed", len(transition.actions or [])),
        ),
    )


async def validate_fsm_contract(fsm: ModelFSMSubcontract) -> list[str]:
    """
    Validate FSM contract for correctness.

    Pure validation function - no side effects.

    Args:
        fsm: FSM subcontract to validate

    Returns:
        List of validation errors (empty if valid)

    Example:
        Validate FSM contract before execution::

            # Load FSM contract
            fsm = ModelFSMSubcontract(
                state_machine_name="order_processing",
                initial_state="pending",
                states=[
                    ModelFSMStateDefinition(state_name="pending", is_initial=True),
                    ModelFSMStateDefinition(state_name="completed", is_terminal=True),
                ],
                transitions=[
                    ModelFSMStateTransition(
                        transition_name="complete_order",
                        from_state="pending",
                        to_state="completed",
                        trigger="complete",
                    )
                ],
                terminal_states=["completed"],
            )

            # Validate before execution
            errors = await validate_fsm_contract(fsm)
            if errors:
                print("FSM validation failed:")
                for error in errors:
                    print(f"  - {error}")
            else:
                print("FSM contract is valid")
                # Safe to execute transitions
    """
    errors: list[str] = []

    # Check initial state exists
    if not _get_state_definition(fsm, fsm.initial_state):
        errors.append(f"Initial state not defined: {fsm.initial_state}")

    # Check terminal states exist
    for terminal_state in fsm.terminal_states:
        if not _get_state_definition(fsm, terminal_state):
            errors.append(f"Terminal state not defined: {terminal_state}")

    # Check error states exist
    for error_state in fsm.error_states:
        if not _get_state_definition(fsm, error_state):
            errors.append(f"Error state not defined: {error_state}")

    # Check all transitions reference valid states
    for transition in fsm.transitions:
        # Support wildcard transitions
        if transition.from_state != "*":
            if not _get_state_definition(fsm, transition.from_state):
                errors.append(
                    f"Transition '{transition.transition_name}' references invalid from_state: {transition.from_state}"
                )
        if not _get_state_definition(fsm, transition.to_state):
            errors.append(
                f"Transition '{transition.transition_name}' references invalid to_state: {transition.to_state}"
            )

    # Check for unreachable states
    reachable_states = _find_reachable_states(fsm)
    all_states = {state.state_name for state in fsm.states}
    unreachable = all_states - reachable_states
    if unreachable:
        errors.append(f"Unreachable states: {', '.join(sorted(unreachable))}")

    # Check terminal states have no explicit outgoing transitions
    # (wildcard transitions with from_state="*" are naturally exempt as they don't match specific terminal state names)
    terminal_states_set = {
        state.state_name for state in fsm.states if state.is_terminal
    }
    for transition in fsm.transitions:
        if transition.from_state in terminal_states_set:
            # Terminal states should not have ANY explicit outgoing transitions
            errors.append(
                f"Terminal state '{transition.from_state}' has explicit outgoing transition: {transition.transition_name}"
            )

    return errors


def get_initial_state(fsm: ModelFSMSubcontract) -> FSMState:
    """
    Get initial FSM state.

    Args:
        fsm: FSM subcontract

    Returns:
        FSMState initialized to initial state with empty context

    Example:
        Initialize FSM state for a new execution::

            # Load FSM contract
            fsm = ModelFSMSubcontract(
                state_machine_name="workflow",
                initial_state="start",
                states=[...],
            )

            # Get initial state
            state = get_initial_state(fsm)
            print(f"Starting in state: {state.current_state}")  # "start"
            print(f"Context: {state.context}")                  # {}
            print(f"History: {state.history}")                  # []

            # Use state for first transition
            result = await execute_transition(
                fsm=fsm,
                current_state=state.current_state,
                trigger="begin",
                context=state.context,
            )
    """
    return FSMState(current_state=fsm.initial_state, context={}, history=[])


# Private helper functions


def _get_state_definition(
    fsm: ModelFSMSubcontract, state_name: str
) -> ModelFSMStateDefinition | None:
    """Find state definition by name."""
    for state in fsm.states:
        if state.state_name == state_name:
            return state
    return None


def _find_transition(
    fsm: ModelFSMSubcontract, from_state: str, trigger: str
) -> ModelFSMStateTransition | None:
    """Find transition matching from_state and trigger."""
    # First look for exact match
    for transition in fsm.transitions:
        if transition.from_state == from_state and transition.trigger == trigger:
            return transition

    # Then look for wildcard transitions
    for transition in fsm.transitions:
        if transition.from_state == "*" and transition.trigger == trigger:
            return transition

    return None


async def _evaluate_conditions(
    transition: ModelFSMStateTransition,
    context: FSMContextType,
) -> bool:
    """
    Evaluate all transition conditions.

    Args:
        transition: Transition with conditions to evaluate
        context: Execution context for condition evaluation

    Returns:
        True if all conditions met, False otherwise
    """
    if not transition.conditions:
        return True

    for condition in transition.conditions:
        # Skip optional conditions if not required
        if not condition.required:
            continue

        # Evaluate condition based on type and expression
        condition_met = await _evaluate_single_condition(condition, context)

        if not condition_met:
            return False

    return True


def _get_nested_field_value(context: FSMContextType, field_path: str) -> object:
    """
    Get value from nested dict using dot notation path.

    Supports nested field access like "user.email" or "data.items.count".

    Args:
        context: The context dictionary
        field_path: Dot-separated path like "user.email" or "data.items.count"

    Returns:
        The value at the path, or None if any segment is missing or
        if any intermediate value is not a dict

    Examples:
        >>> _get_nested_field_value({"user": {"email": "test@example.com"}}, "user.email")
        'test@example.com'

        >>> _get_nested_field_value({"count": 5}, "count")
        5

        >>> _get_nested_field_value({"user": {"name": "Bob"}}, "user.email")
        None

        >>> _get_nested_field_value({"user": None}, "user.email")
        None
    """
    # Fast path: no dots means simple field access
    if "." not in field_path:
        return context.get(field_path)

    # Split and traverse for nested paths
    segments = field_path.split(".")
    current: object = context

    for segment in segments:
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None

    return current


async def _evaluate_single_condition(
    condition: ModelFSMTransitionCondition,
    context: FSMContextType,
) -> bool:
    """
    Evaluate a single transition condition.

    Args:
        condition: Condition to evaluate
        context: Execution context

    Returns:
        True if condition met, False otherwise

    Important - Type Coercion Behavior:
        The 'equals' and 'not_equals' operators perform STRING-BASED comparison
        by casting both sides to str before evaluation.

        Why This Design?
        - FSM conditions are typically defined in YAML/JSON where all values are strings
        - String coercion ensures consistent behavior regardless of value source
        - Avoids type mismatch errors when comparing config values to runtime values

        Examples:
            10 == "10"           → True  (both become "10")
            10 != "10"           → False (both become "10")
            True == "True"       → True  (both become "True")
            None == "None"       → True  (both become "None")
            [1,2] == "[1, 2]"    → True  (both become "[1, 2]")

        Impact:
            - Type information is LOST during comparison
            - Integer 0 is treated same as string "0"
            - Boolean True is treated same as string "True"

        Workarounds:
            - For numeric comparison: Use 'greater_than' or 'less_than' operators
            - For type-aware checks: Preprocess context values before FSM execution
            - For strict equality: Add custom condition evaluator

        Other Operators:
            - 'greater_than', 'less_than': Cast to float (preserves numeric comparison)
            - 'min_length', 'max_length': Cast expected value to int
            - 'exists', 'not_exists': No type coercion (presence check only)
    """
    # Expression-based evaluation using validated parser
    # Format: "field operator value"
    # Example: "data_sources min_length 1"
    #
    # Uses parse_expression for validation:
    # - Ensures exactly 3 tokens (field, operator, value)
    # - Validates operator is in SUPPORTED_OPERATORS
    # - Security: Rejects underscore-prefixed field names

    try:
        field_name, operator, expected_value = parse_expression(condition.expression)
    except ModelOnexError:
        # Invalid expression format - fail gracefully
        # parse_expression raises for:
        # - Empty expression
        # - Wrong token count (not exactly 3)
        # - Unsupported operator
        # - Underscore-prefixed field names (security)
        return False

    # Use nested field access to support dot notation (e.g., "user.email")
    field_value = _get_nested_field_value(context, field_name)

    # Evaluate based on operator
    # Standard operators (validated by ModelFSMTransitionCondition)
    if operator == "==" or operator == "equals":
        # STRING-BASED COMPARISON via fsm_operators module
        # Both values are cast to str before comparison (INTENTIONAL)
        # See fsm_operators.evaluate_equals docstring for type coercion behavior
        return evaluate_equals(field_value, expected_value)
    elif operator == "!=" or operator == "not_equals":
        # STRING-BASED COMPARISON via fsm_operators module
        # Both values are cast to str before comparison (INTENTIONAL)
        # See fsm_operators.evaluate_not_equals docstring for type coercion behavior
        return evaluate_not_equals(field_value, expected_value)
    elif operator == ">":
        try:
            # Cast to SupportsFloat - TypeError caught if not actually numeric
            return float(cast("SupportsFloat", field_value) or 0) > float(
                expected_value or "0"
            )
        except VALIDATION_ERRORS:
            # fallback-ok: non-numeric values return False for numeric comparison
            return False
    elif operator == "<":
        try:
            # Cast to SupportsFloat - TypeError caught if not actually numeric
            return float(cast("SupportsFloat", field_value) or 0) < float(
                expected_value or "0"
            )
        except VALIDATION_ERRORS:
            # fallback-ok: non-numeric values return False for numeric comparison
            return False
    elif operator == ">=":
        try:
            # Cast to SupportsFloat - TypeError caught if not actually numeric
            return float(cast("SupportsFloat", field_value) or 0) >= float(
                expected_value or "0"
            )
        except VALIDATION_ERRORS:
            # fallback-ok: non-numeric values return False for numeric comparison
            return False
    elif operator == "<=":
        try:
            # Cast to SupportsFloat - TypeError caught if not actually numeric
            return float(cast("SupportsFloat", field_value) or 0) <= float(
                expected_value or "0"
            )
        except VALIDATION_ERRORS:
            # fallback-ok: non-numeric values return False for numeric comparison
            return False
    elif operator == "in":
        # Check if field_value is in expected_value (comma-separated list or iterable)
        # Note: expected_value is always a string from parse_expression
        expected_list = [v.strip() for v in expected_value.split(",")]
        return str(field_value) in expected_list
    elif operator == "not_in":
        # Check if field_value is NOT in expected_value (comma-separated list)
        # Note: expected_value is always a string from parse_expression
        expected_list = [v.strip() for v in expected_value.split(",")]
        return str(field_value) not in expected_list
    elif operator == "contains":
        # Check if field_value contains expected_value as substring
        if field_value is None:
            return False
        return str(expected_value) in str(field_value)
    elif operator == "matches":
        # Regex match (basic pattern matching)
        import re

        if field_value is None:
            return False
        try:
            return bool(re.match(str(expected_value), str(field_value)))
        except re.error:
            return False

    # Unknown operator - fail safe
    return False


async def _execute_state_actions(
    fsm: ModelFSMSubcontract,
    state: ModelFSMStateDefinition,
    action_type: str,  # "entry" or "exit"
    context: FSMContextType,
) -> list[ModelIntent]:
    """
    Execute state entry/exit actions, returning intents.

    Args:
        fsm: FSM subcontract
        state: State definition with actions
        action_type: "entry" or "exit"
        context: Execution context

    Returns:
        List of intents for executing actions
    """
    intents: list[ModelIntent] = []

    actions = state.entry_actions if action_type == "entry" else state.exit_actions

    # Guard against None actions
    if not actions:
        return []

    # Convert action_type to the payload format - typed as Literal for type safety
    payload_action_type: Literal["on_enter", "on_exit"] = (
        "on_enter" if action_type == "entry" else "on_exit"
    )

    for action_name in actions:
        # Create intent for each action
        intents.append(
            ModelIntent(
                intent_type="fsm_state_action",
                target="action_executor",
                payload=ModelPayloadFSMStateAction(
                    state_name=state.state_name,
                    action_type=payload_action_type,
                    action_name=action_name,
                    parameters={"fsm": fsm.state_machine_name, "context": context},
                    correlation_id=fsm.correlation_id,
                ),
                priority=2,
            )
        )

    return intents


async def _execute_transition_actions(
    transition: ModelFSMStateTransition,
    context: FSMContextType,
    *,
    correlation_id: UUID | None = None,
) -> list[ModelIntent]:
    """
    Execute transition actions, returning intents.

    Args:
        transition: Transition with actions to execute
        context: Execution context
        correlation_id: Optional correlation ID from FSM subcontract for tracing

    Returns:
        List of intents for executing actions
    """
    intents: list[ModelIntent] = []

    # Guard against None actions
    if not transition.actions:
        return []

    for action in transition.actions:
        intents.append(
            ModelIntent(
                intent_type="fsm_transition_action",
                target="action_executor",
                payload=ModelPayloadFSMTransitionAction(
                    from_state=transition.from_state,
                    to_state=transition.to_state,
                    trigger=transition.trigger,
                    action_name=action.action_name,
                    parameters={
                        "action_type": action.action_type,
                        "transition_name": transition.transition_name,
                        "context": context,
                        "is_critical": action.is_critical,
                        "timeout_ms": action.timeout_ms,
                    },
                    correlation_id=correlation_id,
                ),
                priority=2,
            )
        )

    return intents


def _find_reachable_states(fsm: ModelFSMSubcontract) -> set[str]:
    """
    Find all states reachable from initial state.

    Args:
        fsm: FSM subcontract

    Returns:
        Set of reachable state names
    """
    reachable = {fsm.initial_state}
    queue = [fsm.initial_state]

    while queue:
        current = queue.pop(0)

        for transition in fsm.transitions:
            # Handle wildcard transitions
            if transition.from_state == "*" or transition.from_state == current:
                if transition.to_state not in reachable:
                    reachable.add(transition.to_state)
                    queue.append(transition.to_state)

    return reachable


# Public API
__all__ = [
    "FSMState",
    "FSMTransitionResult",
    "execute_transition",
    "get_initial_state",
    "validate_fsm_contract",
]
