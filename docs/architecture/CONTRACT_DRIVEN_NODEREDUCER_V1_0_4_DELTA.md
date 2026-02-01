> **Navigation**: [Home](../index.md) > [Architecture](./overview.md) > Contract-Driven NodeReducer v1.0 Delta

# Contract-Driven NodeReducer v1.0 – Delta Corrections (v1.0.4 / v1.0.5)

> **Document Type**: Delta / Errata
> **Base Spec**: Contract-Driven NodeReducer v1.0 (v1.0.2 / v1.0.3 drafts)
> **Current Version**: v1.0.5
> **Ticket**: [OMN-495](https://linear.app/omninode/issue/OMN-495)

This document captures **only the corrections and normative changes** introduced in **v1.0.4 and v1.0.5** relative to earlier NodeReducer v1.0 drafts. It does **not** restate the full spec – just the parts that changed or were tightened.

---

## 1. Purity Boundary – Hard Split Between FSM and NodeReducer

### 1.1. What Is Pure (Corrected)

Earlier drafts were hand-wavy about purity and sometimes implied that `NodeReducer` itself was a pure reducer.

**v1.0.4 Correct Behavior**:

- The **only** pure APIs are the FSM executor functions, e.g.:

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

- They:
  - Take all state as explicit parameters.
  - Produce results and intents only.
  - Do not read or write globals.
  - Are **thread-safe by contract**.

### 1.2. What Is Not Pure (Corrected)

`NodeReducer` is now explicitly defined as **not pure**:

- It is a **stateful façade** over a pure FSM core.
- It maintains internal mutable state (`_fsm_state` or equivalent).
- Its true signature is:

    ```python
    class NodeReducer:
        """
        NOT PURE: Maintains internal mutable state.
        The effective signature is:

            process(self, input) -> output  # self contains hidden state
        """
    ```

**Normative rule added**:

- `NodeReducer` MUST NOT be described as pure in docs, comments, or tests.
- Any design that relies on `NodeReducer.process` being pure is **non-conforming**.

---

## 2. Thread Safety – Single-Thread Affinity Only

Earlier language vaguely implied everything was "thread-safe enough" because of immutability.

**v1.0.4 Correction**:

- The following are **thread-safe by contract**:
  - FSM executor functions (`execute_transition`, etc.).
  - Immutable Pydantic models and frozen dataclasses:
    - `ModelReducerInput`
    - `ModelReducerOutput`
    - `ModelFSMStateSnapshot`
    - `ModelFSMTransitionResult`
    - `ModelReducerFsmMetadata`

- `NodeReducer` instances are **not thread-safe**:
  - They MUST be treated as **single-thread-affinity objects**.
  - If an implementation wants to share across threads, it MUST provide its own locking; the spec does not require or assume this.

**New normative statement**:

> v1.0 NodeReducer instances MUST be treated as single-thread affinity objects.

---

## 3. State Snapshot & Mutation Rules

Earlier drafts implied "don't mutate state" but didn't enforce it normatively.

**v1.0.4 Clarification**:

- FSM executor MUST:
  - Treat `ModelFSMStateSnapshot` as effectively immutable.
  - Create **new** snapshots when state changes.
  - NEVER mutate `context` or `history` in-place.

- NodeReducer internal state mutation rules:
  - On `success=True`: internal state MAY be updated to the new state.
  - On `success=False`: internal state MUST NOT change.
  - On `ModelOnexError`: internal state MUST NOT change.

This guarantees: **"no transition performed" ⇒ state really didn't move**.

---

## 4. Metadata Type Fix & Typed FSM Metadata

Earlier drafts used `dict[str, str]` for `ModelReducerOutput.metadata`, which was too restrictive for structured FSM metadata.

### 4.1. `ModelReducerOutput.metadata` Type Correction

**Change**:

- `metadata` changed from:

    ```python
    metadata: dict[str, str]
    ```

- To:

    ```python
    metadata: dict[str, Any]
    ```

**Reason**: FSM metadata needs booleans, lists, `None`, etc. (e.g., `failed_conditions: list[str]`).

### 4.2. New `ModelReducerFsmMetadata` (Typed)

A new model was added for type-safe FSM metadata:

- `ModelReducerFsmMetadata` contains:

  - `fsm_state`
  - `fsm_previous_state`
  - `fsm_transition_success`
  - `fsm_transition_name`
  - `failure_reason`
  - `failed_conditions`
  - `error`

**Normative pattern**:

- Implementations SHOULD:
  - Populate `fsm_metadata: ModelReducerFsmMetadata | None`.
  - ALSO populate `metadata: dict[str, Any]` with the same core FSM fields for backwards compatibility.

---

## 5. FSM Metadata Contract – Always-Present Keys

Earlier drafts described metadata keys informally; v1.0.4 makes this **normative**.

**New requirement**:

For every FSM operation in FSM mode, `ModelReducerOutput.metadata` MUST contain the following keys, **always present** (values may be `None`):

- `fsm_state: str`
- `fsm_previous_state: str`
- `fsm_transition_success: bool`
- `fsm_transition_name: str | None`
- `failure_reason: str | None`
- `failed_conditions: list[str] | None`
- `error: str | None`

Implementations that omit or rename these keys are **non-conforming**.

---

## 6. Error Model – MUST vs MUST NOT Raise

Earlier versions blurred the line between configuration errors and business failures.

**v1.0.4 introduces strict rules**:

### 6.1. MUST Raise `ModelOnexError` When:

1. **Invalid current state**:
   - Current state not in declared states.
   - Error code MUST be `VALIDATION_ERROR`.

2. **No matching transition**:
   - No transition matches `(current_state, trigger)` (even with wildcard).
   - Error code MUST be `VALIDATION_ERROR`.

### 6.2. MUST NOT Raise `ModelOnexError` When:

3. **Conditions not met**:
   - Transition is found, but conditions evaluate to `False`.
   - Return `ModelFSMTransitionResult(success=False)` with:
     - `failure_reason="conditions_not_met"`.

4. **Condition evaluation error**:
   - Evaluation throws (e.g., value missing, type issues).
   - Return `ModelFSMTransitionResult(success=False)` with:
     - `failure_reason="condition_evaluation_error"`.

This cleanly separates:

- **Configuration errors** → exceptions.
- **Business constraint failures** → structured result.

---

## 7. Expression Evaluation – Normative Operator Semantics

Earlier drafts described operators informally; v1.0.4 locks them down.

### 7.1. 3-Token Grammar (Strict)

All condition expressions MUST follow:

- `"<field> <operator> <value>"` (exactly 3 tokens when split on whitespace).

If `len(tokens) != 3`, the implementation MUST treat it as a condition evaluation error and set `failure_reason="condition_evaluation_error"`.

### 7.2. String Operators (`equals`, `not_equals`)

**Normative behavior**:

- `equals` / `not_equals` MUST be implemented as:

    ```python
    str(lhs) == str(rhs)
    ```

- No type-aware equality in v1.0.
- Numeric equality with `equals` is **explicitly discouraged** and considered undefined behavior.

### 7.3. Numeric Operators (`greater_than`, `less_than`)

- Both sides MUST be parsed via `float(...)`.
- If parsing fails:
  - Condition MUST evaluate as failed.
  - `failure_reason` MUST be `"condition_evaluation_error"`.

### 7.4. Existence Operators (`exists`, `not_exists`)

- `exists`:
  - `True` iff key is present in context dict (value irrelevant).
- `not_exists`:
  - `True` iff key is absent from context dict.

The third token is syntactic padding and is ignored but still required (to preserve 3-token rule).

---

## 8. Wildcard Transition Resolution – Algorithmic Rules

Earlier language described wildcard precedence informally. v1.0.4 replaces that with a precise algorithm.

### 8.1. Matching Algorithm

Given `current_state`, `trigger`, and transitions `T`:

1. Filter to `candidate_set` where `t.trigger == trigger`.
2. Partition:
   - `exact_matches`: `t.from_state == current_state`
   - `wildcards`: `t.from_state == "*"`
3. If `exact_matches` non-empty:
   - Ignore all wildcard transitions.
   - Choose transition with:
     - Highest `priority` (descending).
     - If tie: first one defined in the contract.
4. Else if `wildcards` non-empty:
   - Choose transition with:
     - Highest `priority` (descending).
     - If tie: first one defined in the contract.
5. Else:
   - Raise `ModelOnexError(VALIDATION_ERROR)` – no matching transition.

### 8.2. Non-Obvious Constraint

- **Exact state match ALWAYS beats wildcard**, regardless of priority.
- Priority is only used **within** the same specificity class.

Any "optimization" that lets a wildcard with higher priority override an exact match is **non-conforming**.

---

## 9. Canonical Intent Payloads for FSM Actions

Previous drafts mentioned action Intents but didn't normatively define payload shape.

v1.0.4 introduces a **stable payload contract** for:

- `fsm_state_action`
- `fsm_transition_action`

### 9.1. `fsm_state_action` Payload

**Required Keys**:

- `fsm_name: str`
- `state: str`
- `action_name: str`
- `action_phase: str` (`"entry"` or `"exit"`)
- `operation_id: str`

**Optional Keys**:

- `previous_state: str | None`
- `next_state: str | None`
- `correlation_id: str | None`

**Canonical Intent Example**:

```python
ModelIntent(
    intent_type="fsm_state_action",
    target="action_executor",
    payload={
        "fsm_name": fsm.state_machine_name,
        "state": state_name,
        "action_name": action_name,
        "action_phase": "entry",
        "operation_id": str(input_data.operation_id),
        "previous_state": old_state,
        "next_state": new_state,
        "correlation_id": str(fsm.correlation_id),
    },
    priority=1,
)
```

### 9.2. `fsm_transition_action` Payload

**Required Keys**:

- `fsm_name: str`
- `transition_name: str`
- `from_state: str`
- `to_state: str`
- `action_name: str`
- `operation_id: str`

**Optional Keys**:

- `trigger: str | None`
- `correlation_id: str | None`

**Canonical Intent Example**:

```python
ModelIntent(
    intent_type="fsm_transition_action",
    target="action_executor",
    payload={
        "fsm_name": fsm.state_machine_name,
        "transition_name": transition.transition_name,
        "from_state": old_state,
        "to_state": new_state,
        "action_name": action.action_name,
        "operation_id": str(input_data.operation_id),
        "trigger": trigger,
        "correlation_id": str(fsm.correlation_id),
    },
    priority=1,
)
```

**Payload Stability Guarantee**:

- REQUIRED keys must **always** be present and must not be renamed.
- New versions may add optional keys, but cannot break the required ones.

---

## 10. Recommended Usage Patterns – Default Mental Model

Earlier drafts hinted at multiple styles without declaring a default.

v1.0.4 explicitly defines **Pattern C** as the default mental model:

### Pattern C (Default): External State Store

- FSM state is stored externally (DB, KV store, etc.).
- FSM executor is used as a stateless adapter.

```python
async def handle_request(request, state_store):
    entity_id = request.entity_id

    current_state = await state_store.get_state(entity_id)

    snapshot = ModelFSMStateSnapshot(
        current_state=current_state,
        context={},  # or loaded context
    )

    result = execute_transition(fsm, snapshot, trigger, context)

    await state_store.set_state(entity_id, result.new_state)

    return result
```

This pattern:
- Avoids hidden state in long-lived instances.
- Plays nicely with horizontal scaling.
- Makes testing and replay simpler.

---

## 11. Implementation Checklist – v1.0.4 Delta Items Only

If your implementation was aligned with earlier v1.0 drafts, these are the **extra** things you must do to be v1.0.4-conformant:

### 1. Purity Boundary

- [ ] Remove any claims that `NodeReducer.process` is pure.
- [ ] Explicitly document that only FSM executor functions are pure.

### 2. Thread Safety

- [ ] Document `NodeReducer` as single-thread-affinity.
- [ ] Ensure tests do not rely on cross-thread safety for a shared instance.

### 3. Metadata

- [ ] Change `ModelReducerOutput.metadata` to `dict[str, Any]`.
- [ ] Always populate all FSM metadata keys, even if `None`.
- [ ] Add `ModelReducerFsmMetadata` and populate `fsm_metadata` where possible.

### 4. Error Model

- [ ] Raise `ModelOnexError(VALIDATION_ERROR)` for invalid state and no matching transition.
- [ ] Use `ModelFSMTransitionResult(success=False)` for condition failures and evaluation errors.

### 5. Expression Semantics

- [ ] Enforce 3-token rule for expressions.
- [ ] Implement string-based equality and float-based numeric comparisons.
- [ ] Mark numeric equality via `equals` as undefined behavior in docs.

### 6. Wildcard Resolution

- [ ] Implement the exact matching algorithm (exact > wildcard, then priority, then definition order).

### 7. Action Intents

- [ ] Emit `fsm_state_action` and `fsm_transition_action` with the canonical payloads.
- [ ] Use `"action_executor"` as `target` by default (unless your system has a different configured target, in which case document it).

---

**If all of the above boxes are checked, your implementation is delta-aligned with v1.0.4 and compatible with the full spec.**

---

## Additional v1.0.4 Normative Rules

The following rules were added to strengthen the spec:

### No Fallback Rule

If a chosen transition fails due to condition failure or evaluation error, the executor MUST NOT attempt fallback or alternative transitions. v1.0 prohibits any kind of fallback transition resolution. The failure is final for that invocation.

### Persistence Intent Rule

When `persistence_enabled` is `true`, exactly one `persist_state` Intent MUST be emitted per successful transition. On failed transitions (`success=False`), no persistence Intent MUST be emitted.

### Typed vs Dict Precedence

If `fsm_metadata` is present, consumers SHOULD prefer it over the `metadata` dict. Both representations MUST remain logically consistent and MUST NEVER diverge.

### History Semantics

v1.0 does not define any semantics for `snapshot.history` beyond storing literal state values. Reducers, orchestrators, or tooling MUST NOT rely on history ordering, meaning, or presence. History is purely informational and MAY be empty.

### History Mutation Prohibition

FSM executors MUST NOT modify `snapshot.history` in place. Any history updates MUST occur by creating a new list and constructing a new snapshot instance.

---

## References

- **Full Spec**: [CONTRACT_DRIVEN_NODEREDUCER_V1_0.md](./CONTRACT_DRIVEN_NODEREDUCER_V1_0.md)
- **Linear Issue**: [OMN-495](https://linear.app/omninode/issue/OMN-495)

---

## 12. v1.0.5 Additional Clarifications

The following clarifications were added in v1.0.5 to address implementation feedback:

### 12.1. Context Construction Responsibility

Context construction is the **NodeReducer's responsibility**, not the FSM executor's:
- NodeReducer MUST build the context dict before calling the executor
- FSM executor MUST treat context as **readonly** - no mutation, no key injection

### 12.2. Terminal State Check Location

Terminal state checking MUST occur in the FSM executor:
- Executor MUST check `snapshot.current_state` against terminal states **before** evaluating transitions

### 12.3. Transition Name on Condition Failure

When a transition is selected but fails due to conditions:
- `fsm_transition_name` MUST be the selected transition's name (not `None`)
- `fsm_transition_name` is `None` ONLY when no matching transition exists

### 12.4. Action Phase Ordering

Action execution follows strict phase ordering:
1. Exit actions MUST complete before transition actions begin
2. Transition actions MUST complete before entry actions begin
3. Entry actions execute last

The `execution_order` field controls ordering **within** a phase only.

### 12.5. Intent Emission Ordering

Intents MUST be emitted in deterministic order:
1. Exit action intents
2. Transition action intents
3. Entry action intents
4. Persistence intent (if enabled and success=True)

### 12.6. Self-Loop Persistence

Self-loop transitions (same `from_state` and `to_state`) with `success=True` MUST emit persistence intent when enabled.

### 12.7. Internal State Divergence

NodeReducer SHOULD detect and raise `ModelOnexError` if `_fsm_state` diverges from expected state.

### 12.8. Snapshot History Initialization

`snapshot.history` MUST always be a list, never `None`. Empty list `[]` is valid.

### 12.9. Reserved Context Key Warning

When user metadata contains reserved keys, Reducer MUST emit a warning Intent (not silently drop).

### 12.10. Duplicate Structural Transition Validation

Two transitions with identical `(from_state, trigger, priority)` tuple MUST raise `VALIDATION_ERROR`.

### 12.11. exists/not_exists Parser Requirements

Parser MUST allow any placeholder token for exists/not_exists and MUST NOT validate it semantically.

### 12.12. Correlation ID Propagation

If FSMSubcontract defines correlation_id, action intents MUST include it in the payload.

### 12.13. Context Deep Copy

For contexts with nested mutables, implementations SHOULD use `copy.deepcopy()`.

### 12.14. failed_conditions on Evaluation Error

When `failure_reason="condition_evaluation_error"`, `failed_conditions` MUST be `None`.

### 12.15. Optional Condition Error Handling

Optional condition errors MUST NOT produce `failure_reason` classification - they are silently treated as `False`.

---

## References

- **Full Spec**: [CONTRACT_DRIVEN_NODEREDUCER_V1_0.md](./CONTRACT_DRIVEN_NODEREDUCER_V1_0.md)
- **Linear Issue**: [OMN-495](https://linear.app/omninode/issue/OMN-495)

---

**Last Updated**: 2025-12-10
**Version**: 1.0.5
