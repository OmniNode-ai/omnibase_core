> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Contract-Driven NodeReducer v1.0

# Contract-Driven NodeReducer v1.0 Specification

> **Version**: 1.0.5
> **Date**: 2025-12-10
> **Status**: DRAFT - Ready for Implementation
> **Ticket**: [OMN-495](https://linear.app/omninode/issue/OMN-495)
> **Full Roadmap**: NODEREDUCER_VERSIONING_ROADMAP.md (to be created)
> **See Also**: [ONEX Terminology Guide](../standards/onex_terminology.md) for canonical definitions of Reducer, Intent, and other ONEX concepts.

---

## Executive Summary

This document defines the **minimal v1.0 implementation** of contract-driven `NodeReducer`. The goal is a stable foundation for FSM-driven state management that can be shipped safely and extended incrementally.

**v1.0 Scope**: FSM-driven state transitions with pure function semantics, Intent emission for side effects, entry/exit actions, conditional transitions, and state persistence. No parallel transitions, no complex condition expressions, no distributed state coordination.

**Core Philosophy**: The FSM executor is a pure function:

```text
execute_transition(fsm, snapshot, trigger, context) -> (new_snapshot, intents[])
```

All side effects are emitted as Intents for Effect nodes to execute. This maintains FSM executor purity and enables deterministic state transitions.

**v1.0.4+ Clarification**: The purity guarantee applies to the **FSM executor functions**, not to `NodeReducer` instances. See [Purity Boundary](#purity-boundary-v104-normative) for details.

---

## Table of Contents

1. [Conceptual Modes](#conceptual-modes)
2. [Design Principles](#design-principles)
3. [Purity Boundary (v1.0.4 Normative)](#purity-boundary-v104-normative)
4. [v1.0 Scope](#v10-scope)
5. [Core Models](#core-models)
6. [Enums](#enums)
7. [FSM Subcontract Models](#fsm-subcontract-models)
8. [Contract Validation Invariants](#contract-validation-invariants)
9. [Execution Model](#execution-model)
10. [Intent Pattern](#intent-pattern)
11. [FSM Metadata Contract](#fsm-metadata-contract)
12. [Error Model](#error-model-v10)
13. [NodeReducer Behavior](#v10-nodereducer-behavior)
14. [Example Contracts](#example-contracts)
15. [Implementation Plan](#implementation-plan)
16. [Acceptance Criteria](#acceptance-criteria)

---

## Conceptual Modes

NodeReducer supports two conceptual modes. **v1.0 implements FSM mode only.**

### Mode 1: FSM-Driven State Transitions (v1.0 Implemented)

The primary v1.0 use case. NodeReducer acts as a **finite state machine engine**:

```text
delta(state, trigger, context) -> (new_state, intents[])
```

- **Input**: Current state + trigger event + context data
- **Output**: New state + list of Intents for side effects
- **Data Flow**: `metadata["trigger"]` drives FSM, `context` provides guard data
- **Reduction Type**: Use `EnumReductionType.TRANSFORM` (other values reserved)

### Mode 2: Data Reduction Pipelines (Reserved - Not in v1.0)

Future use case for collection-oriented data processing:

```text
reduce(data[], reduction_type) -> aggregated_result
```

- **Input**: Collection of items + reduction operation
- **Output**: Aggregated/transformed result
- **Reduction Types**: `FOLD`, `AGGREGATE`, `DEDUPLICATE`, `MERGE`, etc.
- **Status**: Fields present in models but **execution not implemented in v1.0**

### v1.0 Enforcement

When using FSM mode in v1.0:

- `reduction_type` **SHOULD** be `EnumReductionType.TRANSFORM`
  - Other values are accepted but emit a warning log Intent at process time
  - Future versions may assign specific semantics to other reduction types
- `streaming_mode`, `batch_size`, `window_size_ms` are **ignored** (reserved for data-reduction mode)

### Context Construction

The FSM executor builds `context` from `ModelReducerInput` as follows:

```python
def _build_fsm_context(input_data: ModelReducerInput) -> dict[str, Any]:
    """
    Build FSM context from reducer input.

    Context keys:
        - All keys from input_data.metadata (shallow copy)
        - "data": The input data list (for condition evaluation)
        - "operation_id": The operation ID as string
    """
    context = dict(input_data.metadata)  # Shallow copy
    context["data"] = input_data.data
    context["operation_id"] = str(input_data.operation_id)
    return context
```

**Reserved Context Keys**:

| Key | Source | Type |
|-----|--------|------|
| `data` | `input_data.data` | `list[T_Input]` |
| `operation_id` | `input_data.operation_id` | `str` |
| `trigger` | `input_data.metadata["trigger"]` | `str` (required for FSM) |

Reserved keys (`data`, `operation_id`) in metadata MUST NOT override system-assigned context keys. If conflict occurs, system keys take precedence.

**Trigger Extraction**:

The FSM trigger is extracted from `input_data.metadata["trigger"]`. If not present, defaults to `"process"`.

```python
trigger = input_data.metadata.get("trigger", "process")
```

### Non-TRANSFORM Warning

When `reduction_type != EnumReductionType.TRANSFORM` in FSM mode, the executor emits a warning Intent:

```python
ModelIntent(
    intent_type="log_event",
    target="logging_service",
    payload={
        "level": "warning",
        "message": "Non-TRANSFORM reduction_type used in FSM mode",
        "reduction_type": str(input_data.reduction_type),
        "fsm_name": fsm.state_machine_name,
        "note": "Behavior reserved for future versions",
    },
)
```

---

## Global Normative Rules (v1.0.5)

These rules override all other sections when there is ambiguity or contradiction.

### Single Source of Behavior

The v1.0.5 normative behavior is defined **only** by:
- The Error Model section
- The Expression Grammar and Operators section
- The FSM Transition Selection and Wildcards section
- The FSM Metadata Contract section
- The Intent Payload section

Any contradictions elsewhere (including docstrings, diagrams, or prose) are **non-normative** and MUST be interpreted to match these sections.

### Reserved Fields Global Rule

Any field globally marked as reserved for v1.1 or later:
- MUST be parsed
- MUST be validated structurally (types, ranges)
- MUST NOT alter runtime behavior in v1.0 even if set

If an implementation executes reserved behavior in v1.0, it is **non-conforming**.

### NodeReducer Is A Stateful Facade

- NodeReducer is a **stateful facade** around the pure FSM executor
- The FSM executor (`execute_transition`) is the canonical behavior
- Any optimizations inside NodeReducer MUST NOT change the externally observed semantics defined for `execute_transition` plus the error model and metadata contract

### Single-Entity Constraint (v1.0.4 Normative)

v1.0 `NodeReducer` MAY only be used for a **single FSM instance** (single entity).

Multi-entity reducers (e.g., managing orders for multiple customers):
- MUST NOT rely on `NodeReducer._fsm_state`
- MUST operate using pure executors with external state persistence (Pattern C)
- MUST manage entity-keyed state externally

**Rationale**: `NodeReducer._fsm_state` is a single scalar value, not a map. Attempting to use one `NodeReducer` instance for multiple entities will cause state corruption.

### Terminal State Behavior (v1.0.4 Normative)

When a state is marked as terminal (`is_terminal: true`):
- Transitions **from** terminal states MUST raise `ModelOnexError` with code `VALIDATION_ERROR`
- Terminal states represent completed workflows that cannot be re-entered
- Contract validation MUST detect and raise `ModelOnexError` if transitions are defined from terminal states

**Contract-Time vs Runtime**:
- Contract loader MUST reject contracts with outgoing transitions from terminal states
- Runtime executor MUST raise `ModelOnexError` if somehow reached (defense in depth)

### Trigger Canonicalization (v1.0.4 Normative)

Trigger matching MUST be:
- **Strict string equality**: `trigger == transition.trigger`
- **Case-sensitive**: `"Submit"` ≠ `"submit"`
- **No trimming**: Leading/trailing whitespace is significant
- **No normalization**: No Unicode normalization, lowercasing, or transformation

Implementations MUST NOT apply any canonicalization to trigger values.

**Trigger Defaulting Rule**:

The default trigger behavior (`input_data.metadata.get("trigger", "process")`) is a **convenience default**:
- If `metadata["trigger"]` is absent, the trigger DEFAULTS to `"process"`
- Contracts that rely on this behavior MUST define transitions with `trigger: "process"`
- This default is **stable and reserved** - implementations MUST NOT change it

**Trigger Character Set (Recommended)**:

Triggers SHOULD conform to: `[a-zA-Z0-9_.-]+`
- Alphanumeric characters, underscores, dots, hyphens
- No whitespace (discouraged though technically allowed)
- Contract validation MAY warn on triggers outside this character set

### YAML Order Preservation (v1.0.4 Normative)

Contract loading MUST preserve declaration order exactly as written in YAML:
- Transition order in `transitions` list determines tiebreaker precedence
- State order in `states` list is preserved
- Condition order in `conditions` list determines evaluation order

Implementations MUST use order-preserving parsers (Python 3.7+ dicts preserve insertion order).

### History Mutation Semantics (v1.0.5 Normative)

**Boundary Clarification**: FSM executor and NodeReducer have different rules for history:

**FSM Executor** (pure):
- MUST NOT modify `snapshot.history` in any way
- MUST NOT append states to history
- History is passed through unchanged in returned result
- This is a **hard purity requirement**

**NodeReducer** (impure):
- MAY update history outside the executor scope
- If updating, MUST create a new list (never mutate in place)
- MUST document any history policy it implements
- History updates occur **after** executor returns, not during

If implementations choose to maintain history:
- They MUST create a new list (never mutate in place)
- They MUST document their history policy
- Consumers MUST NOT rely on any specific history behavior

**History Opacity Rule**:

History MUST be treated as **opaque**:
- No consumer MAY rely on: length, ordering, content, or format
- History MAY be truncated, deduplicated, or reformatted across versions
- Any logic that depends on history structure is **non-conforming**
- History exists for debugging/auditing only, not for correctness
- Examples showing ordered history are **illustrative only** - do not interpret as semantic ordering (v1.0.5)

### Concurrency Model (v1.0.4 Disclaimer)

v1.0 provides **no concurrency guarantees**:
- No locking semantics defined
- No optimistic concurrency control
- No distributed coordination

External state stores (Pattern C) MUST define their own consistency/locking strategy. Two concurrent transitions for the same entity may race without any conflict detection from the spec.

### FSMTransitionResult.metadata Contract (v1.0.5 Normative)

The `ModelFSMTransitionResult.metadata` dict has the following requirements:

**Important Distinction**: `ModelFSMTransitionResult.metadata` (internal executor result) is distinct from `ModelReducerOutput.metadata` (external API). The 7-key requirement applies to `ModelReducerOutput.metadata` (see FSM Metadata Contract section). `ModelFSMTransitionResult.metadata` has relaxed requirements as follows:

**On Success** (`success=True`):
- `metadata` MAY contain only failure-related keys set to `None`
- No additional keys are required at the executor level

**On Failure** (`success=False`):
- `failure_reason` MUST be present (one of: `"conditions_not_met"`, `"condition_evaluation_error"`)
- `failed_conditions` MUST be present when `failure_reason="conditions_not_met"` (list of condition names)
- `failed_conditions` MUST be `None` when `failure_reason="condition_evaluation_error"` (v1.0.5)
- `error` SHOULD be present with a human-readable message

**Error Field Canonical Location**:

The `error` field appears in both `ModelFSMTransitionResult.error` and `metadata["error"]`. Normative rule:
- `result.error` is the **canonical location**
- `metadata["error"]` MUST equal `result.error` when both are present
- Consumers SHOULD prefer `result.error`

### Reserved System Context Keys (v1.0.4 Normative)

When building the FSM execution context, the executor injects system keys:
- `"data"`: The input data payload
- `"operation_id"`: The operation identifier as string

**Normative Rules**:
- These keys are **system-reserved** and MUST NOT be overwritten by user metadata
- Condition expressions MAY reference these keys
- Contract validation SHOULD warn if user metadata contains these keys
- User-defined context keys MUST NOT conflict with reserved keys

**Reserved Key List** (v1.0.4):
- `data`
- `operation_id`
- `_fsm_*` (any key starting with `_fsm_` is reserved for future use)

### NodeReducer State Initialization (v1.0.4 Normative)

On `NodeReducer` initialization:
- `_fsm_state` MUST be initialized to `contract.initial_state`
- Implementations MUST NOT derive initial state from snapshot
- The initial state MUST be a valid state declared in the contract

```python
def __init__(self, container: ModelONEXContainer):
    super().__init__(container)
    self._fsm_state = self._fsm_contract.initial_state  # MUST match contract
```

### Context Defensive Copy Rule (v1.0.5 Normative)

The FSM executor receives a mutable `context` dict. To preserve purity:
- FSM executor SHOULD create a shallow copy of `snapshot.context` before use
- Executor MUST NOT mutate the original context
- If context is passed to condition evaluators or action builders, defensive copying is RECOMMENDED

**Deep Copy for Nested Mutables (v1.0.5 Clarification)**:

When context contains nested mutable objects (lists, dicts), shallow copy is insufficient:
- Shallow copy protects only top-level keys; nested objects remain shared references
- For contexts with nested mutables, implementations SHOULD use `copy.deepcopy()`
- Performance-sensitive implementations MAY use shallow copy if they guarantee no nested mutation
- Condition evaluators and action builders MUST treat context as **readonly** regardless of copy depth

### Optional Condition Behavior (v1.0.5 Normative)

For conditions with `required: false`:
- If condition evaluates to `False`: transition MAY still proceed (condition is advisory)
- If condition produces evaluation error: treat as `False` and continue (no failure)
- Optional conditions MUST NOT cause transition failure
- Optional condition errors MUST NOT produce `failure_reason` classification - they are silently treated as `False` (v1.0.5)

For conditions with `required: true` (default):
- If condition evaluates to `False`: transition fails with `conditions_not_met`
- If condition produces error: transition fails with `condition_evaluation_error`

### Context Construction Responsibility (v1.0.5 Normative)

Context construction is the **NodeReducer's responsibility**, not the FSM executor's:
- NodeReducer MUST build the context dict before calling the executor
- FSM executor MUST treat context as **readonly** - no mutation, no key injection
- Executor MUST NOT derive or inject keys into context
- This preserves executor purity: context is an explicit input parameter

```python
    # NodeReducer responsibility (impure)
    context = self._build_fsm_context(input_data)

    # FSM executor (pure) - receives readonly context
    result = execute_transition(fsm, snapshot, trigger, context)
```

### Terminal State Check Location (v1.0.5 Normative)

Terminal state checking MUST occur in the FSM executor:
- Executor MUST check `snapshot.current_state` against terminal states **before** evaluating transitions
- If current state is terminal, executor MUST raise `ModelOnexError` with `VALIDATION_ERROR`
- NodeReducer MAY pre-check as defense-in-depth but MUST NOT rely on it

### Transition Name on Condition Failure (v1.0.5 Normative)

When a transition is selected but fails due to conditions:
- `fsm_transition_name` MUST be the selected transition's name
- `fsm_transition_name` MUST NOT be `None` when a transition was selected
- `fsm_transition_name` is `None` ONLY when no matching transition exists (which raises `ModelOnexError`)

This allows consumers to know which transition was attempted even when conditions blocked it.

### Action Phase Ordering (v1.0.5 Normative)

Action execution follows strict phase ordering regardless of `execution_order` values:
1. **Exit actions** MUST complete before transition actions begin
2. **Transition actions** MUST complete before entry actions begin
3. **Entry actions** execute last

The `execution_order` field controls ordering **within** a phase only, not across phases.

### Intent Emission Ordering (v1.0.5 Normative)

Intents MUST be emitted in deterministic order:
1. Exit action intents (in action execution order)
2. Transition action intents (in action execution order)
3. Entry action intents (in action execution order)
4. Persistence intent (if `persistence_enabled` and `success=True`)

NodeReducer MUST NOT reorder intents. Consumers MAY rely on this ordering.

### Self-Loop Transition Behavior (v1.0.5 Normative)

A self-loop is a transition where `from_state == to_state`:
- Self-loops with `success=True` MUST emit persistence intent (if enabled)
- `fsm_transition_success=True` indicates the transition executed, regardless of state change
- Self-loops are valid and MUST NOT be treated as no-ops
- Entry/exit actions MUST still execute for self-loops (exit first, then entry)

### Internal State Divergence Protection (v1.0.5 Normative)

NodeReducer MUST detect internal state divergence:
- Before calling executor, NodeReducer SHOULD verify `_fsm_state` matches expected state
- If `_fsm_state` differs from the state passed to executor, this indicates corruption
- Implementations SHOULD raise `ModelOnexError` on divergence detection

### Snapshot History Initialization (v1.0.5 Normative)

`snapshot.history` MUST always be a list:
- Implementations MUST NOT pass `None` for history
- If history is not tracked, pass an empty list `[]`
- Executor MUST NOT fail on empty history

### Reserved Context Key Warning (v1.0.5 Normative)

When user metadata contains reserved keys (`data`, `operation_id`, `_fsm_*`):
- System keys take precedence (user values are overwritten)
- Reducer MUST emit a warning Intent:

```python
    ModelIntent(
        intent_type="log_event",
        target="logging_service",
        payload={
            "level": "warning",
            "message": "Reserved context key overwritten",
            "key": conflicting_key,
            "user_value": user_value,
            "system_value": system_value,
        },
    )
```

### Duplicate Structural Transition Validation (v1.0.5 Normative)

Contract validation MUST reject duplicate structural transitions:
- Two transitions with identical `(from_state, trigger, priority)` tuple MUST raise `VALIDATION_ERROR`
- This is distinct from duplicate `transition_name` (already forbidden)
- Rationale: Identical tuples create ambiguous selection that definition order cannot reliably resolve

### Contract Validation Rules (v1.0.5 Normative)

Contract validation MUST detect and handle:

| Condition | Behavior |
|-----------|----------|
| Transition from terminal state | MUST raise `ModelOnexError` |
| Duplicate transition name | MUST raise `ModelOnexError` |
| Duplicate structural transition (same from_state, trigger, priority) | MUST raise `ModelOnexError` (v1.0.5) |
| Invalid target state | MUST raise `ModelOnexError` |
| Invalid from_state (not in states, not wildcard) | MUST raise `ModelOnexError` |
| Reserved rollback/recovery fields set | SHOULD emit warning Intent |
| Undefined `is_terminal` outgoing transitions | MUST raise `ModelOnexError` |
| Duplicate action names in same action list | Allowed (executed twice) |
| Operations defined in contract | SHOULD warn (not implemented in v1.0) |
| Reserved field with invalid type/range | MUST raise `ModelOnexError` (v1.0.5) |
| initial_state not in declared states | MUST raise `ModelOnexError` |

### Version Mismatch Handling (v1.0.4 Normative)

When `state_machine_version` in contract differs from persisted state:
- v1.0 does NOT define migration semantics
- Implementations SHOULD reject version mismatches or require explicit migration
- Contract version changes MAY invalidate persisted state

### Action Ordering Within Lists (v1.0.4 Normative)

When multiple actions exist in `entry_actions`, `exit_actions`, or `transition.actions`:
- Actions MUST be executed in **declaration order** (YAML list order)
- If `execution_order` field is present on actions, sort by `execution_order` ascending
- If two actions have same `execution_order`, **declaration order** is the tiebreaker

### Intent Construction Error Handling (v1.0.4 Normative)

If action intent construction fails (e.g., invalid action_config schema):
- Executor MUST catch the error
- Executor MUST emit a failure Intent with error details
- The transition itself MAY still succeed (action failures are non-blocking in v1.0)
- Alternatively, implementations MAY raise `ModelOnexError` for malformed action configs

### Glossary

| Term | Definition |
|------|------------|
| **FSM Executor** | Pure functions (`execute_transition`, etc.) that perform stateless FSM logic |
| **NodeReducer** | Stateful facade class that wraps FSM executor and maintains internal state |
| **Effect Node** | Node type responsible for executing side effects from Intents |
| **Intent** | Declaration of a side effect to be executed by an Effect node |
| **Snapshot** | Immutable representation of FSM state at a point in time (`ModelFSMStateSnapshot`) |
| **Terminal State** | A state marked `is_terminal: true` from which no transitions are allowed |
| **Entity** | A single FSM instance; multi-entity scenarios require external state management |

---

## Design Principles

These principles apply to v1.0 and all future versions:

1. **Pure FSM Executor**: The `execute_transition()` function produces `(new_snapshot, intents[])` without executing side effects
2. **YAML-Driven**: State machines defined declaratively in contracts - zero custom Python code required
3. **Intent Emission**: Side effects declared as Intents for Effect nodes to execute
4. **Typed Boundaries**: All public surfaces use Pydantic models
5. **Deterministic**: Same snapshot + trigger + context always produces same new snapshot
6. **Entry/Exit Actions**: States can define actions triggered on entry/exit (emitted as Intents)

### Thread Safety and State Management (v1.0.4 Normative)

This section defines the **hard line** on thread safety. The previous language was too vague.

#### What IS Thread-Safe (by contract)

The following are **thread-safe by contract**:

1. **FSM Executor Functions**: `execute_transition` and any other pure FSM helper functions.

2. **Immutable Models**:
   - `ModelReducerInput`
   - `ModelReducerOutput`
   - `ModelFSMStateSnapshot`
   - `ModelFSMTransitionResult`
   - `ModelReducerFsmMetadata`

**Caveat**: Nested containers (`dict`, `list`) are still structurally mutable, so executors MUST NOT mutate them in-place.

#### What Is NOT Thread-Safe

`NodeReducer` instances are **NOT thread-safe**:

- They MUST NOT be shared across threads or async tasks without explicit synchronization.
- The spec does not require or guarantee any internal locking.

**Normative Rule**:

```text
v1.0 NodeReducer instances MUST be treated as single-thread affinity objects.
```

If an implementation chooses to share an instance across threads, it MUST provide its own locking. That is an implementation detail; the protocol does not require or rely on it.

**TODO(v1.1)**: Add thread-local FSM state or explicit state passing for thread-safe concurrent execution.

---

## Purity Boundary (v1.0.4 Normative)

This section defines the **exact and non-negotiable** boundary where purity is guaranteed. Implementations that diverge from these rules are non-conforming.

### What IS Pure

The **FSM executor functions** are pure and MUST remain pure:

```python
def execute_transition(
    fsm: ModelFSMSubcontract,
    snapshot: ModelFSMStateSnapshot,
    trigger: str,
    context: dict[str, Any],
) -> ModelFSMTransitionResult:
    """
    Pure function: same inputs always produce same outputs.
    No side effects. No shared state. Thread-safe.
    """
```

Pure functions:
- Take all state as explicit parameters
- Produce results without side effects
- Do not touch any shared/global state
- Same inputs → same outputs, deterministically

This is the **only place** where the "pure reducer" story is allowed to live.

### What Is NOT Pure

`NodeReducer` is **not pure** and MUST NEVER be described as such:

```python
class NodeReducer:
    """
    NOT PURE: Maintains internal mutable state.
    The effective signature is:

        process(self, input) -> output  # self contains hidden state
    """
    _fsm_state: str  # Internal mutable state
```

**Normative Rule**:
- Implementations MUST treat `NodeReducer` as a **stateful façade over a pure FSM core**.
- No code, tests, or documentation may assume `NodeReducer.process` is pure.

### Deriving Pure Semantics from Impure API

The conceptual pure reducer:

```text
delta(state, trigger, context) -> (new_state, intents)
```

Is derived from the concrete API as follows:

| Conceptual | Concrete Source |
|------------|-----------------|
| `state` (input) | `self._fsm_state` before call |
| `trigger` | `input.metadata.get("trigger", "process")` |
| `context` | `_build_fsm_context(input)` |
| `new_state` (output) | `output.result` |
| `intents` (output) | `output.intents` |

### State Snapshot and Mutation Rules

**Snapshot Reconstruction (2.1)**:

For every transition attempt, the FSM executor:
- MUST treat `ModelFSMStateSnapshot` as effectively immutable
- MUST create a **new** snapshot instance when state changes
- MUST NOT mutate `context` or `history` in-place
- MUST NOT modify `snapshot.history` in place; any history updates MUST occur by creating a new list and constructing a new snapshot instance

**History Semantics (v1.0.4)**:

v1.0 does not define any semantics for `snapshot.history` beyond storing literal state values. Reducers, orchestrators, or tooling MUST NOT rely on history ordering, meaning, or presence. History is purely informational and MAY be empty.

**Internal State Mutation in NodeReducer (2.2)**:

`NodeReducer` is allowed to maintain an internal FSM state cell (`_fsm_state`), but:
- On successful transition: it MAY update its internal state to the new state
- On failed transition with `success=False`: it MUST NOT update internal state
- On hard errors where `ModelOnexError` is thrown: internal state MUST remain unchanged

This guarantees that "no transition performed" really means "state didn't move".

### Recommended Usage Patterns

Treat the pure FSM executor and NodeReducer as **two different tools**.

**Pattern A: Pure Functions (Testing / Deterministic Pipelines)**

```python
from omnibase_core.utils.util_fsm_executor import execute_transition

# Explicitly pass state - fully pure
snapshot = ModelFSMStateSnapshot(current_state="pending", context={})
result = execute_transition(fsm_contract, snapshot, "submit", context)
new_snapshot = ModelFSMStateSnapshot(
    current_state=result.new_state,
    context=result.metadata,
)
```

**Pattern B: Instance per Request (Simple Services)**

```python
# Create fresh instance per request - no shared state concerns
async def handle_request(request):
    reducer = NodeReducer(container)  # Fresh instance
    return await reducer.process(input_data)
```

**Pattern C: External State Store (Distributed Systems) - DEFAULT MENTAL MODEL**

```python
# State stored externally, reducer is stateless adapter
async def handle_request(request, state_store):
    current_state = await state_store.get_state(entity_id)
    snapshot = ModelFSMStateSnapshot(current_state=current_state, context={})
    result = execute_transition(fsm, snapshot, trigger, context)
    await state_store.set_state(entity_id, result.new_state)
    return result
```

**Going forward, unless explicitly stated otherwise, Pattern C is the default mental model.**

---

## v1.0 Scope

### What's IN v1.0

| Feature | Description |
|---------|-------------|
| **FSM State Transitions** | Declarative state machine with named transitions |
| **Entry/Exit Actions** | Actions executed on state entry/exit (emitted as Intents) |
| **Transition Actions** | Actions executed during transitions |
| **Conditional Transitions** | Expression-based conditions for transition guards |
| **Intent Emission** | Side effects declared as Intents |
| **State Persistence** | Persistence intents emitted when enabled |
| **Wildcard Transitions** | Global error handlers with `from_state: "*"` |
| **Terminal State Detection** | Identify when FSM has completed |
| **State History Tracking** | Track sequence of state transitions |
| **Transition Validation** | Contract validation at load time |

### What's NOT in v1.0

| Feature | Deferred To | Rationale |
|---------|-------------|-----------|
| **Parallel Transitions** | v1.1 | Merge semantics need careful design |
| **Complex Expressions** | v1.1 | Arithmetic and functions require expression language |
| **Distributed State** | v1.2 | Requires distributed coordination primitives |
| **Hierarchical States** | v1.2 | Parent-child state relationships add complexity |
| **State Timeouts** | v1.1 | Automatic transitions on timeout |
| **Transition Retries** | v1.1 | Fields defined but execution deferred |
| **Rollback Execution** | v1.2 | Rollback fields defined but execution deferred |
| **Custom Condition Evaluators** | v1.2 | Pluggable condition evaluation |
| **Real-time State Sync** | v1.3 | Multi-instance state synchronization |

### Reserved Fields (v1.0)

The following fields are **defined in models for forward-compatibility** but are **ignored by the v1.0 executor**. Do not rely on their behavior until the specified version.

#### ModelFSMSubcontract Reserved Fields

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `rollback_enabled` | `bool` | `True` | v1.2 |
| `recovery_enabled` | `bool` | `True` | v1.2 |
| `concurrent_transitions_allowed` | `bool` | `False` | v1.1 |
| `max_checkpoints` | `int` | `10` | v1.1 |
| `conflict_resolution_strategy` | `str` | `"priority_based"` | v1.1 |

#### ModelFSMStateDefinition Reserved Fields

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `timeout_ms` | `int \| None` | `None` | v1.1 |

#### ModelFSMStateTransition Reserved Fields

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `retry_enabled` | `bool` | `False` | v1.1 |
| `max_retries` | `int` | `0` | v1.1 |
| `retry_delay_ms` | `int` | `1000` | v1.1 |
| `rollback_transitions` | `list[str]` | `[]` | v1.2 |

#### ModelFSMTransitionCondition Reserved Fields

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `retry_count` | `int` | `0` | v1.1 |
| `timeout_ms` | `int \| None` | `None` | v1.1 |

#### ModelReducerInput Reserved Fields (Data Reduction Mode)

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `streaming_mode` | `EnumStreamingMode` | `BATCH` | v1.2+ |
| `batch_size` | `int` | `1000` | v1.2+ |
| `window_size_ms` | `int` | `5000` | v1.2+ |

**Implementation Note**: These fields are present to allow contracts to be written with future capabilities in mind. The v1.0 executor will accept contracts containing these fields but will not execute their associated logic.

---

## Core Models

### ModelReducerInput

```python
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)


class ModelReducerInput[T_Input](BaseModel):
    """
    Input model for NodeReducer operations.

    Strongly typed input wrapper for data reduction operations with
    comprehensive configuration for streaming modes, conflict resolution,
    and batch processing.

    Type Parameters:
        T_Input: The type of elements in the data list.

    Thread Safety:
        Immutable (frozen=True) after creation - thread-safe for
        concurrent read access.

    v1.0 FSM Mode Behavior:
        In v1.0, for FSM mode:
        - streaming_mode, batch_size, and window_size_ms are RESERVED
        - They MUST be accepted and parsed but MUST NOT affect runtime behavior
        - The executor MUST behave as if streaming_mode is always BATCH
        - reduction_type SHOULD be TRANSFORM; other values emit a warning Intent
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    data: list[T_Input]
    reduction_type: EnumReductionType
    operation_id: UUID = Field(default_factory=uuid4)
    conflict_resolution: EnumConflictResolution = EnumConflictResolution.LAST_WINS
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batch_size: int = Field(default=1000, gt=0, le=10000)
    window_size_ms: int = Field(default=5000, ge=1000, le=60000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
```

### ModelReducerOutput

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.reducer.model_intent import ModelIntent


class ModelReducerOutput[T_Output](BaseModel):
    """
    Output model for NodeReducer operations.

    Strongly typed output wrapper with reduction statistics,
    conflict resolution metadata, and Intent emission list.

    Pure FSM Pattern:
        result: The new state after reduction
        intents: Side effects to be executed by Effect node

    Thread Safety:
        Immutable (frozen=True) after creation.

    v1.0.4 Note:
        metadata is dict[str, Any] to support structured FSM metadata
        (bool, list[str], etc.). See ModelReducerFsmMetadata for the
        typed alternative when using FSM mode.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    result: T_Output
    operation_id: UUID
    reduction_type: EnumReductionType
    processing_time_ms: float
    items_processed: int
    conflicts_resolved: int = 0
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batches_processed: int = 1

    # Intent emission for pure FSM pattern
    intents: list[ModelIntent] = Field(
        default_factory=list,
        description="Side effect intents emitted during reduction (for Effect node)",
    )

    # v1.0.4: Changed from dict[str, str] to dict[str, Any] to support
    # structured FSM metadata (bool, list[str], None, etc.)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    # Optional typed FSM metadata (v1.0.4+)
    # When present, this provides strongly-typed access to FSM state.
    # When absent, use metadata dict with FSM Metadata Contract keys.
    fsm_metadata: "ModelReducerFsmMetadata | None" = Field(
        default=None,
        description="Typed FSM metadata (optional, for FSM mode)",
    )
```

### ModelReducerFsmMetadata (v1.0.4+)

```python
from pydantic import BaseModel, ConfigDict, Field


class ModelReducerFsmMetadata(BaseModel):
    """
    Strongly-typed FSM metadata for ModelReducerOutput.

    This model provides type-safe access to FSM transition results,
    replacing the informal dict[str, Any] metadata convention for FSM mode.

    v1.0.4+: Use this model when type safety is required. The metadata
    dict remains available for backwards compatibility and custom fields.

    Thread Safety:
        Immutable (frozen=True) after creation.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    # Always present fields
    fsm_state: str = Field(
        ...,
        description="FSM state after transition attempt",
    )

    fsm_previous_state: str = Field(
        ...,
        description="FSM state before transition attempt",
    )

    fsm_transition_success: bool = Field(
        ...,
        description="True if state changed, False otherwise",
    )

    fsm_transition_name: str | None = Field(
        ...,
        description="Name of executed transition, or None if none matched",
    )

    # Failure-specific fields (present when fsm_transition_success is False)
    failure_reason: str | None = Field(
        default=None,
        description="One of: 'conditions_not_met', 'condition_evaluation_error'",
    )

    failed_conditions: list[str] | None = Field(
        default=None,
        description="Names of conditions that evaluated to false",
    )

    error: str | None = Field(
        default=None,
        description="Human-readable error message",
    )
```

### ModelIntent

```python
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelIntent(BaseModel):
    """
    Intent declaration for side effects from pure Reducer FSM.

    The Reducer is a pure function: delta(state, action) -> (new_state, intents[])
    Instead of performing side effects directly, it emits Intents describing
    what side effects should occur. The Effect node consumes these Intents
    and executes them.

    Intent Types (Common Examples):
        - "log_event": Emit log message or metrics
        - "emit_event": Publish event to message bus
        - "persist_state": Write state to storage
        - "record_metric": Record metrics to monitoring service
        - "fsm_state_action": Execute FSM entry/exit action
        - "fsm_transition_action": Execute FSM transition action

    Thread Safety:
        Immutable (frozen=True) after creation. Note: shallow immutability -
        mutable nested data (dict/list contents) can still be modified.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
    )

    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this intent",
    )

    intent_type: str = Field(
        ...,
        description="Type of intent (log_event, emit_event, persist_state, etc.)",
        min_length=1,
        max_length=100,
    )

    target: str = Field(
        ...,
        description="Target for the intent execution (service, channel, topic)",
        min_length=1,
        max_length=200,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Intent payload data",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    # Lease fields for single-writer semantics
    lease_id: UUID | None = Field(
        default=None,
        description="Optional lease ID if this intent relates to a leased workflow",
    )

    epoch: int | None = Field(
        default=None,
        description="Optional epoch if this intent relates to versioned state",
        ge=0,
    )
```

### ModelFSMTransitionResult

```python
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from omnibase_core.models.reducer.model_intent import ModelIntent


@dataclass
class ModelFSMTransitionResult:
    """
    Result of FSM transition execution.

    Pure data structure containing transition outcome and intents for side effects.
    Not frozen because timestamp is set at construction time.

    This structure is the canonical wire and execution representation. All implementations
    must match field names and invariant semantics exactly.

    Thread Safety:
        Instances should be treated as effectively immutable after creation.
        Do not modify fields after construction.
    """

    success: bool
    new_state: str
    old_state: str
    transition_name: str | None
    intents: list[ModelIntent]
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
```

### ModelFSMStateSnapshot

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelFSMStateSnapshot:
    """
    Current FSM state snapshot.

    Frozen dataclass preventing field reassignment.

    Warning: context (dict) and history (list) are mutable containers.
    Avoid modifying these after creation to maintain FSM purity.
    FSM executor creates new snapshots rather than mutating existing ones.
    """

    current_state: str
    context: dict[str, Any]
    history: list[str] = field(default_factory=list)
```

---

## Enums

### EnumReductionType

```python
from enum import Enum


class EnumReductionType(Enum):
    """Types of reduction operations supported."""

    FOLD = "fold"              # Reduce collection to single value
    ACCUMULATE = "accumulate"  # Build up result incrementally
    MERGE = "merge"            # Combine multiple datasets
    AGGREGATE = "aggregate"    # Statistical aggregation
    NORMALIZE = "normalize"    # Score normalization and ranking
    DEDUPLICATE = "deduplicate"  # Remove duplicates
    SORT = "sort"              # Sort and rank operations
    FILTER = "filter"          # Filter with conditions
    GROUP = "group"            # Group by criteria
    TRANSFORM = "transform"    # Data transformation
```

### EnumConflictResolution

```python
from enum import Enum


class EnumConflictResolution(Enum):
    """Strategies for resolving conflicts during reduction."""

    FIRST_WINS = "first_wins"  # Keep first encountered value
    LAST_WINS = "last_wins"    # Keep last encountered value
    MERGE = "merge"            # Attempt to merge values
    ERROR = "error"            # Raise error on conflict
    CUSTOM = "custom"          # Use custom resolution function
```

### EnumStreamingMode

```python
from enum import Enum


class EnumStreamingMode(Enum):
    """Streaming processing modes."""

    BATCH = "batch"            # Process all data at once
    INCREMENTAL = "incremental"  # Process data incrementally
    WINDOWED = "windowed"      # Process in time windows
    REAL_TIME = "real_time"    # Process as data arrives
```

---

## FSM Subcontract Models

### ModelFSMSubcontract

```python
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMSubcontract(BaseModel):
    """
    FSM (Finite State Machine) subcontract model.

    Comprehensive state machine subcontract providing state definitions,
    transitions, operations, validation, and recovery mechanisms.
    Designed for composition into node contracts requiring FSM functionality.

    VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

    v1.0 Reserved Fields (parsed but NOT executed):
        - rollback_enabled: Parsed, but rollback logic NOT executed until v1.2
        - recovery_enabled: Parsed, but recovery logic NOT executed until v1.2
        - concurrent_transitions_allowed: Parsed, but NOT enforced until v1.1
        - max_checkpoints: Parsed, but checkpoint limiting NOT executed until v1.1
        - conflict_resolution_strategy: Parsed, but NOT applied until v1.1

    Setting these fields in v1.0 contracts will NOT change runtime behavior.
    They exist for forward-compatibility only.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core FSM identification
    state_machine_name: str = Field(
        default=...,
        description="Unique name for the state machine",
        min_length=1,
    )

    state_machine_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the state machine definition",
    )

    description: str = Field(
        default=...,
        description="Human-readable state machine description",
        min_length=1,
    )

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for FSM instance tracking",
    )

    # State definitions
    states: list["ModelFSMStateDefinition"] = Field(
        default=...,
        description="All available states in the system",
        min_length=1,
    )

    initial_state: str = Field(
        default=...,
        description="Name of the initial state",
        min_length=1,
    )

    terminal_states: list[str] = Field(
        default_factory=list,
        description="Names of terminal/final states",
    )

    error_states: list[str] = Field(
        default_factory=list,
        description="Names of error/failure states",
    )

    # Transition specifications
    transitions: list["ModelFSMStateTransition"] = Field(
        default=...,
        description="All valid state transitions",
        min_length=1,
    )

    # Operation definitions
    operations: list["ModelFSMOperation"] = Field(
        default_factory=list,
        description="Available transition operations",
    )

    # FSM persistence and recovery
    persistence_enabled: bool = Field(
        default=True,
        description="Whether state persistence is enabled",
    )

    checkpoint_interval_ms: int = Field(
        default=30000,
        description="Interval for automatic checkpoints",
        ge=1000,
    )

    max_checkpoints: int = Field(
        default=10,
        description="Maximum number of checkpoints to retain",
        ge=1,
    )

    recovery_enabled: bool = Field(
        default=True,
        description="Whether automatic recovery is enabled",
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Whether rollback operations are enabled",
    )

    # Conflict resolution
    conflict_resolution_strategy: str = Field(
        default="priority_based",
        description="Strategy for resolving transition conflicts",
    )

    concurrent_transitions_allowed: bool = Field(
        default=False,
        description="Whether concurrent transitions are allowed",
    )

    transition_timeout_ms: int = Field(
        default=5000,
        description="Default timeout for transitions",
        ge=1,
    )

    # Validation and monitoring
    strict_validation_enabled: bool = Field(
        default=True,
        description="Whether strict state validation is enabled",
    )

    state_monitoring_enabled: bool = Field(
        default=True,
        description="Whether state monitoring/metrics are enabled",
    )

    event_logging_enabled: bool = Field(
        default=True,
        description="Whether state transition events are logged",
    )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,
        validate_assignment=True,
    )
```

### ModelFSMStateDefinition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMStateDefinition(BaseModel):
    """
    State definition for FSM subcontract.

    Defines state properties, lifecycle management,
    and validation rules for FSM state handling.

    v1.0 Reserved Fields (parsed but NOT executed):
        - timeout_ms: Parsed, but automatic timeout transitions NOT executed until v1.1

    Setting timeout_ms in v1.0 contracts will NOT change runtime behavior.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Model version",
    )

    state_name: str = Field(
        default=...,
        description="Unique name for the state",
        min_length=1,
    )

    state_type: str = Field(
        default=...,
        description="Type classification (operational, snapshot, error, terminal)",
        min_length=1,
    )

    description: str = Field(
        default=...,
        description="Human-readable state description",
        min_length=1,
    )

    is_terminal: bool = Field(
        default=False,
        description="Whether this is a terminal/final state",
    )

    is_recoverable: bool = Field(
        default=True,
        description="Whether recovery is possible from this state",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Maximum time allowed in this state",
        ge=1,
    )

    entry_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state entry",
    )

    exit_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state exit",
    )

    required_data: list[str] = Field(
        default_factory=list,
        description="Required data fields for this state",
    )

    optional_data: list[str] = Field(
        default_factory=list,
        description="Optional data fields for this state",
    )

    validation_rules: list[str] = Field(
        default_factory=list,
        description="Validation rules for state data",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelFSMStateTransition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMStateTransition(BaseModel):
    """
    State transition specification for FSM subcontract.

    Defines complete transition behavior including source/target states,
    triggers, conditions, actions, and rollback mechanisms.

    v1.0 Reserved Fields (parsed but NOT executed):
        - retry_enabled: Parsed, but retry logic NOT executed until v1.1
        - max_retries: Parsed, but retry logic NOT executed until v1.1
        - retry_delay_ms: Parsed, but retry logic NOT executed until v1.1
        - rollback_transitions: Parsed (validated), but rollback NOT executed until v1.2

    Setting these fields in v1.0 contracts will NOT change runtime behavior.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Model version",
    )

    transition_name: str = Field(
        default=...,
        description="Unique name for the transition",
        min_length=1,
    )

    from_state: str = Field(
        default=...,
        description="Source state name (use '*' for wildcard)",
        min_length=1,
    )

    to_state: str = Field(
        default=...,
        description="Target state name",
        min_length=1,
    )

    trigger: str = Field(
        default=...,
        description="Event or condition that triggers transition",
        min_length=1,
    )

    priority: int = Field(
        default=1,
        description="Priority for conflict resolution",
        ge=1,
    )

    conditions: list["ModelFSMTransitionCondition"] = Field(
        default_factory=list,
        description="Conditions that must be met for transition",
    )

    actions: list["ModelFSMTransitionAction"] = Field(
        default_factory=list,
        description="Actions to execute during transition",
    )

    rollback_transitions: list[str] = Field(
        default_factory=list,
        description="Available rollback transition names",
    )

    is_atomic: bool = Field(
        default=True,
        description="Whether transition must complete atomically",
    )

    retry_enabled: bool = Field(
        default=False,
        description="Whether failed transitions can be retried",
    )

    max_retries: int = Field(
        default=0,
        description="Maximum number of retry attempts",
        ge=0,
    )

    retry_delay_ms: int = Field(
        default=1000,
        description="Delay between retry attempts",
        ge=0,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelFSMTransitionCondition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMTransitionCondition(BaseModel):
    """
    Condition specification for FSM state transitions.

    Defines condition types, expressions, and validation logic
    for determining valid state transitions.

    v1.0 Reserved Fields (parsed but NOT executed):
        - retry_count: Parsed, but condition retry NOT executed until v1.1
        - timeout_ms: Parsed, but condition timeout NOT executed until v1.1

    Setting these fields in v1.0 contracts will NOT change runtime behavior.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Subcontract version",
    )

    condition_name: str = Field(
        default=...,
        description="Unique name for the condition",
        min_length=1,
    )

    condition_type: str = Field(
        default=...,
        description="Type of condition (validation, state, processing, custom)",
        min_length=1,
    )

    expression: str = Field(
        default=...,
        description="Condition expression or rule",
        min_length=1,
    )

    required: bool = Field(
        default=True,
        description="Whether this condition is required for transition",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if condition fails",
    )

    retry_count: int = Field(
        default=0,
        description="Number of retries for failed conditions",
        ge=0,
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for condition evaluation",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelFSMTransitionAction

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions,
    including logging, validation, and state modifications.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Subcontract version",
    )

    action_name: str = Field(
        default=...,
        description="Unique name for the action",
        min_length=1,
    )

    action_type: str = Field(
        default=...,
        description="Type of action (log, validate, modify, event, cleanup)",
        min_length=1,
    )

    action_config: list["ModelActionConfigParameter"] = Field(
        default_factory=list,
        description="Strongly-typed configuration parameters for the action",
    )

    execution_order: int = Field(
        default=1,
        description="Order of execution relative to other actions",
        ge=1,
    )

    is_critical: bool = Field(
        default=False,
        description="Whether action failure should abort transition",
    )

    rollback_action: str | None = Field(
        default=None,
        description="Action to execute if rollback is needed",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for action execution",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelFSMOperation

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMOperation(BaseModel):
    """
    FSM operation definition.

    RESERVED FOR v1.1+: This model is defined for forward compatibility
    but operations are not used in v1.0 execution.

    Future versions may use operations for:
    - Complex multi-step transitions
    - Transactional state changes
    - Conditional branching logic
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Model version",
    )

    operation_name: str = Field(
        default=...,
        description="Unique name for the operation",
        min_length=1,
    )

    operation_type: str = Field(
        default=...,
        description="Type of operation",
        min_length=1,
    )

    description: str = Field(
        default="",
        description="Human-readable operation description",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

---

## Contract Validation Invariants

The following invariants are **enforced at contract load time**. If any invariant is violated, the node **MUST NOT start** and MUST raise `ModelOnexError`.

### State Invariants

| Invariant | Description | Error Code |
|-----------|-------------|------------|
| `initial_state ∈ states` | Initial state must be a declared state | `VALIDATION_ERROR` |
| `terminal_states ⊆ states` | All terminal states must be declared states | `VALIDATION_ERROR` |
| `error_states ⊆ states` | All error states must be declared states | `VALIDATION_ERROR` |
| `len(states) >= 1` | At least one state must be defined | `VALIDATION_ERROR` |
| `initial_state != ""` | Initial state must be non-empty | `VALIDATION_ERROR` |

### Transition Invariants

| Invariant | Description | Error Code |
|-----------|-------------|------------|
| `transition.from_state ∈ states ∪ {"*"}` | Source state must exist or be wildcard | `VALIDATION_ERROR` |
| `transition.to_state ∈ states` | Target state must be a declared state | `VALIDATION_ERROR` |
| `transition.transition_name` is unique | No duplicate transition names | `VALIDATION_ERROR` |
| `transition.trigger != ""` | Trigger must be non-empty | `VALIDATION_ERROR` |
| `len(transitions) >= 1` | At least one transition must be defined | `VALIDATION_ERROR` |

### Rollback Invariants (v1.2+, validated but not executed in v1.0)

| Invariant | Description | Error Code |
|-----------|-------------|------------|
| `rollback_transition ∈ transition_names` | Rollback must reference existing transition | `VALIDATION_ERROR` |

### Validation Implementation

```python
def validate_fsm_contract(fsm: ModelFSMSubcontract) -> None:
    """
    Validate FSM contract invariants at load time.

    This function enforces ALL invariants from the State Invariants,
    Transition Invariants, and Rollback Invariants tables.

    Raises:
        ModelOnexError: If any invariant is violated.
    """
    # Structural invariants
    if len(fsm.states) < 1:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="At least one state must be defined",
        )

    if len(fsm.transitions) < 1:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="At least one transition must be defined",
        )

    if not fsm.initial_state or fsm.initial_state == "":
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="initial_state must be non-empty",
        )

    state_names = {s.state_name for s in fsm.states}

    # State membership invariants
    if fsm.initial_state not in state_names:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"initial_state '{fsm.initial_state}' not in declared states",
            context={"declared_states": list(state_names)},
        )

    for terminal in fsm.terminal_states:
        if terminal not in state_names:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"terminal_state '{terminal}' not in declared states",
            )

    for error_state in fsm.error_states:
        if error_state not in state_names:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"error_state '{error_state}' not in declared states",
            )

    # Transition invariants
    transition_names: set[str] = set()
    for t in fsm.transitions:
        # Uniqueness check
        if t.transition_name in transition_names:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Duplicate transition name: '{t.transition_name}'",
            )
        transition_names.add(t.transition_name)

        # Trigger non-empty check
        if not t.trigger or t.trigger == "":
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Transition '{t.transition_name}' has empty trigger",
            )

        # from_state membership (wildcard allowed)
        if t.from_state != "*" and t.from_state not in state_names:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Transition '{t.transition_name}' from_state '{t.from_state}' not in declared states",
            )

        # to_state membership (wildcard NOT allowed)
        if t.to_state not in state_names:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Transition '{t.transition_name}' to_state '{t.to_state}' not in declared states",
            )

    # Rollback invariants (validated but not executed in v1.0)
    for t in fsm.transitions:
        for rollback_name in t.rollback_transitions:
            if rollback_name not in transition_names:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Transition '{t.transition_name}' references unknown rollback '{rollback_name}'",
                )
```

---

## Execution Model

### FSM Execution Flow

v1.0 uses **pure function FSM execution**:

```text
   Input Event
       │
       ▼
┌─────────────────┐
│ Validate State  │──▶ Raise ModelOnexError if invalid
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Find Transition │──▶ Raise ModelOnexError if none found
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Evaluate Guards  │──▶ Return failed result + log Intent
└────────┬────────┘
         │ Conditions Met
         ▼
┌─────────────────┐
│  Exit Actions   │──▶ Emit Intents
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Trans. Actions   │──▶ Emit Intents
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Entry Actions  │──▶ Emit Intents
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Persistence   │──▶ Emit Intent (if enabled)
└────────┬────────┘
         │
         ▼
   FSMTransitionResult
   (new_state, intents[])
```

### Execution Rules

1. **Pure Function**: `execute_transition(fsm, state, trigger, context)` returns result and intents
2. **No Side Effects**: All side effects emitted as Intents
3. **Abort on Invalid State**: Invalid current state raises `ModelOnexError`
4. **Abort on No Transition**: No matching transition raises `ModelOnexError`
5. **Structured Failure on Conditions**: Unmet conditions return `ModelFSMTransitionResult(success=False)` with failure metadata and log Intent
6. **Action Order**: Exit actions -> Transition actions -> Entry actions

### Transition Selection Algorithm

When multiple transitions match the current state and trigger, FSM executors MUST follow this deterministic ordering:

1. Filter transitions by matching trigger
2. Sort by specificity: exact state match > wildcard ("*")
3. Sort by priority (descending)
4. Stable sort by definition order (first defined wins)

Condition evaluation occurs only on the selected transition; v1.0 does not attempt fallback transition resolution.

**No Fallback Rule (Normative)**:

If a chosen transition fails due to condition failure or evaluation error, the executor MUST NOT attempt fallback or alternative transitions. v1.0 prohibits any kind of fallback transition resolution. The failure is final for that invocation.

### Transition Failure Reasons

When a transition fails due to unmet conditions, the `ModelFSMTransitionResult` includes structured failure information.

**Failure Reason Values** (in `metadata["failure_reason"]`):

| Value | Meaning |
|-------|---------|
| `"conditions_not_met"` | One or more guard conditions evaluated to false |
| `"condition_evaluation_error"` | Error occurred during condition evaluation |

**Example Failed Result**:

```python
    # Note: This is ModelFSMTransitionResult (internal executor result).
    # The NodeReducer maps this to ModelReducerOutput which has the full
    # 7-key metadata requirement. See FSM Metadata Contract section.
    ModelFSMTransitionResult(
        success=False,
        new_state="pending",        # Unchanged from old_state
        old_state="pending",
        transition_name="start_payment",  # v1.0.5: MUST be set even on failure
        intents=[
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "warning",
                    "message": "Transition conditions not met",
                    "fsm": "order_processing_fsm",
                    "transition": "start_payment",
                    "failed_conditions": ["has_items", "has_customer"],
                },
            )
        ],
        metadata={
            "failure_reason": "conditions_not_met",
            "failed_conditions": ["has_items", "has_customer"],
            # Note: failed_conditions is list when conditions_not_met,
            # but MUST be None when condition_evaluation_error (v1.0.5)
        },
        error="Conditions not met: has_items, has_customer",
    )
```

### Condition Evaluation

v1.0 uses a simple expression-based condition evaluation:

```yaml
conditions:
  - condition_name: has_data_sources
    condition_type: validation
    expression: "data_sources min_length 1"
    required: true
```

**v1.0 Expression Format**: `field_name operator expected_value`

### Tokenization Rules

Expressions are tokenized by **splitting on whitespace**. v1.0 uses strict 3-token parsing:

```python
def parse_expression(expression: str) -> tuple[str, str, str]:
    """
    Parse condition expression into (field, operator, value).

    Raises:
        ValueError: If expression does not have exactly 3 tokens.
    """
    tokens = expression.split()
    if len(tokens) != 3:
        raise ValueError(
            f"Expression must have exactly 3 tokens: 'field operator value', got {len(tokens)}"
        )
    return tokens[0], tokens[1], tokens[2]
```

**Implications**:

- ✅ `status equals active` → `("status", "equals", "active")`
- ✅ `count greater_than 10` → `("count", "greater_than", "10")`
- ❌ `plan_name equals enterprise plus` → **Error**: 4 tokens
- ❌ `status equals` → **Error**: 2 tokens

**Values with spaces are NOT supported in v1.0**. If you need to match values containing spaces:
- Use a different encoding (e.g., `enterprise_plus`)
- Preprocess context to use space-free keys

For `exists` and `not_exists`, the third token is ignored but must be present:

```yaml
# Correct
expression: "user_id exists _"

# Also correct (any placeholder)
expression: "user_id exists true"
```

**Parser Requirements for exists/not_exists (v1.0.5 Clarification)**:

- Parser MUST allow any placeholder token as the third token for `exists` and `not_exists` operators
- Parser MUST NOT validate the placeholder semantically (any non-empty string is valid)
- The placeholder is structurally required to satisfy the 3-token grammar but is not evaluated
- Recommended placeholders: `_`, `true`, `placeholder`, `ignored`

**Expression Grammar Design Philosophy**:

v1.0 intentionally restricts expression grammar to eliminate ambiguity and reduce implementation surface area. Complex conditions must be encoded as precomputed fields in context.

### Supported Operators

| Operator | Description | Value Type | Example |
|----------|-------------|------------|---------|
| `equals` | String equality (type-coerced) | Any (coerced to str) | `status equals active` |
| `not_equals` | String inequality (type-coerced) | Any (coerced to str) | `status not_equals error` |
| `min_length` | Minimum collection length | Integer | `items min_length 1` |
| `max_length` | Maximum collection length | Integer | `items max_length 100` |
| `greater_than` | Numeric comparison | Numeric | `count greater_than 0` |
| `less_than` | Numeric comparison | Numeric | `count less_than 1000` |
| `exists` | Field exists in context | Ignored | `user_id exists _` |
| `not_exists` | Field does not exist | Ignored | `error_code not_exists _` |

### Type Coercion Behavior

The `equals` and `not_equals` operators perform **string-based comparison** by casting both sides to `str` before evaluation. This is intentional for YAML/JSON config compatibility but is a known limitation.

```text
10 == "10"           -> True  (both become "10")
True == "True"       -> True  (both become "True")
None == "None"       -> True  (both become "None")
3.14 == "3.14"       -> True  (both become "3.14")
3.0 == "3"           -> FALSE (becomes "3.0" vs "3")  # Footgun!
```

### v1.0.4 Normative Requirements for Expression Evaluation

The following requirements are **mandatory** for v1.0 implementations:

**String Comparison Operators**:

1. `equals` and `not_equals` MUST be implemented as string-based comparison only:
   ```python
   str(context_value) == str(expected_value)
   ```

2. Implementations MUST NOT introduce type-aware equality semantics for `equals` or `not_equals` in v1.0. All values are coerced to strings before comparison.

3. Contracts MUST NOT rely on numeric equality using `equals`. Such usage is **undefined behavior** and may produce unexpected results:
   ```yaml
   # UNDEFINED BEHAVIOR - DO NOT USE
   expression: "count equals 10"  # May fail: "10.0" != "10"
   ```

**Numeric Comparison Operators**:

4. `greater_than` and `less_than` MUST be implemented with numeric parsing:
   ```python
   float(context_value) > float(expected_value)
   ```

5. If numeric parsing fails, the condition evaluation MUST return `False` and the transition result MUST include `failure_reason="condition_evaluation_error"`.

### Condition Evaluation Error Classification (v1.0.4)

The following scenarios MUST all result in `failure_reason="condition_evaluation_error"`:

| Scenario | Example | Behavior |
|----------|---------|----------|
| **Wrong token count** | `"status"` (1 token) | Expression parse error |
| **Wrong token count** | `"a equals b c"` (4 tokens) | Expression parse error |
| **Numeric parse failure** | `"count greater_than abc"` | `float("abc")` fails |
| **Missing context key** | `"status equals active"` when `status` not in context | Key lookup fails for non-existence operators |

In all cases:
- The transition MUST yield `ModelFSMTransitionResult` with:
  - `success = False`
  - `failure_reason = "condition_evaluation_error"`
  - `error` set to a human-readable message
  - `failed_conditions` containing the `condition_name`, if available

### Missing Context Key Rule (v1.0.5 Normative)

When a condition expression references a context key that does not exist:

**For `exists` / `not_exists` operators** (v1.0.5 clarification):
- These operators MUST short-circuit **before** missing-key error handling
- `exists` MUST return `False` (key is absent) - no error
- `not_exists` MUST return `True` (key is absent) - no error
- These operators MUST NOT produce `condition_evaluation_error` for missing keys

**For ALL other operators** (`equals`, `not_equals`, `greater_than`, `less_than`, `min_length`, `max_length`):
- Missing context key MUST produce `failure_reason="condition_evaluation_error"`
- This is NOT treated as `conditions_not_met` - it is an evaluation error

**Invalid Expected Value** (v1.0.5):
- If the expected value (third token) is malformed for the operator, this MUST yield `condition_evaluation_error`
- Example: `"count greater_than abc"` - `abc` cannot be parsed as float

**Rationale**: Strict handling prevents silent failures from typos or contract/context mismatches.

### Condition Evaluator Purity Rule (v1.0.5 Normative)

Condition evaluation MUST be pure:
- MUST NOT mutate context
- MUST NOT access external state (database, network, filesystem)
- MUST NOT produce side effects (logging is permitted but MUST NOT affect evaluation result)
- MUST be deterministic: same context + expression → same boolean result

**Logging Restriction** (v1.0.5):
- Logging during condition evaluation is permitted for debugging
- Logging MUST NOT depend on the evaluation result (no conditional logs based on True/False outcome)
- Exception: Error logs for `condition_evaluation_error` are permitted
- Rationale: Result-dependent logging breaks determinism guarantees for replay/testing

Implementations that violate condition evaluator purity are **non-conforming** and break the FSM executor purity guarantee.

**Existence Operators**:

6. `exists` MUST return `True` if and only if the field name is a key in the context dict (regardless of value).

7. `not_exists` MUST return `True` if and only if the field name is NOT a key in the context dict.

**Recommended Patterns**:

| Need | Correct Approach | Avoid |
|------|------------------|-------|
| String equality | `status equals active` | - |
| Numeric comparison | `count greater_than 9` | `count equals 10` |
| Boolean check | `enabled equals true` | Relying on Python bool coercion |
| Null check | `error_code not_exists _` | `error_code equals None` |

**Workarounds for strict typing**:
- Use `greater_than`/`less_than` for numeric comparison
- Preprocess context values before FSM execution
- Encode booleans as strings (`"true"`, `"false"`) in context

### Wildcard Transitions

Wildcard transitions (`from_state: "*"`) match from any state, useful for global error handlers:

```yaml
transitions:
  - transition_name: global_error_handler
    from_state: "*"
    to_state: error
    trigger: fatal_error
```

**Matching Priority**: Exact state match takes precedence over wildcard.

### Wildcard and Priority Resolution – Algorithmic Definition

The spec previously described this verbally. This section makes it algorithmic so nobody "optimizes" it into nonsense.

Given:
- `current_state`
- `trigger`
- A set of transitions `T`

The executor MUST:

```text
1. Filter transitions where t.trigger == trigger
   → candidate_set

2. Partition candidate_set into:
   - exact_matches: t.from_state == current_state
   - wildcards: t.from_state == "*"

3. IF len(exact_matches) >= 1:
   - Ignore all wildcard transitions
   - Among exact_matches, choose the one with:
     a. Highest priority (numeric, descending)
     b. If tie: first as defined in contract (stable sort)

4. ELSE IF len(wildcards) >= 1:
   - Among wildcards, choose the one with:
     a. Highest priority (numeric, descending)
     b. If tie: first as defined in contract (stable sort)

5. ELSE (neither set is non-empty):
   - Raise ModelOnexError with code VALIDATION_ERROR
     ("no matching transition")
```

**This resolves all specificity/priority/order ambiguities. Anything else is a bug.**

**Example Conflict**:

```yaml
transitions:
  # Transition A: exact match, priority 1
  - transition_name: pending_cancel
    from_state: pending
    to_state: cancelled
    trigger: cancel
    priority: 1

  # Transition B: wildcard match, priority 10
  - transition_name: global_cancel
    from_state: "*"
    to_state: force_cancelled
    trigger: cancel
    priority: 10
```

**Resolution**: When in state `pending` with trigger `cancel`:
- Transition A matches (exact state: `pending`)
- Transition B matches (wildcard: `*`)
- **Winner: Transition A** (exact match beats wildcard, regardless of priority)

**Priority Only Matters Within Same Specificity**:

```yaml
transitions:
  # Both are wildcards, priority determines winner
  - transition_name: soft_cancel
    from_state: "*"
    to_state: soft_cancelled
    trigger: cancel
    priority: 1

  - transition_name: hard_cancel
    from_state: "*"
    to_state: hard_cancelled
    trigger: cancel
    priority: 10
```

**Resolution**: For trigger `cancel` from any state:
- Both transitions are wildcards (same specificity)
- **Winner: hard_cancel** (higher priority: 10 > 1)

**Edge Case - Same Priority**:

If two transitions have equal specificity and equal priority, the **first defined in the contract** wins. This is a stable sort property, but relying on definition order is discouraged. Always use explicit priorities to avoid ambiguity.

### State Persistence

When `persistence_enabled: true`, the executor emits a persistence Intent:

```python
ModelIntent(
    intent_type="persist_state",
    target="state_persistence",
    payload={
        "fsm_name": fsm.state_machine_name,
        "state": new_state,
        "previous_state": old_state,
        "operation_id": str(input_data.operation_id),  # REQUIRED (v1.0.5)
        "timestamp": datetime.now(UTC).isoformat(),
        # OPTIONAL: "context": context,
        # OPTIONAL: "correlation_id": correlation_id,
    },
    priority=1,  # High priority
)
```

**Note (v1.0.5)**: The `operation_id` field is REQUIRED in the payload. See [Canonical persist_state Payload](#canonical-persist_state-payload-v104-normative) for the complete schema.

**Persistence Intent Rule (Normative)**:

When `persistence_enabled` is `true`, exactly one `persist_state` Intent MUST be emitted per successful transition. On failed transitions (`success=False`), no persistence Intent MUST be emitted.

**Self-Loop Persistence (v1.0.5 Clarification)**:

Self-loop transitions (same `from_state` and `to_state`) with `success=True` MUST emit a persistence intent when `persistence_enabled` is `true`. The state value does not change, but the transition is still recorded for audit and idempotency purposes.

### Canonical persist_state Payload (v1.0.4 Normative)

**REQUIRED Keys** (MUST always be present):

| Key | Type | Description |
|-----|------|-------------|
| `fsm_name` | `str` | `state_machine_name` from contract |
| `previous_state` | `str` | State before transition |
| `state` | `str` | State after transition |
| `operation_id` | `str` | `input.operation_id` as string |
| `timestamp` | `str` | ISO-8601 timestamp |

**OPTIONAL Keys** (MAY be present):

| Key | Type | Description |
|-----|------|-------------|
| `context` | `dict[str, Any]` | FSM context snapshot |
| `correlation_id` | `str` | Correlation ID if available |
| `entity_id` | `str` | External entity identifier (for multi-entity scenarios) |

**Payload Stability**: REQUIRED keys form a stable contract. Consumers MUST NOT rely on OPTIONAL keys being present.

---

## Intent Pattern

### Pure FSM Philosophy

The NodeReducer follows the pure FSM pattern:

```python
# Pure function signature
def delta(state: S, action: A) -> tuple[S, list[Intent]]:
    # Determine new state (pure logic)
    # Emit intents for side effects
    return (new_state, intents)
```

**Key Principle**: The Reducer never performs side effects directly. It only declares what should happen through Intents.

### Common Intent Types

| Intent Type | Target | Purpose |
|-------------|--------|---------|
| `persist_state` | `state_persistence` | Save FSM state to storage |
| `record_metric` | `metrics_service` | Record transition metrics |
| `log_event` | `logging_service` | Log state transitions |
| `fsm_state_action` | `action_executor` | Execute entry/exit action |
| `fsm_transition_action` | `action_executor` | Execute transition action |
| `emit_event` | Event topic | Publish domain event |

### Intent Flow

```text
┌─────────────┐
│  NodeReducer │  Emits Intents
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Intent[]   │  Pure declarations
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  NodeEffect │  Executes side effects
└─────────────┘
```

### Intent Routing Contract

The boundary between NodeReducer and NodeEffect is defined by the **Intent Routing Contract**:

**NodeReducer Responsibilities** (Producer):
- Emit `ModelIntent` objects describing desired side effects
- Set `intent_type` to identify the category of side effect
- Set `target` to identify the destination service/topic/channel
- Populate `payload` with data needed to execute the side effect
- **Never** execute side effects directly
- **Never** import or reference Effect node implementations

**NodeEffect Responsibilities** (Consumer):
- Subscribe to Intents via `intent_type` and/or `target`
- Execute side effects based on Intent payload
- Handle failures and retries for side effect execution
- Report execution results (success/failure) if needed

**Target Interpretation**:

| Target Pattern | Interpretation | Example |
|----------------|----------------|---------|
| `service_name` | Direct service call | `state_persistence`, `metrics_service` |
| `topic:name` | Event bus topic | `topic:order_events` |
| `channel:name` | Message channel | `channel:notifications` |
| `action_executor` | FSM action handler | Built-in action execution |

**v1.0 Built-in Intent Types**:

```python
# Emitted by FSM executor
"persist_state"          # State persistence service
"log_event"              # Logging service
"record_metric"          # Metrics service
"fsm_state_action"       # Entry/exit action handler
"fsm_transition_action"  # Transition action handler
```

**Custom Intent Types**:

Contracts may define custom intent types for domain-specific side effects:

```yaml
# Example: Order processing FSM emits custom intents
entry_actions:
  - send_order_confirmation  # Results in fsm_state_action intent
  - notify_warehouse         # Results in fsm_state_action intent
```

The Effect node responsible for `action_executor` target interprets these action names and routes to appropriate handlers.

**Action Semantics**:

In v1.0, FSM actions are opaque identifiers. Reducers emit action intents containing the action name. Effect nodes interpret these names using their own action registry.

### Canonical Action Intent Payload (v1.0.4 Normative)

For v1.0, FSM actions MUST be emitted as `ModelIntent` objects with the following canonical payload shape. Effect node implementers MUST support this shape.

**Entry/Exit Actions** (`fsm_state_action`):

```python
ModelIntent(
    intent_type="fsm_state_action",
    target="action_executor",
    payload={
        # REQUIRED keys (v1.0.4 stable contract)
        "fsm_name": str,           # fsm.state_machine_name
        "state": str,              # State name being entered/exited
        "action_name": str,        # Action identifier from entry_actions/exit_actions
        "action_phase": str,       # "entry" or "exit"
        "operation_id": str,       # input.operation_id as string

        # OPTIONAL keys (may be present)
        "previous_state": str | None,  # Previous state (for entry actions)
        "next_state": str | None,      # Next state (for exit actions)
        "correlation_id": str | None,  # FSM correlation ID if available
    },
    priority=1,
)
```

**Transition Actions** (`fsm_transition_action`):

```python
ModelIntent(
    intent_type="fsm_transition_action",
    target="action_executor",
    payload={
        # REQUIRED keys (v1.0.4 stable contract)
        "fsm_name": str,           # fsm.state_machine_name
        "transition_name": str,    # Transition being executed
        "from_state": str,         # Source state
        "to_state": str,           # Target state
        "action_name": str,        # Action identifier from transition.actions
        "operation_id": str,       # input.operation_id as string

        # OPTIONAL keys (may be present)
        "trigger": str | None,     # Trigger that initiated transition
        "correlation_id": str | None,  # FSM correlation ID if available
    },
    priority=1,
)
```

**Payload Stability Guarantee**:

The REQUIRED keys in the above payloads form a **stable contract**. v1.0 implementations:
- MUST include all REQUIRED keys
- MAY include additional keys
- MUST NOT remove or rename REQUIRED keys

Future versions MAY add new OPTIONAL keys but MUST NOT change REQUIRED key semantics.

**Payload Violation Rule (v1.0.4 Normative)**:

For both `fsm_state_action` and `fsm_transition_action`:
- Emission of an Intent missing any REQUIRED key is a **protocol violation**
- Consumers MAY treat such intents as malformed and either drop them or route them to an error handler
- Implementations MUST emit intents strictly conforming to the canonical payload schema

**Correlation ID Propagation (v1.0.5 Clarification)**:

If the FSMSubcontract defines a `correlation_id` (via context or input), action intents MUST include it in the payload:
- The `correlation_id` field is OPTIONAL in the payload schema but MUST be present when available
- This enables end-to-end tracing of FSM operations across Effect nodes
- Effect nodes SHOULD propagate the correlation_id to downstream side effects

**Decoupling Guarantee**:

NodeReducer has **zero knowledge** of:
- How intents are routed to Effect nodes
- Which Effect node handles which intent type
- Whether the side effect succeeds or fails
- What happens after the intent is emitted

This decoupling enables:
- Testing reducers without Effect infrastructure
- Swapping Effect implementations without changing Reducer contracts
- Parallel development of Reducer and Effect nodes

---

## Error Model (v1.0)

v1.0 uses **ModelOnexError** for FSM execution errors.

### v1.0.4 Normative Error Handling Requirements

The following behaviors are **mandatory** for v1.0 implementations:

**MUST Raise `ModelOnexError`**:

1. **Invalid Current State**: If the current FSM state is not a declared state in the contract, the executor MUST raise `ModelOnexError` with code `VALIDATION_ERROR`. This is a configuration/programming error.

2. **No Matching Transition**: If no transition matches the `(current_state, trigger)` pair (including wildcard rules), the executor MUST raise `ModelOnexError` with code `VALIDATION_ERROR`. This is treated as a configuration error, not a runtime business constraint.

**MUST NOT Raise `ModelOnexError`**:

3. **Conditions Not Met**: If at least one transition matches and the chosen transition's conditions are not satisfied, the executor MUST return `ModelFSMTransitionResult(success=False)` with `failure_reason="conditions_not_met"`. It MUST NOT raise `ModelOnexError` in this case.

4. **Condition Evaluation Error**: If condition evaluation encounters an error (e.g., missing field in context), the executor MUST return `ModelFSMTransitionResult(success=False)` with `failure_reason="condition_evaluation_error"`. It MUST NOT raise `ModelOnexError` unless the error is unrecoverable.

**Rationale**: This distinction allows callers to differentiate between:
- **Configuration errors** (exception) - indicates bug in contract or calling code
- **Business constraint failures** (structured result) - expected runtime condition

### Error Examples

```python
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Invalid state error - MUST raise
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message=f"Invalid current state: {current_state}",
    context={"fsm": fsm.state_machine_name, "state": current_state},
)

# No transition found error - MUST raise
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message=f"No transition for trigger '{trigger}' from state '{current_state}'",
    context={
        "fsm": fsm.state_machine_name,
        "state": current_state,
        "trigger": trigger,
    },
)
```

### Error Handling Strategy

| Scenario | Behavior | Result | v1.0.4 Normative |
|----------|----------|--------|------------------|
| Invalid current state | Raise `ModelOnexError` | Exception | **MUST** raise |
| No matching transition | Raise `ModelOnexError` | Exception | **MUST** raise |
| Conditions not met | Return `ModelFSMTransitionResult(success=False)` | `failure_reason: "conditions_not_met"` | **MUST NOT** raise |
| Condition evaluation error | Return `ModelFSMTransitionResult(success=False)` | `failure_reason: "condition_evaluation_error"` | **MUST NOT** raise |
| Action execution fails | Emit failure Intent | Non-blocking | Advisory only |
| Invalid target state | Raise `ModelOnexError` | Exception | **MUST** raise (contract validation should prevent) |

### Distinguishing Failure Types

```python
result = await reducer.process(input_data)

