"""
FSM Semantic Analysis Module.

This module validates FSM (Finite State Machine) **semantics**, not structure.
Pydantic already validates structural correctness (e.g., all states exist,
transitions reference valid states). This module detects semantic issues like:

- Unreachable states (defined but never reached from initial state)
- Cycles without exit conditions (infinite loops with no escape)
- Ambiguous transitions (same trigger from same state → multiple targets)
- Dead transitions (transitions that can never fire due to conditions)
- Missing transitions (non-terminal states with no outgoing paths)
- Duplicate state names (same name appears multiple times)

All functions work with frozen (immutable) ModelFSMSubcontract instances
and return comprehensive analysis results without raising exceptions.

Usage:
    from omnibase_core.validation.fsm_analysis import analyze_fsm

    result = analyze_fsm(fsm_subcontract)
    if not result.is_valid:
        for error in result.errors:
            print(error)
"""

from __future__ import annotations

from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.validation.model_ambiguous_transition import (
    ModelAmbiguousTransition,
)
from omnibase_core.models.validation.model_fsm_analysis_result import (
    ModelFSMAnalysisResult,
)


def analyze_fsm(fsm: ModelFSMSubcontract) -> ModelFSMAnalysisResult:
    """
    Perform comprehensive semantic analysis on an FSM subcontract.

    This is the main entry point for FSM validation. It runs all semantic
    analysis checks and aggregates results into a single comprehensive result.

    The function does NOT raise exceptions - all issues are returned in the
    result object for programmatic inspection and handling.

    Args:
        fsm: Immutable FSM subcontract to analyze

    Returns:
        Comprehensive analysis result with all detected semantic issues.
        Check result.is_valid to determine if FSM is semantically correct.

    Example:
        >>> result = analyze_fsm(fsm_subcontract)
        >>> if not result.is_valid:
        ...     for error in result.errors:
        ...         print(f"FSM Error: {error}")
        >>> if result.unreachable_states:
        ...     print(f"Unreachable: {result.unreachable_states}")
    """
    # Run all individual analysis functions
    unreachable = _find_unreachable_states(fsm)
    cycles = _find_cycles_without_exit(fsm)
    ambiguous = _find_ambiguous_transitions(fsm)
    dead = _find_dead_transitions(fsm, unreachable_states=unreachable)
    missing = _find_missing_transitions(fsm)
    duplicates = _find_duplicate_state_names(fsm)

    # Build comprehensive error messages
    errors: list[str] = []

    if unreachable:
        errors.append(
            f"Found {len(unreachable)} unreachable state(s): {', '.join(sorted(unreachable))}"
        )

    if cycles:
        for cycle in cycles:
            errors.append(
                f"Found cycle without exit: {' -> '.join(cycle)} -> {cycle[0]}"
            )

    if ambiguous:
        for amb in ambiguous:
            errors.append(
                f"Ambiguous transition: {amb.from_state} + {amb.trigger} -> "
                f"{{{', '.join(sorted(amb.target_states))}}}"
            )

    if dead:
        errors.append(
            f"Found {len(dead)} dead transition(s): {', '.join(sorted(dead))}"
        )

    if missing:
        errors.append(
            f"Found {len(missing)} state(s) missing transitions: {', '.join(sorted(missing))}"
        )

    if duplicates:
        errors.append(
            f"Found {len(duplicates)} duplicate state name(s): {', '.join(sorted(duplicates))}"
        )

    return ModelFSMAnalysisResult(
        unreachable_states=unreachable,
        cycles_without_exit=cycles,
        ambiguous_transitions=ambiguous,
        dead_transitions=dead,
        missing_transitions=missing,
        duplicate_state_names=duplicates,
        errors=errors,
    )


