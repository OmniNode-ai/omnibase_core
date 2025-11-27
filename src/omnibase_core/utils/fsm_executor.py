"""
FSM execution utilities for declarative state machines.

Pure functions for executing FSM transitions from ModelFSMSubcontract.
No side effects - returns results and intents.

Typing: Strongly typed with strategic Any usage for runtime context flexibility.
Context dictionaries use dict[str, Any] as they contain dynamic execution data.
"""

from datetime import datetime
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.fsm.model_fsm_state_snapshot import (
    ModelFSMStateSnapshot as FSMState,
)
from omnibase_core.models.fsm.model_fsm_transition_result import (
    ModelFSMTransitionResult as FSMTransitionResult,
)
from omnibase_core.models.model_intent import ModelIntent


async def execute_transition(
    fsm: ModelFSMSubcontract,
    current_state: str,
    trigger: str,
    context: dict[str, Any],
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
                payload={
                    "level": "WARNING",
                    "message": f"FSM transition conditions not met: {transition.transition_name}",
                    "context": {
                        "fsm": fsm.state_machine_name,
                        "from_state": current_state,
                        "to_state": transition.to_state,
                    },
                },
                priority=3,
            )
        )

        return FSMTransitionResult(
            success=False,
            new_state=current_state,  # Stay in current state
            old_state=current_state,
            transition_name=transition.transition_name,
            intents=intents,
            error="Transition conditions not met",
        )

    # 4. Execute exit actions from current state
    exit_intents = await _execute_state_actions(fsm, state_def, "exit", context)
    intents.extend(exit_intents)

    # 5. Execute transition actions
    transition_intents = await _execute_transition_actions(transition, context)
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
                payload={
                    "fsm_name": fsm.state_machine_name,
                    "state": transition.to_state,
                    "previous_state": current_state,
                    "context": context,
                    "timestamp": datetime.now().isoformat(),
                },
                priority=1,  # High priority for persistence
            )
        )

    # 9. Create monitoring intent
    intents.append(
        ModelIntent(
            intent_type="record_metric",
            target="metrics_service",
            payload={
                "metric_name": "fsm_transition",
                "tags": {
                    "fsm": fsm.state_machine_name,
                    "from_state": current_state,
                    "to_state": transition.to_state,
                    "trigger": trigger,
                },
                "value": 1,
            },
            priority=3,
        )
    )

    return FSMTransitionResult(
        success=True,
        new_state=transition.to_state,
        old_state=current_state,
        transition_name=transition.transition_name,
        intents=intents,
        metadata={
            "conditions_evaluated": len(transition.conditions or []),
            "actions_executed": len(transition.actions or []),
        },
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
    context: dict[str, Any],
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


async def _evaluate_single_condition(
    condition: ModelFSMTransitionCondition,
    context: dict[str, Any],
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
    # Simple expression-based evaluation
    # Format: "field operator value"
    # Example: "data_sources min_length 1"

    parts = condition.expression.split()
    if len(parts) < 2:
        # Invalid expression format
        return False

    field_name = parts[0]
    operator = parts[1]
    expected_value = parts[2] if len(parts) > 2 else None

    field_value = context.get(field_name)

    # Evaluate based on operator
    if operator == "equals":
        # STRING-BASED COMPARISON: Both values are cast to str before comparison
        # This is INTENTIONAL to handle YAML/JSON config values consistently
        # Examples: 10 == "10" → True, True == "True" → True, None == "None" → True
        # WARNING: Type information is lost! Use greater_than/less_than for numeric checks
        # See function docstring for complete type coercion behavior documentation
        return str(field_value) == str(expected_value)
    elif operator == "not_equals":
        # STRING-BASED COMPARISON: Both values are cast to str before comparison
        # This is INTENTIONAL to handle YAML/JSON config values consistently
        # Examples: 10 != "10" → False, True != "True" → False
        # WARNING: Type information is lost! Use greater_than/less_than for numeric checks
        # See function docstring for complete type coercion behavior documentation
        return str(field_value) != str(expected_value)
    elif operator == "min_length":
        if not field_value:
            return False
        try:
            return len(field_value) >= int(expected_value or "0")
        except (TypeError, ValueError):
            return False
    elif operator == "max_length":
        if not field_value:
            return True
        try:
            return len(field_value) <= int(expected_value or "0")
        except (TypeError, ValueError):
            return False
    elif operator == "greater_than":
        try:
            return float(field_value or 0) > float(expected_value or "0")
        except (TypeError, ValueError):
            return False
    elif operator == "less_than":
        try:
            return float(field_value or 0) < float(expected_value or "0")
        except (TypeError, ValueError):
            return False
    elif operator == "exists":
        return field_name in context
    elif operator == "not_exists":
        return field_name not in context

    # Unknown operator - fail safe
    return False


async def _execute_state_actions(
    fsm: ModelFSMSubcontract,
    state: ModelFSMStateDefinition,
    action_type: str,  # "entry" or "exit"
    context: dict[str, Any],
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

    for action_name in actions:
        # Create intent for each action
        intents.append(
            ModelIntent(
                intent_type="fsm_state_action",
                target="action_executor",
                payload={
                    "action_name": action_name,
                    "action_type": action_type,
                    "state": state.state_name,
                    "fsm": fsm.state_machine_name,
                    "context": context,
                },
                priority=2,
            )
        )

    return intents


async def _execute_transition_actions(
    transition: ModelFSMStateTransition,
    context: dict[str, Any],
) -> list[ModelIntent]:
    """
    Execute transition actions, returning intents.

    Args:
        transition: Transition with actions to execute
        context: Execution context

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
                payload={
                    "action_name": action.action_name,
                    "action_type": action.action_type,
                    "transition": transition.transition_name,
                    "context": context,
                    "is_critical": action.is_critical,
                    "timeout_ms": action.timeout_ms,
                },
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