# Use typed metadata if available (v1.0.4+)
if result.fsm_metadata:
    if not result.fsm_metadata.fsm_transition_success:
        if result.fsm_metadata.failure_reason == "conditions_not_met":
            logger.info(f"Blocked by: {result.fsm_metadata.failed_conditions}")
        elif result.fsm_metadata.failure_reason == "condition_evaluation_error":
            logger.error(f"Evaluation failed: {result.fsm_metadata.error}")
else:
    # Fallback to dict metadata
    if not result.metadata.get("fsm_transition_success", True):
        failure_reason = result.metadata.get("failure_reason")

        if failure_reason == "conditions_not_met":
            failed = result.metadata.get("failed_conditions", [])
            logger.info(f"Transition blocked by conditions: {failed}")

        elif failure_reason == "condition_evaluation_error":
            logger.error(f"Condition evaluation failed: {result.metadata.get('error')}")
```

---

## FSM Metadata Contract

This section defines the **required metadata keys** in `ModelReducerOutput.metadata` when using FSM mode. These keys form a stable contract for consumers.

### v1.0.4 Update: Typed Metadata

v1.0.4 introduces `ModelReducerFsmMetadata` as a **typed alternative** to the metadata dict. Implementations SHOULD populate both:
- `fsm_metadata`: Typed model for type-safe access
- `metadata`: Dict for backwards compatibility and custom fields

### Output Metadata Keys

| Key | Type | When Present | Description |
|-----|------|--------------|-------------|
| `fsm_state` | `str` | Always | FSM state after transition attempt |
| `fsm_previous_state` | `str` | Always | FSM state before transition attempt |
| `fsm_transition_success` | `bool` | Always | `True` if state changed, `False` otherwise |
| `fsm_transition_name` | `str \| None` | Always | Name of executed transition, or `None` if none matched |
| `failure_reason` | `str` | On failure | One of: `"conditions_not_met"`, `"condition_evaluation_error"` |
| `failed_conditions` | `list[str]` | When `failure_reason == "conditions_not_met"` | Names of conditions that evaluated to false |
| `error` | `str` | On failure | Human-readable error message |

**v1.0.4 Normative**: ALL keys in the above table MUST be present in the metadata dict on every FSM operation, even if the value is `None`. This guarantees schema stability for consumers. Omission of a key is non-conforming.

**Typed vs Dict Precedence**:

If `fsm_metadata` is present, consumers SHOULD prefer it over the `metadata` dict. Both representations MUST remain logically consistent and MUST NEVER diverge.

**Metadata Evolution Rules**:

For forward compatibility:
- New metadata keys MAY be added in future minor versions
- New keys MUST be optional for consumers
- Existing keys MUST NOT be removed or have their meanings changed
- Implementations MUST ignore unknown metadata keys

### Mapping from ModelFSMTransitionResult to ModelReducerOutput

The NodeReducer maps `ModelFSMTransitionResult` to `ModelReducerOutput` as follows:

```python
def _build_reducer_output(
    self,
    input_data: ModelReducerInput,
    fsm_result: ModelFSMTransitionResult,
    processing_time_ms: float,
) -> ModelReducerOutput:
    # Build typed metadata (v1.0.4+)
    fsm_metadata = ModelReducerFsmMetadata(
        fsm_state=fsm_result.new_state,
        fsm_previous_state=fsm_result.old_state,
        fsm_transition_success=fsm_result.success,
        fsm_transition_name=fsm_result.transition_name,
        failure_reason=fsm_result.metadata.get("failure_reason"),
        failed_conditions=fsm_result.metadata.get("failed_conditions"),
        error=fsm_result.error,
    )

    return ModelReducerOutput(
        result=fsm_result.new_state,
        operation_id=input_data.operation_id,
        reduction_type=input_data.reduction_type,
        processing_time_ms=processing_time_ms,
        items_processed=len(input_data.data),
        intents=fsm_result.intents,
        # Typed metadata (v1.0.4+)
        fsm_metadata=fsm_metadata,
        # Dict metadata (backwards compatibility)
        metadata={
            "fsm_state": fsm_result.new_state,
            "fsm_previous_state": fsm_result.old_state,
            "fsm_transition_success": fsm_result.success,
            "fsm_transition_name": fsm_result.transition_name,
            "failure_reason": fsm_result.metadata.get("failure_reason"),
            "failed_conditions": fsm_result.metadata.get("failed_conditions"),
            "error": fsm_result.error,
        },
    )
