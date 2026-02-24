# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract Graph Data Model (OMN-2540).

Defines the core data model for the contract graph used in ONEX Local Agent
Graph Navigation. Provides ContractState, ContractTransition, TransitionGuard,
TransitionCost, ContractGraph, and registry snapshot types.

Design principles:
- Pydantic models with frozen=True for immutability
- Full type annotations for mypy strict compliance
- JSON-serializable for logging and debugging
- Idempotent construction from the same registry state
- No mutable global state; each session gets its own graph instance
"""

from pydantic import BaseModel, ConfigDict, Field


class TransitionGuard(BaseModel):
    """Guards that must pass for a transition to be valid.

    Guards are evaluated at action enumeration time and graph boundary
    enforcement time. All guard evaluation is pure and side-effect-free.

    Attributes:
        required_capabilities: Set of capability strings that the executing
            agent must possess. E.g. {"llm.generation", "storage.vector_db"}.
        required_schema_version: If set, the source state's schema_version must
            match this value for the guard to pass.
        policy_tier_max: If set, the source state's policy_tier must be
            less than or equal to this value (lower = more permissive).
            None means no policy tier restriction.
        precondition_keys: Keys that must be present in the source state's
            metadata for this guard to pass.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    required_capabilities: frozenset[str] = Field(
        default_factory=frozenset,
        description="Capability strings the executing agent must possess",
    )
    required_schema_version: str | None = Field(
        default=None,
        description="Required schema version of the source state, or None for any",
    )
    policy_tier_max: int | None = Field(
        default=None,
        description="Maximum allowed policy tier (inclusive). None = no restriction.",
    )
    precondition_keys: frozenset[str] = Field(
        default_factory=frozenset,
        description="Keys that must be present in source state metadata",
    )


class TransitionCost(BaseModel):
    """Cost metadata for a contract transition.

    Used for ordering transitions in the action set enumeration (lower cost
    transitions appear first).

    Attributes:
        diff_size_estimate: Estimated number of schema fields changed, 0 if unknown.
        latency_estimate_ms: Estimated latency in milliseconds, 0 if unknown.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    diff_size_estimate: int = Field(
        default=0,
        ge=0,
        description="Estimated number of schema fields changed by this transition",
    )
    latency_estimate_ms: int = Field(
        default=0,
        ge=0,
        description="Estimated latency in milliseconds for this transition",
    )

    @property
    def total_cost(self) -> int:
        """Composite cost score for ordering (lower = cheaper)."""
        return self.diff_size_estimate + self.latency_estimate_ms


class ContractState(BaseModel):
    """A node in the contract graph — a declared, schema-validated node contract.

    Each ContractState corresponds to a registered node contract in the ONEX
    node registry. The identity of a state is its node_id.

    Attributes:
        node_id: Unique identifier for this node contract (e.g., "node.datasource.select").
        schema_version: Semantic version string of the contract schema (e.g., "1.0.0").
        capabilities: Set of capability strings this node provides/requires.
        policy_tier: Numeric policy tier (0 = most permissive, higher = more restricted).
        metadata: Arbitrary key-value metadata from the registry entry.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str = Field(
        ...,
        description="Unique identifier for this contract state",
        min_length=1,
    )
    schema_version: str = Field(
        ...,
        description="Semantic version of the contract schema",
        min_length=1,
    )
    capabilities: frozenset[str] = Field(
        default_factory=frozenset,
        description="Capability strings associated with this node",
    )
    policy_tier: int = Field(
        default=0,
        ge=0,
        description="Policy restriction tier (0=most permissive, higher=more restricted)",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary string key-value metadata from the registry entry",
    )

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ContractState):
            return NotImplemented
        return self.node_id == other.node_id