def _find_unreachable_states(fsm: ModelFSMSubcontract) -> list[str]:
    """
    Find all states that cannot be reached from the initial state.

    Uses breadth-first search starting from the initial state to identify
    all reachable states, then returns the complement (unreachable states).

    Handles wildcard transitions ('*') which can transition FROM any state.

    Args:
        fsm: Immutable FSM subcontract to analyze

    Returns:
        List of state names that are unreachable from initial state.
        Empty list if all states are reachable.
    """
    all_state_names = {state.state_name for state in fsm.states}

    # Build adjacency list for forward reachability
    # state -> list of states reachable via transitions
    adjacency: dict[str, list[str]] = {name: [] for name in all_state_names}

    # Collect wildcard transition targets (reachable from any state)
    wildcard_targets: list[str] = []

    for transition in fsm.transitions:
        if transition.from_state == "*":
            # Wildcard: add to_state as reachable from ALL states
            wildcard_targets.append(transition.to_state)
        else:
            adjacency[transition.from_state].append(transition.to_state)

    # Add wildcard targets to all states' adjacency lists
    for state_name in all_state_names:
        adjacency[state_name].extend(wildcard_targets)

    # BFS from initial state
    reachable: set[str] = set()
    queue: list[str] = [fsm.initial_state]

    while queue:
        current = queue.pop(0)
        if current in reachable:
            continue
        reachable.add(current)

        for next_state in adjacency.get(current, []):
            if next_state not in reachable:
                queue.append(next_state)

    # Return states that are not reachable
    unreachable = all_state_names - reachable
    return sorted(unreachable)