```

---

## v1.0 NodeReducer Behavior

### Startup Behavior

When a `NodeReducer` instance starts:

1. **Load Contract**: Read `state_transitions` from node contract
2. **Validate Structure**: Validate `ModelFSMSubcontract` with model validators
3. **Initialize FSM**: Set FSM state to `initial_state`
4. **Fail Fast**: If contract validation fails, node **must not start**

### Runtime Behavior

When `process(ModelReducerInput)` is called:

1. **Extract Trigger**: Get trigger from `input_data.metadata.get("trigger", "process")`
2. **Build Context**: Combine input data with metadata
3. **Execute Transition**: Call `execute_fsm_transition()`
4. **Build Output**: Create `ModelReducerOutput` with FSM result and intents
5. **Return**: Return typed output to caller

### Lifecycle

```text
┌─────────────────┐
│  Contract Load  │──▶ Validates FSM structure
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FSM Initialize │──▶ Sets initial state
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Node Ready    │──▶ Contract frozen, FSM initialized
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   process()     │──▶ Executes transition, returns result with intents
└─────────────────┘
```

### Validation Failure Lifecycle

If `validate_fsm_contract` raises `ModelOnexError` during startup:
- The node MUST fail to start and MUST NOT accept any `process` calls
- Implementations MAY log and surface the error via health checks

**Hot Reload Note**: v1.0 does not define hot-reload semantics for FSM contracts. If an implementation supports contract reload, it MUST re-run full validation before accepting requests with the new contract.

### Error Propagation (v1.0.4 Normative)

`NodeReducer.process` error handling behavior:

- NodeReducer.process MUST propagate `ModelOnexError` raised by contract validation or FSM execution
- NodeReducer.process MUST NOT catch and convert `ModelOnexError` into a successful `ModelReducerOutput`
- Implementations MAY log the error but MUST re-raise

**Caller Responsibility**: Callers MUST treat `ModelOnexError` as a configuration or programming error, not as a normal control flow signal.

### FSM State Mutation Protection

Subclasses MUST NOT modify internal FSM state. FSM state transitions must occur exclusively through `execute_transition`.

### Usage

```python
from omnibase_core.nodes import NodeReducer