class ContractTransition(BaseModel):
    """A directed edge in the contract graph — a typed transition between states.

    Transitions are derived strictly from declared node contracts; no inferred
    or hallucinated transitions are allowed.

    Attributes:
        transition_id: Unique identifier for this transition.
        source_state_id: node_id of the source ContractState.
        target_state_id: node_id of the target ContractState.
        input_types: Declared input type names for this transition.
        output_types: Declared output type names for this transition.
        preconditions: Human-readable precondition descriptions (used for
            matching in backward chaining).
        guard: Guards that must pass for this transition to be in the action set.
        cost: Cost metadata for ordering transitions.
        label: Human-readable label for display/debugging.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    transition_id: str = Field(
        ...,
        description="Unique identifier for this transition",
        min_length=1,
    )
    source_state_id: str = Field(
        ...,
        description="node_id of the source ContractState",
        min_length=1,
    )
    target_state_id: str = Field(
        ...,
        description="node_id of the target ContractState",
        min_length=1,
    )
    input_types: tuple[str, ...] = Field(
        default=(),
        description="Declared input type names for this transition",
    )
    output_types: tuple[str, ...] = Field(
        default=(),
        description="Declared output type names for this transition",
    )
    preconditions: tuple[str, ...] = Field(
        default=(),
        description="Precondition descriptions (keys or free text)",
    )
    guard: TransitionGuard = Field(
        default_factory=TransitionGuard,
        description="Guards that must pass for this transition to be available",
    )
    cost: TransitionCost = Field(
        default_factory=TransitionCost,
        description="Cost metadata for ordering transitions",
    )
    label: str = Field(
        default="",
        description="Human-readable label for this transition",
    )

    def __hash__(self) -> int:
        return hash(self.transition_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ContractTransition):
            return NotImplemented
        return self.transition_id == other.transition_id


class ContractGraph(BaseModel):
    """The contract graph: a finite, bounded, schema-enforced state space.

    The graph is constructed from a registry snapshot at navigation time.
    Each navigation session gets its own instance — no global mutable state.

    Supports:
    - Node lookup by ID: O(1)
    - Edge lookup by source state: O(1) (pre-indexed adjacency list)
    - Predecessor lookup by target state: O(1) (for backward chaining)
    - Full adjacency representation

    Attributes:
        states: All ContractState nodes, keyed by node_id.
        transitions: All ContractTransition edges, keyed by transition_id.
        adjacency: Mapping from source node_id to list of transition_ids.
        predecessors: Mapping from target node_id to list of transition_ids.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    states: dict[str, ContractState] = Field(
        default_factory=dict,
        description="All states, keyed by node_id",
    )
    transitions: dict[str, ContractTransition] = Field(
        default_factory=dict,
        description="All transitions, keyed by transition_id",
    )
    adjacency: dict[str, tuple[str, ...]] = Field(
        default_factory=dict,
        description="source node_id -> tuple of transition_ids (outgoing edges)",
    )
    predecessors: dict[str, tuple[str, ...]] = Field(
        default_factory=dict,
        description="target node_id -> tuple of transition_ids (incoming edges)",
    )

    def get_state(self, node_id: str) -> ContractState | None:
        """Look up a state by its node_id. Returns None if not found."""
        return self.states.get(node_id)

    def get_outgoing_transitions(self, node_id: str) -> list[ContractTransition]:
        """Return all outgoing transitions from the given state node_id."""
        transition_ids = self.adjacency.get(node_id, ())
        return [
            self.transitions[tid] for tid in transition_ids if tid in self.transitions
        ]

    def get_incoming_transitions(self, node_id: str) -> list[ContractTransition]:
        """Return all incoming transitions to the given state node_id."""
        transition_ids = self.predecessors.get(node_id, ())
        return [
            self.transitions[tid] for tid in transition_ids if tid in self.transitions
        ]

    def get_transition(self, transition_id: str) -> ContractTransition | None:
        """Look up a transition by its transition_id. Returns None if not found."""
        return self.transitions.get(transition_id)

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self.states)

    @property
    def edge_count(self) -> int:
        """Number of directed edges in the graph."""
        return len(self.transitions)


class RegistryNode(BaseModel):
    """A single node entry from the registry snapshot.

    This is the raw data structure provided by the node registry.
    ContractGraphBuilder converts these into ContractState and
    ContractTransition instances.

    Attributes:
        node_id: Unique node identifier.
        schema_version: Schema version string.
        capabilities: Capability strings.
        policy_tier: Policy restriction tier.
        metadata: Arbitrary metadata.
        declared_transitions: List of declared transition entries.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str = Field(..., min_length=1)
    schema_version: str = Field(..., min_length=1)
    capabilities: tuple[str, ...] = Field(default=())
    policy_tier: int = Field(default=0, ge=0)
    metadata: dict[str, str] = Field(default_factory=dict)
    declared_transitions: tuple["RegistryTransitionDecl", ...] = Field(default=())


class RegistryTransitionDecl(BaseModel):
    """A declared transition in a registry node entry.

    Attributes:
        transition_id: Unique ID for this transition.
        target_node_id: Target node_id for this transition.
        input_types: Input type names.
        output_types: Output type names.
        preconditions: Precondition descriptions.
        required_capabilities: Capabilities required by the guard.
        required_schema_version: Schema version required by the guard.
        policy_tier_max: Max policy tier for the guard.
        precondition_keys: Metadata keys required by the guard.
        diff_size_estimate: Estimated diff size for cost.
        latency_estimate_ms: Estimated latency for cost.
        label: Human-readable label.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    transition_id: str = Field(..., min_length=1)
    target_node_id: str = Field(..., min_length=1)
    input_types: tuple[str, ...] = Field(default=())
    output_types: tuple[str, ...] = Field(default=())
    preconditions: tuple[str, ...] = Field(default=())
    required_capabilities: tuple[str, ...] = Field(default=())
    required_schema_version: str | None = Field(default=None)
    policy_tier_max: int | None = Field(default=None)
    precondition_keys: tuple[str, ...] = Field(default=())
    diff_size_estimate: int = Field(default=0, ge=0)
    latency_estimate_ms: int = Field(default=0, ge=0)
    label: str = Field(default="")


class RegistrySnapshot(BaseModel):
    """A point-in-time snapshot of the node registry.

    Passed to ContractGraphBuilder.build() to produce a ContractGraph.
    Construction is idempotent: same snapshot -> same graph.

    Attributes:
        nodes: All registered node entries.
        snapshot_id: Optional identifier for this snapshot (for logging).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    nodes: tuple[RegistryNode, ...] = Field(
        default=(),
        description="All registered nodes in this snapshot",
    )
    snapshot_id: str = Field(
        default="",
        description="Optional identifier for this snapshot",
    )


__all__ = [
    "ContractGraph",
    "ContractState",
    "ContractTransition",
    "RegistryNode",
    "RegistrySnapshot",
    "RegistryTransitionDecl",
    "TransitionCost",
    "TransitionGuard",
]