def _find_cycles_without_exit(fsm: ModelFSMSubcontract) -> list[list[str]]:
    """
    Find all cycles (loops) in the FSM that have no path to terminal states.

    A cycle without exit is a strongly connected component where:
    1. States can reach each other in a loop
    2. No state in the cycle can reach a terminal state

    This creates infinite loops that trap the FSM with no way to complete.

    Uses Tarjan's algorithm to find SCCs, then checks if each SCC can reach
    a terminal state.

    Args:
        fsm: Immutable FSM subcontract to analyze

    Returns:
        List of cycles, where each cycle is a list of state names forming
        the loop. Empty list if no problematic cycles exist.
    """
    all_state_names = {state.state_name for state in fsm.states}
    terminal_states = set(fsm.terminal_states)

    # Build adjacency list
    adjacency: dict[str, list[str]] = {name: [] for name in all_state_names}
    wildcard_targets: list[str] = []

    for transition in fsm.transitions:
        if transition.from_state == "*":
            wildcard_targets.append(transition.to_state)
        else:
            adjacency[transition.from_state].append(transition.to_state)

    # Add wildcard targets
    for state_name in all_state_names:
        adjacency[state_name].extend(wildcard_targets)

    # Find SCCs using Tarjan's algorithm
    index_counter = [0]
    stack: list[str] = []
    lowlinks: dict[str, int] = {}
    index_map: dict[str, int] = {}
    on_stack: set[str] = set()
    sccs: list[list[str]] = []

    def strongconnect(node: str) -> None:
        index_map[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack.add(node)

        for successor in adjacency.get(node, []):
            if successor not in index_map:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in on_stack:
                lowlinks[node] = min(lowlinks[node], index_map[successor])

        # If node is root of SCC
        if lowlinks[node] == index_map[node]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == node:
                    break
            if len(scc) > 1 or (len(scc) == 1 and node in adjacency.get(node, [])):
                sccs.append(scc)

    for state in all_state_names:
        if state not in index_map:
            strongconnect(state)

    # For each SCC, check if it can reach a terminal state
    cycles_without_exit: list[list[str]] = []

    for scc in sccs:
        # BFS from SCC to find if terminal is reachable
        visited: set[str] = set()
        queue = list(scc)
        can_exit = False

        while queue and not can_exit:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current in terminal_states:
                can_exit = True
                break

            for next_state in adjacency.get(current, []):
                if next_state not in visited:
                    queue.append(next_state)

        if not can_exit:
            cycles_without_exit.append(sorted(scc))

    return cycles_without_exit


def _find_ambiguous_transitions(
    fsm: ModelFSMSubcontract,
) -> list[ModelAmbiguousTransition]:
    """
    Find transitions where the same trigger from the same state leads to
    multiple possible target states with the SAME priority.

    This is a semantic error because the FSM executor cannot determine which
    transition to follow when the trigger fires. Different priorities provide
    deterministic resolution (higher priority wins).

    Wildcard transitions ('*') are NOT considered ambiguous with specific state
    transitions because specific states take precedence over wildcards.

    Args:
        fsm: Immutable FSM subcontract to analyze

    Returns:
        List of ambiguous transitions detected. Empty list if no ambiguity exists.
    """
    # Group transitions by (from_state, trigger, priority)
    # Key: (from_state, trigger), Value: dict of priority -> list of to_states
    transition_groups: dict[tuple[str, str], dict[int, list[str]]] = {}

    for transition in fsm.transitions:
        # Skip wildcard transitions - they don't create ambiguity
        # because specific state transitions take precedence
        if transition.from_state == "*":
            continue

        key = (transition.from_state, transition.trigger)
        if key not in transition_groups:
            transition_groups[key] = {}

        priority = transition.priority
        if priority not in transition_groups[key]:
            transition_groups[key][priority] = []

        transition_groups[key][priority].append(transition.to_state)

    # Find groups with 2+ distinct targets at the SAME priority
    ambiguous: list[ModelAmbiguousTransition] = []

    for (from_state, trigger), priority_map in transition_groups.items():
        for _priority, targets in priority_map.items():
            unique_targets = list(set(targets))
            if len(unique_targets) >= 2:
                ambiguous.append(
                    ModelAmbiguousTransition(
                        from_state=from_state,
                        trigger=trigger,
                        target_states=sorted(unique_targets),
                    )
                )

    return ambiguous


def _find_dead_transitions(
    fsm: ModelFSMSubcontract,
    *,
    unreachable_states: list[str] | None = None,
) -> list[str]:
    """
    Find transitions that can never fire due to unreachable source states.

    A transition is dead if its source state is unreachable from the initial
    state. This means the transition can never be triggered because the FSM
    can never reach the state from which the transition originates.

    Note: Condition satisfiability analysis is not performed as conditions
    depend on runtime context that cannot be statically analyzed.

    Wildcard transitions ('*') are never considered dead because they apply
    to all reachable states.

    Args:
        fsm: Immutable FSM subcontract to analyze
        unreachable_states: Pre-computed unreachable states (optimization).
            If None, will compute internally.

    Returns:
        List of transition names that are dead/unreachable.
        Empty list if all transitions are potentially reachable.
    """
    # Use pre-computed unreachable states if provided, otherwise compute
    if unreachable_states is None:
        unreachable_set = set(_find_unreachable_states(fsm))
    else:
        unreachable_set = set(unreachable_states)

    dead: list[str] = []
    for transition in fsm.transitions:
        # Wildcard transitions are never dead (apply to all states)
        if transition.from_state == "*":
            continue

        # If from_state is unreachable, the transition is dead
        if transition.from_state in unreachable_set:
            dead.append(transition.transition_name)

    return sorted(dead)


def _find_missing_transitions(fsm: ModelFSMSubcontract) -> list[str]:
    """
    Find non-terminal states that have no outgoing transitions.

    A non-terminal state MUST have at least one outgoing transition to allow
    the FSM to progress. States with no outgoing transitions trap the FSM
    in that state permanently (unless they are terminal states).

    Terminal states and error states are allowed to have no outgoing transitions.

    Wildcard transitions ('*') count as outgoing transitions for ALL states.

    Args:
        fsm: Immutable FSM subcontract to analyze

    Returns:
        List of state names that are missing outgoing transitions.
        Empty list if all non-terminal states have transitions.
    """
    terminal_states = set(fsm.terminal_states)
    error_states = set(fsm.error_states)

    # Collect states with explicit outgoing transitions
    states_with_outgoing: set[str] = set()
    has_wildcard_transition = False

    for transition in fsm.transitions:
        if transition.from_state == "*":
            # Wildcard means ALL states have at least this outgoing transition
            has_wildcard_transition = True
        else:
            states_with_outgoing.add(transition.from_state)

    # If there's a wildcard transition, all states have outgoing transitions
    if has_wildcard_transition:
        return []

    # Find non-terminal states without outgoing transitions
    missing: list[str] = []

    for state in fsm.states:
        state_name = state.state_name

        # Skip terminal and error states - they don't need outgoing transitions
        if state_name in terminal_states or state_name in error_states:
            continue

        # Check if state has outgoing transitions
        if state_name not in states_with_outgoing:
            missing.append(state_name)

    return sorted(missing)


def _find_duplicate_state_names(fsm: ModelFSMSubcontract) -> list[str]:
    """
    Find state names that appear multiple times in the FSM definition.

    Duplicate state names create ambiguity and are not allowed. Each state
    must have a unique name within the FSM.

    Args:
        fsm: Immutable FSM subcontract to analyze

    Returns:
        List of state names that appear more than once.
        Empty list if all state names are unique.
    """
    # Count occurrences of each state name
    name_counts: dict[str, int] = {}

    for state in fsm.states:
        name = state.state_name
        name_counts[name] = name_counts.get(name, 0) + 1

    # Find names that appear more than once
    duplicates = [name for name, count in name_counts.items() if count > 1]

    return sorted(duplicates)


__all__ = [
    "ModelAmbiguousTransition",
    "ModelFSMAnalysisResult",
    "analyze_fsm",
]
