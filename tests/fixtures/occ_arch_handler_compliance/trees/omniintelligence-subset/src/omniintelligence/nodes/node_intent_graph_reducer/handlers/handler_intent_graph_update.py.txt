# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure graph update handlers for the Intent Graph Reducer.

Implements transition accumulation logic for the directed intent graph.
Each handler is a pure function: (graph_state, event_data) -> None
(mutations are applied in-place on the mutable graph state).

Two event types drive graph updates:

1. Intent Classification events — update node occurrence counts and detect
   transitions (when the same session classifies two sequential intents).

2. Outcome Label events — update node and edge success rates after a session
   is labeled as succeeded or failed.

Design:
    - Config-table-driven: no hardcoded class conditionals
    - Pure functions (no I/O, no logging, no side effects beyond state mutation)
    - Deterministic: same input sequence always produces same graph state

ONEX Compliance:
    - No try/except at this level — errors propagate to the orchestrating handler
    - Pure computation, no logging
"""

from __future__ import annotations

from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass

from omniintelligence.nodes.node_intent_graph_reducer.models.model_intent_graph_state import (
    IntentGraphEdgeState,
    IntentGraphNodeState,
    ModelIntentGraphState,
)

__all__ = [
    "update_graph_on_classification",
    "update_graph_on_outcome",
    "get_top_transitions",
    "get_node_success_rate",
]


# =============================================================================
# Graph Upsert Helpers
# =============================================================================


def _upsert_node(
    graph: ModelIntentGraphState,
    intent_class: EnumIntentClass,
    session_id: str,
) -> IntentGraphNodeState:
    """Ensure a node exists for the given intent class and return it.

    Args:
        graph: The mutable graph state to update.
        intent_class: The intent class to upsert a node for.
        session_id: Session ID used for provenance (ignored after first creation).

    Returns:
        The existing or newly created IntentGraphNodeState.
    """
    if intent_class not in graph.nodes:
        graph.nodes[intent_class] = IntentGraphNodeState(
            intent_class=intent_class,
        )
    _ = session_id  # session_id is accepted for API consistency; not stored on the node
    return graph.nodes[intent_class]


def _upsert_edge(
    graph: ModelIntentGraphState,
    from_class: EnumIntentClass,
    to_class: EnumIntentClass,
) -> IntentGraphEdgeState:
    """Ensure an edge exists for the given transition pair and return it.

    Args:
        graph: The mutable graph state to update.
        from_class: Source intent class.
        to_class: Target intent class.

    Returns:
        The existing or newly created IntentGraphEdgeState.
    """
    key = (from_class, to_class)
    if key not in graph.edges:
        graph.edges[key] = IntentGraphEdgeState(
            from_intent_class=from_class,
            to_intent_class=to_class,
        )
    return graph.edges[key]


# =============================================================================
# Public Update Handlers
# =============================================================================


def update_graph_on_classification(
    graph: ModelIntentGraphState,
    *,
    session_id: str,
    intent_class: EnumIntentClass,
    cost_usd: float = 0.0,
) -> None:
    """Update the intent graph when a new classification event is received.

    Upserts the node for the classified intent class, increments its
    occurrence count, and accumulates cost. If the same session previously
    classified an intent, a transition edge is recorded between the prior
    and current intent classes.

    Args:
        graph: The mutable graph state to update in place.
        session_id: Session ID from the classification event.
        intent_class: The classified intent class.
        cost_usd: Incremental cost contribution for this classification (0.0
            if not yet known; updated later via outcome events).
    """
    # Upsert the node
    node = _upsert_node(graph, intent_class, session_id)
    node.occurrence_count += 1
    node.total_cost_usd += cost_usd

    # If there is a prior intent for this session, record the transition
    prior_class = graph.session_last_intent.get(session_id)
    if prior_class is not None and prior_class is not intent_class:
        edge = _upsert_edge(graph, prior_class, intent_class)
        edge.transition_count += 1
        # Track penultimate intent so outcome events can locate this edge
        graph.session_previous_intent[session_id] = prior_class
    elif prior_class is None:
        # No previous intent — clear any stale penultimate entry
        graph.session_previous_intent.pop(session_id, None)

    # Update the session's last-seen intent
    graph.session_last_intent[session_id] = intent_class


def update_graph_on_outcome(
    graph: ModelIntentGraphState,
    *,
    session_id: str,
    intent_class: EnumIntentClass,
    success: bool,
    cost_usd: float = 0.0,
) -> None:
    """Update the intent graph when an outcome label event is received.

    Recalculates the node's success rate and updates transition edge success
    rates for any transition that ended at this intent class in this session.

    Args:
        graph: The mutable graph state to update in place.
        session_id: Session ID from the outcome event.
        intent_class: The intent class that was labeled.
        success: True if the session outcome was successful.
        cost_usd: Total session cost (used to update edge cost average).
    """
    # Update node outcome statistics
    node = _upsert_node(graph, intent_class, session_id)
    node.total_outcomes += 1
    if success:
        node.total_successes += 1
    if cost_usd > 0.0:
        # Outcome cost supplements the running total; occurrence_count was already
        # incremented at classification time and is not changed here.
        node.total_cost_usd += cost_usd

    # Update transition edge success rates for the transition that led to this
    # intent class. The penultimate intent (session_previous_intent) is the
    # from_class; the current intent_class is the to_class.
    previous_class = graph.session_previous_intent.get(session_id)
    if previous_class is not None:
        key = (previous_class, intent_class)
        if key in graph.edges:
            edge = graph.edges[key]
            outcome_rate = 1.0 if success else 0.0
            edge.total_success_rate_sum += outcome_rate
            edge.total_cost_usd += cost_usd
            edge.total_cost_samples += 1


# =============================================================================
# Query Helpers
# =============================================================================


def get_top_transitions(
    graph: ModelIntentGraphState,
    *,
    top_n: int = 10,
) -> list[IntentGraphEdgeState]:
    """Return the top N most common intent transitions, by transition_count.

    Args:
        graph: The graph state to query.
        top_n: Maximum number of transitions to return.

    Returns:
        List of IntentGraphEdgeState sorted descending by transition_count.
    """
    sorted_edges = sorted(
        graph.edges.values(),
        key=lambda e: e.transition_count,
        reverse=True,
    )
    return sorted_edges[:top_n]


def get_node_success_rate(
    graph: ModelIntentGraphState,
    intent_class: EnumIntentClass,
) -> float:
    """Return the success rate for the given intent class node.

    Args:
        graph: The graph state to query.
        intent_class: The intent class to look up.

    Returns:
        Success rate in [0.0, 1.0]. Returns 0.0 if the node does not exist
        or has no labeled outcomes.
    """
    node = graph.nodes.get(intent_class)
    if node is None:
        return 0.0
    return node.success_rate