class NodeOrderStateMachine(NodeReducer):
    """Order state machine - all logic from contract."""
    pass


# Usage
node = NodeOrderStateMachine(container)

# Execute transition
input_data = ModelReducerInput(
    data=[{"order_id": "12345", "items": [...]}],
    reduction_type=EnumReductionType.TRANSFORM,
    metadata={
        "trigger": "submit_order",
        "customer_id": "cust_001",
    },
)

result = await node.process(input_data)

# Check result
print(f"New state: {result.metadata['fsm_state']}")
print(f"Intents to execute: {len(result.intents)}")

# Process intents via Effect node
for intent in result.intents:
    await effect_node.execute_intent(intent)
```

---

## Example Contracts

### Order Processing State Machine

```yaml
# examples/contracts/reducer/order_processor_fsm.yaml
# NOTE: Fields marked "RESERVED v1.0" are parsed but not executed in v1.0
node_type: REDUCER
node_name: order_processor
node_version: "1.0.0"

state_transitions:
  version:
    major: 1
    minor: 0
    patch: 0
  state_machine_name: order_processing_fsm
  state_machine_version:
    major: 1
    minor: 0
    patch: 0
  description: "Order processing state machine with payment and fulfillment"

  initial_state: pending
  terminal_states:
    - completed
    - cancelled
    - refunded
  error_states:
    - payment_failed
    - fulfillment_failed

  states:
    - version: { major: 1, minor: 0, patch: 0 }
      state_name: pending
      state_type: operational
      description: "Order submitted, awaiting payment"
      entry_actions:
        - create_order_record
        - send_order_confirmation
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: payment_processing
      state_type: operational
      description: "Payment is being processed"
      timeout_ms: 30000  # RESERVED v1.0: parsed but ignored until v1.1
      entry_actions:
        - initiate_payment
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: paid
      state_type: operational
      description: "Payment received, ready for fulfillment"
      entry_actions:
        - record_payment
        - notify_warehouse
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: fulfilling
      state_type: operational
      description: "Order is being fulfilled"
      entry_actions:
        - begin_fulfillment
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: shipped
      state_type: operational
      description: "Order has been shipped"
      entry_actions:
        - send_shipping_notification
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: completed
      state_type: terminal
      description: "Order successfully completed"
      is_terminal: true
      entry_actions:
        - send_delivery_confirmation
        - update_customer_stats

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: cancelled
      state_type: terminal
      description: "Order was cancelled"
      is_terminal: true
      entry_actions:
        - process_cancellation
        - send_cancellation_notification

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: payment_failed
      state_type: error
      description: "Payment processing failed"
      is_recoverable: true
      entry_actions:
        - log_payment_failure
        - send_payment_failure_notification

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: fulfillment_failed
      state_type: error
      description: "Fulfillment failed"
      is_recoverable: true
      entry_actions:
        - log_fulfillment_failure
        - notify_support

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: refunded
      state_type: terminal
      description: "Order was refunded"
      is_terminal: true
      entry_actions:
        - process_refund
        - send_refund_notification

  transitions:
    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: start_payment
      from_state: pending
      to_state: payment_processing
      trigger: process_payment
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_items
          condition_type: validation
          expression: "items min_length 1"
          required: true
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_customer
          condition_type: validation
          expression: "customer_id exists _"
          required: true
      actions:
        - version: { major: 1, minor: 0, patch: 0 }
          action_name: validate_inventory
          action_type: validate
          is_critical: true

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: payment_success
      from_state: payment_processing
      to_state: paid
      trigger: payment_completed
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_transaction_id
          condition_type: validation
          expression: "transaction_id exists _"
          required: true

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: payment_failure
      from_state: payment_processing
      to_state: payment_failed
      trigger: payment_error

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: begin_fulfillment
      from_state: paid
      to_state: fulfilling
      trigger: start_fulfillment

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: ship_order
      from_state: fulfilling
      to_state: shipped
      trigger: order_shipped
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_tracking
          condition_type: validation
          expression: "tracking_number exists _"
          required: true

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: deliver_order
      from_state: shipped
      to_state: completed
      trigger: order_delivered

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: cancel_order
      from_state: pending
      to_state: cancelled
      trigger: cancel
      priority: 2

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: retry_payment
      from_state: payment_failed
      to_state: payment_processing
      trigger: retry_payment

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: refund_order
      from_state: payment_failed
      to_state: refunded
      trigger: refund

    # Wildcard transition for global error handling
    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: global_cancel
      from_state: "*"
      to_state: cancelled
      trigger: force_cancel
      priority: 10

  persistence_enabled: true
  checkpoint_interval_ms: 30000
  max_checkpoints: 10          # RESERVED v1.0: parsed but ignored until v1.1
  recovery_enabled: true       # RESERVED v1.0: parsed but ignored until v1.2
  rollback_enabled: true       # RESERVED v1.0: parsed but ignored until v1.2
  transition_timeout_ms: 5000
  strict_validation_enabled: true
  state_monitoring_enabled: true
  event_logging_enabled: true
```

### Metrics Aggregation FSM

```yaml
# examples/contracts/reducer/metrics_aggregation_fsm.yaml
# NOTE: Fields marked "RESERVED v1.0" are parsed but not executed in v1.0
node_type: REDUCER
node_name: metrics_aggregator
node_version: "1.0.0"

state_transitions:
  version:
    major: 1
    minor: 0
    patch: 0
  state_machine_name: metrics_aggregation_fsm
  state_machine_version:
    major: 1
    minor: 0
    patch: 0
  description: "Metrics collection and aggregation state machine"

  initial_state: idle
  terminal_states:
    - completed
  error_states:
    - error

  states:
    - version: { major: 1, minor: 0, patch: 0 }
      state_name: idle
      state_type: operational
      description: "Waiting for data collection to start"
      entry_actions: []
      exit_actions: []

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: collecting
      state_type: operational
      description: "Collecting metrics from sources"
      entry_actions:
        - start_collection
      exit_actions:
        - finalize_collection

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: aggregating
      state_type: operational
      description: "Aggregating collected metrics"
      entry_actions:
        - begin_aggregation
      exit_actions: []

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: completed
      state_type: terminal
      description: "Aggregation complete"
      is_terminal: true
      entry_actions:
        - emit_aggregation_results

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: error
      state_type: error
      description: "Error during processing"
      is_recoverable: true
      entry_actions:
        - log_error

  transitions:
    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: start_collecting
      from_state: idle
      to_state: collecting
      trigger: collect_metrics
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_data_sources
          condition_type: validation
          expression: "data_sources min_length 1"
          required: true
      actions:
        - version: { major: 1, minor: 0, patch: 0 }
          action_name: initialize_metrics
          action_type: setup

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: begin_aggregate
      from_state: collecting
      to_state: aggregating
      trigger: start_aggregation

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: finish
      from_state: aggregating
      to_state: completed
      trigger: complete

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: handle_error
      from_state: "*"
      to_state: error
      trigger: error_occurred

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: recover
      from_state: error
      to_state: idle
      trigger: reset

  persistence_enabled: true
  transition_timeout_ms: 5000
```

---

## Implementation Plan

### Phase 1: Core Models & Enums (~3 days)

| Task | File | Priority |
|------|------|----------|
| EnumReductionType | `enums/enum_reducer_types.py` | P0 |
| EnumConflictResolution | `enums/enum_reducer_types.py` | P0 |
| EnumStreamingMode | `enums/enum_reducer_types.py` | P0 |
| ModelIntent | `models/reducer/model_intent.py` | P0 |
| ModelReducerInput | `models/reducer/model_reducer_input.py` | P0 |
| ModelReducerOutput | `models/reducer/model_reducer_output.py` | P0 |
| ModelFSMStateSnapshot | `models/fsm/model_fsm_state_snapshot.py` | P0 |
| ModelFSMTransitionResult | `models/fsm/model_fsm_transition_result.py` | P0 |

### Phase 2: FSM Subcontract Models (~3 days)

| Task | File | Priority |
|------|------|----------|
| ModelFSMSubcontract | `models/contracts/subcontracts/model_fsm_subcontract.py` | P0 |
| ModelFSMStateDefinition | `models/contracts/subcontracts/model_fsm_state_definition.py` | P0 |
| ModelFSMStateTransition | `models/contracts/subcontracts/model_fsm_state_transition.py` | P0 |
| ModelFSMTransitionCondition | `models/contracts/subcontracts/model_fsm_transition_condition.py` | P0 |
| ModelFSMTransitionAction | `models/contracts/subcontracts/model_fsm_transition_action.py` | P0 |
| ModelFSMOperation | `models/contracts/subcontracts/model_fsm_operation.py` | P0 |

### Phase 3: Execution & Node (~3 days)

| Task | File | Priority |
|------|------|----------|
| util_fsm_executor.py | `utils/util_fsm_executor.py` | P0 |
| MixinFSMExecution | `mixins/mixin_fsm_execution.py` | P0 |
| NodeReducer | `nodes/node_reducer.py` | P0 |

### Phase 4: Testing (~3 days)

| Task | File | Priority |
|------|------|----------|
| Unit tests for enums | `tests/unit/enums/test_reducer_types.py` | P0 |
| Unit tests for models | `tests/unit/models/reducer/test_*.py` | P0 |
| Unit tests for FSM models | `tests/unit/models/fsm/test_*.py` | P0 |
| Unit tests for executor | `tests/unit/utils/test_fsm_executor.py` | P0 |
| Integration tests | `tests/integration/test_reducer_fsm.py` | P0 |

### Total Estimate

- **Files**: ~20 files
- **Code**: ~1500 lines
- **Tests**: ~800 lines
- **Timeline**: 12 working days

---

## Acceptance Criteria

### Functional Requirements

- [ ] `ModelFSMSubcontract` validates contracts with model validators
- [ ] All FSM state definitions validated (initial, terminal, error states)
- [ ] All transitions validated (from_state, to_state must exist)
- [ ] FSM executes transitions using pure function semantics
- [ ] Entry/exit actions emit Intents (not executed directly)
- [ ] Transition actions emit Intents (not executed directly)
- [ ] Conditions evaluated using expression grammar
- [ ] Wildcard transitions (`from_state: "*"`) supported
- [ ] Persistence Intents emitted when enabled
- [ ] Terminal state detection working

### Type Safety Requirements

- [ ] All FSM models use `ConfigDict(extra="ignore")` for YAML compatibility
- [ ] All result models use `ConfigDict(frozen=True)` for immutability
- [ ] `ModelIntent` uses `ConfigDict(extra="forbid", frozen=True)`
- [ ] `ModelReducerInput`/`Output` are generic `[T_Input]`/`[T_Output]`
- [ ] mypy --strict passes with zero errors

### Testing Requirements

**Core Tests**:
- [ ] Unit tests for each enum
- [ ] Unit tests for each model
- [ ] Unit tests for FSM executor functions
- [ ] Unit tests for condition evaluation
- [ ] Unit test for wildcard transition precedence (exact state > wildcard)
- [ ] Unit test for metadata stability (all fields always present)
- [ ] Integration test with example FSM contract
- [ ] 90%+ code coverage

**v1.0.4 Additional Required Tests**:

Condition Evaluation Error Tests:
- [ ] Wrong token count expressions (1, 2, 4+ tokens) → `condition_evaluation_error`
- [ ] Non-numeric values to `greater_than`/`less_than` → `condition_evaluation_error`
- [ ] Missing context keys with non-existence operators → `condition_evaluation_error`

NodeReducer.process Behavior Tests:
- [ ] Propagates `ModelOnexError` on invalid state (does not wrap)
- [ ] Propagates `ModelOnexError` on no matching transition (does not wrap)
- [ ] Does not mutate internal state on `success=False`
- [ ] Does not mutate internal state on `ModelOnexError`

Metadata Contract Tests:
- [ ] All FSM metadata keys present on every operation (even when `None`)
- [ ] `fsm_metadata` and `metadata` dict are logically consistent
- [ ] Unknown metadata keys are ignored by consumer code

Intent Payload Tests:
- [ ] `fsm_state_action` payloads contain all REQUIRED keys
- [ ] `fsm_transition_action` payloads contain all REQUIRED keys
- [ ] `target` is set correctly on all intents

Transition Selection Tests:
- [ ] Exact state match beats wildcard regardless of priority
- [ ] Priority ordering within same specificity class
- [ ] Definition order as stable tiebreaker
- [ ] No fallback attempted after candidate selection

### Documentation Requirements

- [ ] Example contracts in `examples/contracts/reducer/`
- [ ] API documentation for public functions
- [ ] Migration guide from custom reducer implementations
- [ ] Intent pattern documentation

---

## Implementation Checklist (v1.0.4)

If you want the quick checklist for implementation work, ensure your code does all of the following:

### 1. Stop Pretending NodeReducer Is Pure

- [ ] Docs, comments, and tests clearly mark **only** the FSM executor as pure
- [ ] NodeReducer is documented as a "stateful façade over a pure FSM core"
- [ ] No tests assume `NodeReducer.process` is deterministic without controlling `_fsm_state`

### 2. Enforce "No Mutation" Rules in FSM Executor

- [ ] Return new snapshots, don't mutate old ones
- [ ] Don't mutate nested `dict`/`list` structures in-place
- [ ] On `success=False`, internal state is NOT updated
- [ ] On `ModelOnexError`, internal state is NOT updated

### 3. Treat NodeReducer as Not Thread-Safe

- [ ] No shared global `NodeReducer` instance unless guarded by locks
- [ ] Documentation warns against cross-thread sharing
- [ ] Tests verify single-thread affinity assumption

### 4. Align with the Error Model

- [ ] Throw `ModelOnexError` only on: invalid state, no matching transition, invalid contract
- [ ] Use structured `ModelFSMTransitionResult(success=False)` for condition failures
- [ ] `failure_reason` is set correctly: `"conditions_not_met"` or `"condition_evaluation_error"`

### 5. Enforce Metadata Contract

- [ ] Always populate ALL keys in `metadata` dict (even if `None`):
  - `fsm_state`
  - `fsm_previous_state`
  - `fsm_transition_success`
  - `fsm_transition_name`
  - `failure_reason`
  - `failed_conditions`
  - `error`
- [ ] Optionally populate `fsm_metadata` typed model (v1.0.4+)

### 6. Lock In Expression and Operator Semantics

- [ ] `equals`/`not_equals`: string-based comparison only (`str(lhs) == str(rhs)`)
- [ ] `greater_than`/`less_than`: parse to `float`, fail gracefully if parsing fails
- [ ] `exists`/`not_exists`: key presence check only
- [ ] 3-token rule enforced (error on != 3 tokens)

### 7. Emit Canonical Intent Payloads

- [ ] `fsm_state_action` payloads include all REQUIRED keys
- [ ] `fsm_transition_action` payloads include all REQUIRED keys
- [ ] Intent `target` is set to `"action_executor"`

### 8. Implement Wildcard Resolution Algorithm

- [ ] Exact state match always beats wildcard
- [ ] Priority sorts descending within same specificity
- [ ] Definition order is stable tiebreaker
- [ ] No transition → `ModelOnexError`

**If your implementation does all of the above, you are functionally aligned with v1.0.4 and your behavior will be predictable, debuggable, and safe to build on.**

---

## Final Conformance Checklist (v1.0.4)

A v1.0.4 implementation is considered **conformant** if and only if ALL of the following are true:

### 1. Purity and State

- [ ] FSM executor functions are pure (no shared state, no side effects)
- [ ] NodeReducer is documented and treated as stateful and not thread-safe
- [ ] Snapshots are never mutated in place; new snapshots are created for changes
- [ ] NodeReducer internal state is not changed on failed transitions or `ModelOnexError`

### 2. Error Model

- [ ] Invalid state and no matching transition always raise `ModelOnexError` with `VALIDATION_ERROR`
- [ ] Conditions not met and evaluation errors never raise `ModelOnexError`; they return structured failure results
- [ ] NodeReducer.process propagates `ModelOnexError` and does not wrap it as a normal result

### 3. Expression Grammar

- [ ] All expressions are exactly three tokens
- [ ] `equals` and `not_equals` use string comparison only
- [ ] Numeric operators use float coercion and trigger `condition_evaluation_error` on parse failures
- [ ] `exists` and `not_exists` only check key presence

### 4. Metadata Contract

- [ ] `metadata` always contains the complete FSM key set (7 keys)
- [ ] `fsm_metadata`, when present, matches the metadata dict logically
- [ ] Unknown metadata keys are ignored by consumers

### 5. Transition Selection

- [ ] Exact state beats wildcard every time
- [ ] Priority is applied only within the same specificity
- [ ] Definition order is a stable tiebreaker
- [ ] No fallback transitions are attempted after a candidate is chosen

### 6. Intents

- [ ] `persist_state` intents are emitted exactly once per successful transition when `persistence_enabled` is true
- [ ] `fsm_state_action` and `fsm_transition_action` intents always contain all required payload keys
- [ ] NodeReducer never directly executes side effects; all effects go through intents

### 7. Reserved Fields

- [ ] All reserved v1.1+ fields are parsed and validated but never change runtime behavior
- [ ] No retry, rollback, hierarchical, or timeout behavior is implemented based solely on reserved fields

### 8. Terminal States

- [ ] Transitions from terminal states raise `ModelOnexError`
- [ ] Contract validation warns about transitions defined from terminal states

### 9. Triggers and Order

- [ ] Trigger matching is strict string equality (case-sensitive, no trimming)
- [ ] YAML declaration order is preserved for tiebreaker precedence

### 10. Condition Evaluation

- [ ] Missing context keys produce `condition_evaluation_error` (except for `exists`/`not_exists`)
- [ ] Condition evaluators are pure (no mutation, no side effects, no external state)

### 11. History and Concurrency

- [ ] FSM executor does not modify `snapshot.history`
- [ ] Implementation documents any history policy it chooses to implement
- [ ] External state stores define their own concurrency/locking strategy

---

## References

- **v1.0.4 Delta Document**: [CONTRACT_DRIVEN_NODEREDUCER_V1_0_4_DELTA.md](./CONTRACT_DRIVEN_NODEREDUCER_V1_0_4_DELTA.md) - Quick reference for changes from v1.0.3 to v1.0.4
- **Versioning Roadmap**: NODEREDUCER_VERSIONING_ROADMAP.md (to be created)
- **Example Contract**: order_processor_fsm.yaml (to be created in examples/contracts/reducer/)
- **Linear Issue**: [OMN-495](https://linear.app/omninode/issue/OMN-495)
- **NodeReducer Source**: [node_reducer.py](../../src/omnibase_core/nodes/node_reducer.py)
- **FSM Executor Source**: [util_fsm_executor.py](../../src/omnibase_core/utils/util_fsm_executor.py)
- **NodeCompute Pattern**: [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](./CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md)

---

**Last Updated**: 2025-12-10
**Version**: 1.0.5
**Status**: DRAFT - Ready for Implementation
**Changelog**:
- v1.0.5: **Clarifications and semantic refinements** (incremental improvements based on implementation feedback):
  - **Context Construction Responsibility**: NodeReducer builds context; executor treats it as readonly.
  - **Terminal State Check**: Clarified that terminal state check occurs BEFORE condition evaluation.
  - **Transition Name on Failure**: `transition_name` in metadata MAY be `None` when no matching transition found.
  - **Action Phase Ordering**: Exit actions execute before entry actions (exit old state, then enter new state).
  - **Intent Emission Ordering**: Deterministic order: exit → transition → entry → persistence.
  - **Self-Loop Behavior**: Self-loop transitions with `success=True` MUST emit persistence intent.
  - **Internal State Divergence**: Clarified recovery semantics when `_fsm_state` diverges from `snapshot.current_state`.
  - **Snapshot History Initialization**: Empty history (`[]`) is valid initial state.
  - **Reserved Context Key Warning**: Reserved keys ignored silently, not errors; warning via logging intent.
  - **Duplicate Structural Transition**: Contract loader MUST warn on duplicate `(from_state, trigger)` pairs.
  - **FSMTransitionResult.metadata Contract**: Clarified required keys on failure scenarios.
  - **History Mutation Semantics**: Executor boundary vs NodeReducer boundary clarified.
  - **Missing Context Key Rule**: Clarified `exists`/`not_exists` behavior explicitly.
  - **Condition Evaluator Purity**: Added explicit prohibition on logging side effects.
  - **Contract Validation Rules**: Expanded table with v1.0.5 rules.
  - **Parser Requirements for exists/not_exists**: Parser MUST allow placeholder token, MUST NOT validate semantically.
  - **Correlation ID Propagation**: Action intents MUST include correlation_id when available.
  - **Context Defensive Copy Rule**: Deep-copy SHOULD be used for nested mutables.
  - **Canonical persist_state Payload**: Example updated to include REQUIRED operation_id.
- v1.0.4: **Critical fixes from implementation review** (full audit + technical review corrections):
  - **Global Normative Rules**: Single Source of Behavior, Reserved Fields Global Rule, NodeReducer Is A Stateful Facade, Glossary.
  - **Single-Entity Constraint**: NodeReducer MAY only be used for single FSM instance; multi-entity requires Pattern C.
  - **Terminal State Behavior**: Contract loader MUST reject outgoing transitions from terminal states; runtime raises ModelOnexError.
  - **Trigger Canonicalization**: Strict string equality, case-sensitive, no trimming. Default trigger "process" is stable/reserved.
  - **Trigger Character Set**: SHOULD conform to `[a-zA-Z0-9_.-]+`.
  - **YAML Order Preservation**: Declaration order determines tiebreaker; order-preserving parsers required.
  - **History Mutation Semantics**: FSM executor MUST NOT modify history. History is opaque - no reliance on structure.
  - **Concurrency Model Disclaimer**: v1.0 provides no concurrency guarantees.
  - **FSMTransitionResult.metadata Contract**: Required keys on failure; error canonical location is `result.error`.
  - **Reserved System Context Keys**: `data`, `operation_id`, `_fsm_*` are system-reserved.
  - **NodeReducer State Initialization**: `_fsm_state` MUST equal `contract.initial_state` on init.
  - **Context Defensive Copy Rule**: Executor SHOULD shallow-copy context before use.
  - **Optional Condition Behavior**: `required: false` conditions don't cause failure; errors treated as False.
  - **Contract Validation Rules**: Table of MUST/SHOULD behaviors for contract loading.
  - **Version Mismatch Handling**: v1.0 does not define migration; implementations SHOULD reject mismatches.
  - **Action Ordering**: Declaration order; `execution_order` with declaration as tiebreaker.
  - **Intent Construction Error Handling**: Catch errors, emit failure Intent; transition may still succeed.
  - **Purity Boundary (Normative)**: Purity guaranteed ONLY at FSM executor level.
  - **State Snapshot Mutation Rules**: MUST NOT mutate in-place, MUST create new instances.
  - **Metadata Type Fix**: `dict[str, str]` to `dict[str, Any]`.
  - **Typed FSM Metadata**: `ModelReducerFsmMetadata` model added.
  - **Reserved Field Warnings**: Explicit warnings in all model docstrings.
  - **ModelReducerInput FSM Mode Note**: Streaming fields reserved/ignored.
  - **Error Model (Hardened)**: MUST/MUST NOT requirements.
  - **Error Propagation**: NodeReducer.process MUST propagate ModelOnexError.
  - **Missing Context Key Rule**: Missing keys produce condition_evaluation_error (except exists/not_exists).
  - **Condition Evaluator Purity**: Pure evaluation required.
  - **Condition Evaluation Error Classification**: Table of error scenarios.
  - **Canonical Action Intent Payload**: Stable shapes for action intents.
  - **Canonical persist_state Payload**: REQUIRED keys defined.
  - **Payload Violation Rule**: Missing REQUIRED key is protocol violation.
  - **Thread Safety (Hardened)**: Single-thread affinity objects.
  - **Expression Evaluation (Normative)**: 3-token rule, string coercion, numeric parsing.
  - **Wildcard Resolution (Algorithmic)**: Pseudocode algorithm.
  - **No Fallback Rule**: Explicit prohibition.
  - **Metadata Evolution Rules**: Forward-compatibility rules.
  - **Validation Failure Lifecycle**: Startup failure and hot-reload rules.
  - **Implementation Checklist**: Comprehensive checklist.
  - **Final Conformance Checklist**: 11-category verification.
  - **Extended Testing Requirements**: v1.0.4 additional tests.
  - **Default Mental Model**: Pattern C (External State Store).
- v1.0.3: Added canonical representation statement, fixed 3-token rule violations, added normative transition algorithm, condition-no-fallback statement, reserved context key protection, metadata stability guarantee, FSM state mutation protection, action semantics clarification, expression grammar design philosophy, numeric equality warning, ModelFSMOperation documentation, wildcard/metadata test acceptance criteria
- v1.0.2: Initial specification draft
