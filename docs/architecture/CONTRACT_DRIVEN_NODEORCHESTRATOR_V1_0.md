# Contract-Driven NodeOrchestrator v1.0 Specification

> **Version**: 1.0.5
> **Date**: 2025-12-10
> **Status**: DRAFT - Ready for Implementation
> **Ticket**: [OMN-496](https://linear.app/omninode/issue/OMN-496)
> **Full Roadmap**: NODEORCHESTRATOR_VERSIONING_ROADMAP.md (to be created)
> **See Also**: [ONEX Terminology Guide](../standards/onex_terminology.md) for canonical definitions of Orchestrator, Action, and other ONEX concepts.

---

## Executive Summary

This document defines the **minimal v1.0 implementation** of contract-driven `NodeOrchestrator`. The goal is a stable foundation for workflow-driven coordination that can be shipped safely and extended incrementally.

**v1.0 Scope**: Workflow-driven coordination with pure function semantics, Action emission for deferred execution, dependency-aware topological ordering, wave-based parallel execution, and cycle detection. No distributed coordination, no complex compensation, no saga patterns.

**Core Philosophy**: The workflow executor is a pure function:

```text
execute_workflow(definition, steps, workflow_id) -> (result, actions[])
```

All side effects are emitted as Actions for target nodes (NodeCompute, NodeEffect, NodeReducer) to execute. This maintains workflow executor purity and enables deterministic coordination.

**Key Distinction from NodeReducer**:
- **NodeReducer**: FSM-driven state transitions using `ModelIntent` (passive declarations)
- **NodeOrchestrator**: Workflow-driven coordination using `ModelAction` (active with lease semantics)

**v1.0.5 Clarification**: The purity guarantee applies to the **workflow executor functions**, not to `NodeOrchestrator` instances. See [Purity Boundary](#purity-boundary-v105-normative) for details.

---

## Table of Contents

1. [Conceptual Modes](#conceptual-modes)
2. [Global Normative Rules (v1.0.5)](#global-normative-rules-v105)
3. [Design Principles](#design-principles)
4. [Purity Boundary (v1.0.5 Normative)](#purity-boundary-v105-normative)
5. [Repository Boundaries (v1.0.5 Informative)](#repository-boundaries-v105-informative)
6. [v1.0 Scope](#v10-scope)
7. [Reserved Fields](#reserved-fields-v10)
8. [Core Models](#core-models)
9. [Workflow Subcontract Models](#workflow-subcontract-models)
10. [Enums](#enums)
11. [Contract Validation Invariants](#contract-validation-invariants)
12. [Execution Model](#execution-model)
13. [Action Pattern](#action-pattern)
14. [Orchestrator Metadata Contract](#orchestrator-metadata-contract)
15. [Error Model (v1.0.5)](#error-model-v105)
16. [NodeOrchestrator Behavior](#v10-nodeorchestrator-behavior)
17. [Thread Safety and State Management](#thread-safety-and-state-management)
18. [Example Contracts](#example-contracts)
19. [Implementation Plan](#implementation-plan)
20. [Acceptance Criteria](#acceptance-criteria)
21. [Glossary](#glossary)
22. [Changelog](#changelog)

---

## Conceptual Modes

NodeOrchestrator supports two conceptual modes. **v1.0 implements Workflow Coordination mode only.**

### Mode 1: Workflow Coordination (v1.0 Implemented)

The primary v1.0 use case. NodeOrchestrator acts as a **workflow coordination engine**:

```text
execute_workflow(definition, steps, workflow_id) -> (result, actions[])
```

- **Input**: `ModelWorkflowDefinition` + `list[ModelWorkflowStep]` + workflow ID (all fully typed Pydantic models)
- **Output**: Execution result + list of Actions for target node execution
- **Data Flow**: Steps define what to do, dependencies define execution order
- **Execution Modes**: `SEQUENTIAL`, `PARALLEL`, `BATCH`

**v1.0.2 Normative**: Steps MUST always be `ModelWorkflowStep` instances. Definitions MUST always be `ModelWorkflowDefinition` instances. Core receives fully typed Pydantic models from Infra. Core does NOT parse YAML. Core does NOT coerce dicts into models.

### Mode 2: Batch Processing Pipelines (Reserved - Not in v1.0)

Future use case for large-scale batch coordination:

```text
execute_batch(items[], batch_config) -> batch_result
```

- **Input**: Collection of items + batch configuration
- **Output**: Aggregated batch results
- **Processing Modes**: `STREAMING`, `WINDOWED`, `CHUNKED`
- **Status**: Fields present in enums but **execution not implemented in v1.0**

### v1.0 Enforcement

When using Workflow Coordination mode in v1.0:

- `execution_mode` **MUST** be `SEQUENTIAL`, `PARALLEL`, or `BATCH`
  - `CONDITIONAL` and `STREAMING` MUST raise `ModelOnexError` with code `VALIDATION_ERROR` (reserved but NOT accepted in v1.0)
- Complex compensation patterns, saga rollbacks, and distributed locks are **ignored** (reserved for future versions)

### Context Construction

The workflow executor builds execution context from `ModelOrchestratorInput` as follows:

```python
def _build_workflow_context(input_data: ModelOrchestratorInput) -> dict[str, Any]:
    """
    Build workflow execution context from orchestrator input.

    Context keys:
        - All keys from input_data.metadata (shallow copy)
        - "workflow_id": The workflow ID as string
        - "operation_id": The operation ID as string
        - "execution_mode": The execution mode value
    """
    context = dict(input_data.metadata)  # Shallow copy
    context["workflow_id"] = str(input_data.workflow_id)
    context["operation_id"] = str(input_data.operation_id)
    context["execution_mode"] = input_data.execution_mode.value
    return context
```

**Reserved Context Keys**:

| Key | Source | Type |
|-----|--------|------|
| `workflow_id` | `input_data.workflow_id` | `str` |
| `operation_id` | `input_data.operation_id` | `str` |
| `execution_mode` | `input_data.execution_mode` | `str` |

Reserved keys in metadata MUST NOT override system-assigned context keys. If conflict occurs, system keys take precedence.

---

## Global Normative Rules (v1.0.5)

These rules override all other sections when there is ambiguity or contradiction.

### Single Source of Behavior

The v1.0.5 normative behavior is defined **only** by:
- The Error Model section
- The Execution Model section
- The Action Pattern section
- The Orchestrator Metadata Contract section
- The Contract Validation Invariants section

Any contradictions elsewhere (including docstrings, diagrams, or prose) are **non-normative** and MUST be interpreted to match these sections.

### Reserved Fields Global Rule (v1.0.4 Normative)

Any field globally marked as reserved for v1.1 or later:
- MUST be parsed by SPI during contract codegen
- MUST be preserved by Core in typed models
- MUST be ignored by executor deterministically
- MUST NOT alter runtime behavior in v1.0 even if set

If an implementation executes reserved behavior in v1.0, it is **non-conforming**.

### Contract Loading Responsibility (v1.0.4 Normative)

NodeOrchestrator MUST NOT load `workflow_definition` from `self.contract`:
- Contract resolution occurs at container build time, not inside orchestrator
- `workflow_definition` MUST be injected by container or dispatcher layer
- NodeOrchestrator receives fully-resolved typed models, not raw contracts

**Rationale**: Separation of concerns - contract loading is infrastructure (SPI/Infra), execution is core logic (Core).

### Workflow Definition Injection (v1.0.4 Normative)

NodeOrchestrator MUST treat `workflow_definition` as immutable once injected:
- Container or dispatcher MUST inject `workflow_definition` prior to `process()` being called
- Reassignment of `workflow_definition` during `process()` execution is undefined behavior
- NodeOrchestrator MUST NOT modify the injected `workflow_definition`

### Subcontract Model Immutability (v1.0.4 Normative)

Orchestrator MUST treat all subcontract models as immutable values:
- No mutation of `ModelWorkflowStep` instances
- No mutation of `ModelWorkflowDefinition` instances
- Implementations MAY deep copy if internal mutation is required
- This enables safe sharing of models across concurrent workflows

### Execution Graph Prohibition (v1.0.4 Normative)

The executor MUST NOT consult `execution_graph` even if present in `ModelWorkflowDefinition`:
- Executor MUST NOT check for equivalence between the graph and the step list
- Executor MUST NOT log warnings if the graph and steps disagree
- The `execution_graph` field exists for contract generation purposes only in v1.0

### NodeOrchestrator Is A Stateful Facade

- NodeOrchestrator is a **stateful facade** around the pure workflow executor
- v1.0 NodeOrchestrator is stateful ONLY for `workflow_definition`
- All other state MUST be passed through pure functions
- External workflow stores are RECOMMENDED but not required
- The workflow executor (`execute_workflow`) is the canonical behavior
- Any optimizations inside NodeOrchestrator MUST NOT change the externally observed semantics defined for `execute_workflow` plus the error model and metadata contract

### Side Effect Prohibition (v1.0.4 Normative)

NodeOrchestrator MUST NOT write to external systems:
- Orchestrator emits actions only
- All writes occur in downstream nodes (NodeEffect, NodeReducer)
- Orchestrator MUST NOT call container services or external systems directly
- Orchestrator MUST NOT perform I/O operations (database, network, filesystem)

### Single-Workflow Constraint (v1.0.4 Normative)

v1.0 `NodeOrchestrator` MAY only be used for a **single workflow instance** (single workflow).

Multi-workflow orchestrators (e.g., managing workflows for multiple tenants):
- MUST NOT rely on `NodeOrchestrator.workflow_definition`
- MUST operate using pure executors with external workflow management
- MUST manage workflow-keyed state externally

**Rationale**: `NodeOrchestrator.workflow_definition` is a single scalar value, not a map. Attempting to use one `NodeOrchestrator` instance for multiple workflows will cause definition corruption.

### Cycle Detection Requirement (v1.0.4 Normative)

Workflow validation MUST detect cycles before execution:
- Cycles MUST be detected using DFS-based cycle detection
- Workflows with cycles MUST raise `ModelOnexError` with code `VALIDATION_ERROR`
- Cycle detection MUST occur at validation time, not execution time

### Topological Ordering Requirement (v1.0.4 Normative)

Workflow execution MUST use topological ordering:
- Steps MUST be processed in dependency-respecting order
- Kahn's algorithm is the RECOMMENDED implementation
- Steps with no dependencies are processed first
- Steps with dependencies are processed after all dependencies complete

### Topological Ordering Tiebreaker (v1.0.4 Normative)

When multiple steps have in-degree 0 at a given wave (i.e., multiple steps are eligible for concurrent processing):
- Order MUST follow contract declaration order (YAML order as preserved during loading)
- This ensures deterministic ordering even when topological constraints allow multiple valid orderings

### YAML Order Preservation (v1.0.4 Normative)

Contract loading MUST preserve declaration order exactly as written in YAML:
- Step order in `steps` list determines tiebreaker precedence for same-priority steps
- Dependency order is preserved
- Action order within steps is preserved

Implementations MUST use order-preserving parsers (Python 3.7+ dicts preserve insertion order).

### Action Emission Ordering (v1.0.4 Normative)

Actions MUST be emitted in deterministic order:
1. Actions for completed steps (in processing order)
2. No actions for failed or skipped steps

NodeOrchestrator MUST NOT reorder actions. Consumers MAY rely on this ordering.

### Action Emission Wave Ordering (v1.0.4 Normative)

Action emission MUST follow strict wave ordering:
- Within a wave, actions MUST appear in YAML declaration order
- Across waves, actions MUST appear in wave order (wave N before wave N+1)
- All actions in wave N are emitted before any action in wave N+1
- This guarantees deterministic action ordering for consumers

### Lease-Based Single-Writer Semantics (v1.0.4 Normative)

Every `ModelAction` MUST include:
- `lease_id`: UUID proving Orchestrator ownership of the action
- `epoch`: Monotonically increasing version number (>= 0)

v1.0 uses **per-action leases**. Each action has its own lease independent of other actions.

**Note**: v1.1 may introduce hierarchical leases (workflow lease -> action leases) for improved coordination.

These fields enable:
- Single-writer guarantees: Only the lease holder can execute the action
- Optimistic concurrency control: Epoch conflicts are detectable
- Distributed coordination: Multiple orchestrators can coordinate safely

### Epoch Increment Responsibility (v1.0.4 Normative)

Epoch management follows a clear separation of concerns:
- Orchestrator sets `epoch=0` for all newly created actions
- Target node increments epoch after each successful execution
- Orchestrator MUST NOT increment epoch - this is the target node's responsibility

### Step Priority vs Action Priority (v1.0.4 Normative)

Step priority and action priority serve different purposes:

| Aspect | Step Priority | Action Priority |
|--------|---------------|-----------------|
| **Scope** | Authoring-time hint | Execution-time constraint |
| **Range** | 1-1000 | 1-10 |
| **Purpose** | Order tiebreaker for same-wave steps | Target node scheduling priority |

**Clamping Rule**: `action_priority = min(step.priority, 10)`
- Clamping is REQUIRED for schema boundary conversion
- Clamping MUST NOT emit warnings (this is expected behavior, not an anomaly)
- Batch mode MUST clamp step priority to action priority exactly as in sequential and parallel modes

### Concurrency Model (v1.0.4 Disclaimer)

v1.0 provides **limited concurrency support**:
- Wave-based parallel execution within a single workflow
- No cross-workflow coordination
- No distributed locking semantics
- No optimistic concurrency control beyond epoch tracking

External coordination (e.g., distributed locks) MUST be provided by the infrastructure.

### Load Balancing Prohibition (v1.0.4 Normative)

v1.0 MUST ignore `load_balancing_enabled` field entirely:
- Load balancing logic MUST NOT exist inside Orchestrator
- The field exists for forward compatibility but has no effect in v1.0
- Future versions may implement load balancing in the infrastructure layer

### Contract Validation Rules (v1.0.4 Normative)

Contract validation MUST detect and handle:

| Condition | Behavior |
|-----------|----------|
| Dependency cycle detected | MUST raise `ModelOnexError` |
| Duplicate step ID | MUST raise `ModelOnexError` |
| Invalid dependency reference | MUST raise `ModelOnexError` |
| Empty workflow name | MUST raise `ModelOnexError` |
| Invalid execution mode (`CONDITIONAL`, `STREAMING`) | MUST raise `ModelOnexError` |
| Negative timeout | MUST raise `ModelOnexError` |
| Reserved compensation fields set | Saga-related fields MUST be ignored and MUST NOT influence control flow |
| Saga patterns defined in contract | Saga-related fields MUST be ignored and MUST NOT influence control flow |

### Disabled Step Handling (v1.0.4 Normative)

Steps with `enabled: false`:
- MUST be skipped entirely (no action created)
- MUST NOT be marked as failed
- MUST be included in `skipped_steps` (not `completed_steps` or `failed_steps`)
- Dependencies on disabled steps MUST be treated as automatically satisfied

### Disabled Step Forward Compatibility (v1.0.4 Normative)

v1.0 MUST treat disabled steps as automatically satisfied:
- This applies even if the disabled step would be invalid in stricter future versions
- Disabled steps are not validated beyond basic structural checks
- This ensures forward compatibility when stricter validation is added in future versions

### DAG Invariant for Disabled Steps (v1.0.4 Normative)

- Workflow MUST remain a valid DAG after disabling steps
- Disabled steps count as automatically satisfied dependencies
- Disabled steps MUST NOT create hidden cycles (cycles that would only manifest if step were enabled)
- Validation SHOULD check DAG validity for all possible enable/disable combinations

### Skip on Failure Semantics (v1.0.4 Normative)

The `skip_on_failure` field has precise semantics:
- `skip_on_failure` applies ONLY to failures of earlier steps in the workflow
- `skip_on_failure` does NOT override unmet dependency constraints
- Unmet dependencies ALWAYS block execution, regardless of `skip_on_failure` setting
- A step with `skip_on_failure=true` will be skipped if any prior step failed, but only if its dependencies are otherwise met

### Dependency Met Check (v1.0.4 Normative)

A step's dependencies are considered met when:
- All step IDs in `depends_on` are either:
  - In `completed_step_ids` set, OR
  - Reference a disabled step (`enabled: false`)
- Executor MUST check: `all(dep_id in completed_step_ids or is_disabled(dep_id) for dep_id in step.depends_on)`

### Dependency Failure Semantics (v1.0.4 Normative)

If a step's dependency cannot be met:
- Step is not eligible for action creation
- If workflow cannot progress (all remaining steps have unmet dependencies), workflow MUST fail deterministically
- This applies AFTER disabled steps are treated as satisfied
- The workflow result MUST include unprocessed steps in appropriate tracking fields

### UUID Stability (v1.0.4 Normative)

UUID generation for steps follows a strict rule:
- `step_id` values come from contract load time, not execution time
- Orchestrator MUST NOT generate `step_id` values
- `step_id` values are immutable once loaded from the contract
- This ensures deterministic identification of steps across workflow executions

### Step Metadata Immutability (v1.0.4 Normative)

NodeOrchestrator MUST NOT modify `ModelWorkflowStep` metadata:
- `metadata` fields MUST NOT be altered during processing
- `correlation_id` MUST NOT be modified or regenerated
- All step fields are read-only from the orchestrator's perspective
- If metadata modification is needed, create a new step instance via `model_copy()`

### Expression Evaluation Prohibition (v1.0.4 Normative)

v1.0 MUST NOT parse or evaluate any conditional expressions in contracts:
- Expression evaluation engine is reserved for v1.1
- Fields that might contain expressions (e.g., condition strings) MUST be ignored
- No expression parsing, compilation, or evaluation logic may exist in v1.0
- This ensures clean separation of declarative definitions from runtime evaluation

### Metadata Isolation (v1.0.4 Normative)

`WorkflowExecutionResult.metadata` MUST NOT include orchestrator-internal fields:
- Prohibited internal fields: `step_to_action_map`, execution waves, dependency graph structures
- Only user-facing metadata may be included in the result
- Internal bookkeeping data MUST remain internal to the orchestrator implementation

### Validation Phase Separation (v1.0.4 Normative)

The pure executor assumes `workflow_definition` is already valid:
- Validation happens BEFORE execution, not during
- Executor MUST NOT re-validate `workflow_definition` during `process()`
- If validation is needed, it must be performed by the caller before invoking the executor
- This separation enables efficient execution without redundant validation

### Action Creation Exception Handling (v1.0.4 Normative)

Exception handling during action creation follows strict rules:
- Only `ModelOnexError` MAY be raised intentionally by action creation logic
- All other exceptions MUST be caught and converted into FAILED steps
- Unexpected exceptions MUST NOT propagate to the caller
- Failed steps due to exceptions MUST include error details in the result

### Failure Strategy Precedence (v1.0.4 Normative)

Step-level `error_action` takes precedence over workflow-level `failure_strategy`:
- When a step has explicit `error_action` set, that value is used
- Workflow-level `failure_strategy` applies ONLY when step-level `error_action` is not explicitly set
- This allows fine-grained control over error handling at the step level while providing workflow-wide defaults

### Partial Parallel-Wave Failure Continuation (v1.0.4 Normative)

Behavior when a step fails within a parallel wave:
- If any step in a wave fails with `error_action="stop"`:
  - All remaining steps in the same wave MUST be skipped
  - Workflow ends with FAILED state
  - Steps already completed in the wave remain completed
- If `error_action="continue"`:
  - Remaining steps in the wave MAY execute only if their dependencies are met
  - A failed step's dependents will have unmet dependencies

### Orphan Step Handling (v1.0.4 Normative)

Steps with no dependency path from any root (orphan steps):
- MUST still be executed (they are not invalid)
- Orphan detection MUST NOT cause validation failure in v1.0
- Orphan steps are processed in the first wave (no dependencies to wait for)
- This allows workflows where some steps are independent entry points

### Dependency List Ordering (v1.0.4 Normative)

Orchestrator MUST treat `depends_on` list as semantically unordered:
- The order of UUIDs in `depends_on` has no semantic meaning
- During DAG construction, dependencies MUST be sorted by step declaration index for determinism
- This ensures consistent behavior regardless of how dependencies are listed

### Action Metadata Immutability (v1.0.4 Normative)

`Action.metadata` MUST be treated as immutable after action creation:
- Executor MUST NOT mutate metadata post-creation
- If metadata modification is needed, create a new action via `model_copy()`
- This enables safe action sharing across concurrent consumers

### parallel_group vs depends_on Precedence (v1.0.4 Normative)

When `parallel_group` conflicts with `depends_on`:
- `parallel_group` MAY NOT override `depends_on`
- If parallel_group would suggest concurrent execution but dependency ordering requires sequential, dependency ordering wins
- Dependencies are the authoritative source for execution order

### parallel_group Non-Semantic in v1.0 (v1.0.4 Normative)

The `parallel_group` field behavior in v1.0:
- `parallel_group` is ignored in v1.0 except as metadata
- Executor MUST NOT enforce group-based batching based on `parallel_group`
- Parallel execution is determined solely by dependency topology in v1.0
- Future versions MAY use `parallel_group` for execution hints

### Retry Count Semantics (v1.0.4 Normative)

The `retry_count` field semantics in v1.0:
- Retries do NOT produce new actions in v1.0
- `retry_count` is advisory metadata only (passed to target node)
- Orchestrator MUST NOT implement retry logic internally in v1.0
- v1.1 MAY introduce retry-action chains where retries produce new actions

### Empty Workflow Handling (v1.0.4 Normative)

Behavior for workflows with no steps:
- Empty workflow (steps=[]) MUST succeed immediately with COMPLETED state
- No actions are emitted for empty workflows
- Execution time SHOULD be near-zero
- This is valid and not an error condition

### Action Payload Type Requirements (v1.0.4 Normative)

Type requirements for `Action.payload`:
- `Action.payload` MUST contain only JSON-serializable values
- Non-serializable values (functions, classes, file handles, etc.) MUST cause `ModelOnexError` during action creation
- This ensures actions can be safely serialized for distributed execution

### Cross-Step correlation_id Consistency (v1.0.4 Normative)

Handling of `correlation_id` across steps:
- `correlation_id` MUST uniquely identify step lineage within a workflow
- Orchestrator MUST NOT generate or modify `correlation_id` - it comes from the step definition
- `correlation_id` MUST appear in `action.metadata` exactly as provided in the step
- This enables end-to-end tracing of workflow execution

### order_index Non-Semantic (v1.0.4 Normative)

The `order_index` field behavior in v1.0:
- `order_index` MUST NOT influence execution order in v1.0
- If provided, `order_index` is metadata only (preserved but not used)
- Execution order is determined by dependencies and declaration order only
- Future versions MAY use `order_index` for explicit ordering hints

### action_id Global Uniqueness (v1.0.4 Normative)

Uniqueness requirements for `action_id`:
- Every `action_id` MUST be globally unique across all workflows and orchestrators
- Reuse of `action_id` is non-conforming behavior
- UUIDs MUST be generated using cryptographically secure random generators
- Collision detection is not required (probability is negligible with proper UUID generation)

### workflow_id vs operation_id Semantics (v1.0.4 Normative)

Distinction between `workflow_id` and `operation_id`:
- `workflow_id` identifies a workflow instance (the workflow being executed)
- `operation_id` identifies a single invocation of `orchestrator.process()`
- Multiple operations MAY share the same `workflow_id` (e.g., re-execution, continuation)
- Each operation MUST have a unique `operation_id`

### Global Timeout Mid-Wave Behavior (v1.0.4 Normative)

Behavior when global timeout elapses during wave execution:
- If global timeout elapses:
  - All unprocessed steps MUST be marked failed
  - Steps in-progress MUST be assumed failed (no guarantee of completion)
  - Workflow ends with FAILED state
  - Actions already emitted remain valid (target nodes decide on timeout)

### Input Metadata Immutability (v1.0.4 Normative)

Immutability of input data metadata:
- `input_data.metadata` MUST NOT be mutated during `process()`
- If additional metadata is required, copy and extend internally
- Original input metadata MUST remain unchanged after `process()` returns
- This enables safe input reuse across multiple invocations

### Step Iteration Order Stability (v1.0.4 Normative)

Stability requirements for step iteration:
- All iteration over `workflow_steps` MUST preserve original step order exactly as loaded
- Step order MUST NOT change between iterations within a single `process()` call
- This ensures deterministic wave construction and action emission

### Zero Timeout Validation (v1.0.4 Normative)

Validation of timeout values:
- `timeout_ms` MUST be >= 100 per schema (both step and workflow level)
- Any value <100 MUST raise `ModelOnexError` with code `VALIDATION_ERROR`
- This is structural validation (occurs at model creation, not execution)
- Zero or negative timeouts are rejected at the schema level

### Execution Mode Override (v1.0.4 Normative)

Behavior when input execution mode differs from workflow definition:
- `input_data.execution_mode` overrides `workflow_definition.execution_mode`
- Conflicts MUST NOT raise validation errors (override is intentional)
- If `input_data.execution_mode` is not set, use `workflow_definition.execution_mode`
- This allows runtime control over execution strategy

### Conditional Step Type Prohibition (v1.0.4 Normative)

Prohibition of conditional step type in v1.0:
- `step_type="conditional"` MUST raise `ModelOnexError` with code `VALIDATION_ERROR` in v1.0
- Conditional nodes are reserved for v1.1 when expression evaluation is supported
- This is distinct from `execution_mode=CONDITIONAL` (also prohibited in v1.0)
- The "conditional" step_type indicates a step that evaluates conditions to determine next steps

### Step Type Normalization (v1.0.4 Normative)

Step type validation follows strict rules:
- `step_type` MUST be one of: `compute`, `effect`, `reducer`, `orchestrator`, `custom`, `parallel`
- Any other value MUST raise `ModelOnexError` with code `VALIDATION_ERROR` at validation time
- Executor MUST NOT coerce unknown values to "custom" or any other default
- This ensures strict contract conformance and prevents silent type mismatches

### parallel_group Opaque Metadata (v1.0.4 Normative)

The `parallel_group` field is purely opaque metadata:
- `parallel_group` is a pure opaque label with no structural semantics
- No prefix, suffix, numeric pattern, or hierarchy MAY be interpreted from the value
- Only strict string equality MAY be used when comparing two `parallel_group` values
- Executor MUST NOT derive batching, ordering, or structure from `parallel_group`
- This ensures implementations do not create implicit coupling to naming conventions

### continue_on_error vs error_action Precedence (v1.0.4 Normative)

Error handling precedence between `continue_on_error` and `error_action`:
- `error_action` controls execution behavior exclusively
- `continue_on_error` is advisory in v1.0 and MUST NOT override `error_action`
- If both are present on a step, `error_action` determines the execution semantics
- This ensures unambiguous error handling behavior

### Deterministic Validation Error Ordering (v1.0.4 Normative)

Validation errors MUST be reported in deterministic order:
- Validation errors MUST be reported in contract declaration order:
  1. Step-structural errors in declaration order
  2. Dependency errors in declaration order
  3. Cycle errors last
- Implementations MAY include additional errors but MUST preserve this ordering
- This ensures consistent error messages across runs and implementations

### workflow_metadata.execution_mode Advisory Only (v1.0.4 Normative)

The `workflow_metadata.execution_mode` field precedence:
- `workflow_metadata.execution_mode` is advisory ONLY
- Precedence (highest to lowest):
  1. `input_data.execution_mode` (highest priority)
  2. `workflow_definition.workflow_metadata.execution_mode` (fallback)
- Executor MUST NOT use `workflow_metadata.execution_mode` directly if `input_data.execution_mode` is present
- This allows runtime override of workflow defaults

### global_timeout_ms vs step timeout_ms (v1.0.4 Normative)

Interaction between global and step-level timeouts:
- `global_timeout_ms` bounds total workflow duration ONLY
- `global_timeout_ms` MUST NOT clamp, override, or reduce any `step.timeout_ms`
- If global timeout elapses mid-step, the step is assumed FAILED
- Step timeout evaluation is otherwise independent of global timeout
- This ensures step timeout semantics are preserved regardless of workflow timeout

### step_outputs JSON Serialization (v1.0.4 Normative)

Type requirements for `step_outputs`:
- `step_outputs` MUST contain only JSON-serializable structures: dict, list, str, int, float, bool, null
- Non-serializable values MUST raise `ModelOnexError` during output construction
- Executor MUST NOT store arbitrary Python objects in `step_outputs`
- This ensures step outputs can be safely serialized for persistence and transmission

### Duplicate step_name Allowed (v1.0.4 Normative)

Step name uniqueness policy:
- Duplicate `step_name` values are permitted within a workflow
- Orchestrator MUST NOT use `step_name` as any form of unique identifier
- Only `step_id` and `correlation_id` MAY be used for identity operations
- Consumers MUST NOT assume uniqueness of `step_name`
- This allows descriptive naming without identity constraints

### skipped_steps Ordering (v1.0.4 Normative)

Ordering requirements for `skipped_steps`:
- `skipped_steps` MUST appear in the original contract declaration order
- Disabled steps MUST NOT be reordered based on dependency resolution
- This ensures deterministic and predictable reporting of skipped steps

### Cross-Step Mutation Prohibition (v1.0.4 Normative)

Mutation prohibition for subcontract models:
- Executor MUST NOT mutate any nested object inside:
  - `ModelWorkflowStep`
  - `ModelWorkflowDefinition`
  - `ModelCoordinationRules`
- Any structure requiring mutation MUST be deep-copied first
- Implementations MUST avoid side effects through shared references
- This ensures model integrity across concurrent operations

### Wave Boundary Internal Only (v1.0.4 Normative)

Wave structure visibility restrictions:
- Wave boundaries MUST NOT appear in:
  - `actions_emitted` metadata
  - `step_outputs`
  - orchestrator output metadata
  - error structures
- Wave structure MUST remain entirely internal to the orchestrator implementation
- This prevents consumers from depending on internal scheduling details

### order_index Action Creation Prohibition (v1.0.4 Normative)

Restrictions on `order_index` influence:
- `order_index` MUST NOT influence:
  - `action_id` generation
  - action priority
  - dependency mapping
  - creation ordering of actions within a wave
- `order_index` is metadata-only and MUST NOT appear in `action.payload`
- This ensures `order_index` remains purely informational

### Contract Loader Determinism (v1.0.5 Normative)

Contract loading MUST guarantee deterministic behavior:
- YAML loader MUST preserve declaration order exactly as written
- Contract loader MUST NOT sort or normalize lists of steps
- Validation tests MUST load from YAML to confirm tie-breaking and step ordering
- Python 3.7+ dict insertion order preservation is REQUIRED
- Any loader that reorders steps is non-conforming

This ensures that the same YAML contract produces identical step ordering across all executions and environments.

### Reserved Fields Governance (v1.0.5 Normative)

Reserved fields have strict governance rules in v1.0:
- Reserved fields MUST NOT be validated beyond structural type checking
- Reserved fields MUST NOT be interpreted or influence any runtime decision
- Reserved fields MUST NOT be logged (except at DEBUG level for troubleshooting)
- Reserved fields MUST be preserved in round-trip serialization
- Reserved fields include: `execution_graph`, `ModelWorkflowNode`, branch conditions, saga fields, compensation fields

**Rationale**: Reserved fields exist for forward compatibility. Validating or interpreting them in v1.0 creates implicit contracts that may conflict with their intended v1.1+ semantics.

### Schema Generation Direction (v1.0.5 Normative)

Schema generation follows a strict one-directional flow:
- JSON Schema/YAML schemas in omnibase_spi MUST be generated FROM `ModelWorkflowDefinition` in omnibase_core
- Schemas MUST NOT be manually authored
- No SPI-generated artifacts may be imported back into Core
- Schema generation is one-directional: Core -> SPI

**Architectural Invariant**: Core defines the source of truth. SPI generates artifacts from Core. Infra consumes both.

### Example Contract Location (v1.0.5 Normative)

Example workflow contracts have restricted placement:
- Example workflow contracts MUST NOT reside in omnibase_core
- Examples belong in: `docs/orchestrator_examples/` OR `omnibase_infra/examples/`
- Core repo contains only runtime logic
- Test fixtures in Core SHOULD be minimal and focused on validation, not demonstration

**Rationale**: Keeping Core free of example artifacts reduces repository clutter and ensures clear separation between runtime code and documentation.

### Synchronous Execution in v1.0 (v1.0.5 Normative)

v1.0 execution model has specific async/sync constraints:
- `execute_workflow` MUST use async signature for API compatibility
- v1.0 execution MUST be synchronous within the async context
- Parallel waves are represented logically as metadata only
- Actual concurrency is deferred to omnibase_infra in future versions

**Note**: The async signature exists to enable non-breaking addition of actual concurrency in v1.1+. v1.0 implementations MUST NOT introduce parallelism beyond wave metadata representation.

### Step Type Routing Only (v1.0.5 Normative)

The `step_type` field has limited semantics in v1.0:
- `step_type` determines action routing target only
- `step_type` MUST NOT change executor semantics in v1.0
- Exception: `step_type="conditional"` MUST be rejected with `ModelOnexError`

Valid step types for routing: `compute`, `effect`, `reducer`, `orchestrator`, `custom`, `parallel`

**Rationale**: Step type indicates WHERE an action should be routed, not HOW it should be executed. Execution semantics come from the target node, not the orchestrator.

---

## Design Principles

These principles apply to v1.0 and all future versions:

1. **Pure Workflow Executor**: The `execute_workflow()` function produces `(result, actions[])` without executing side effects
2. **YAML-Driven**: Workflows defined declaratively in contracts - zero custom Python code required
3. **Action Emission**: Side effects declared as Actions for target nodes to execute
4. **Typed Boundaries**: All public surfaces use Pydantic models (no dict coercion at runtime)
5. **Dependency-Aware**: Topological ordering ensures correct processing sequence
6. **Parallel-Ready**: Wave-based parallel processing for independent steps

---

## Purity Boundary (v1.0.5 Normative)

This section defines the **exact and non-negotiable** boundary where purity is guaranteed. Implementations that diverge from these rules are non-conforming.

### What IS Pure

The **workflow executor functions** are pure and MUST remain pure:

```python
async def execute_workflow(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
    execution_mode: EnumExecutionMode | None = None,
) -> WorkflowExecutionResult:
    """
    Pure function: same inputs always produce same outputs.
    No side effects. No shared state. Thread-safe.
    """
```

Pure functions:
- Take all state as explicit parameters
- Produce results without side effects
- Do not touch any shared/global state
- Same inputs -> same outputs, deterministically

This is the **only place** where the "pure orchestrator" story is allowed to live.

### What Is NOT Pure

`NodeOrchestrator` is **not pure** and MUST NEVER be described as such:

```python
class NodeOrchestrator:
    """
    NOT PURE: Maintains internal mutable state.
    The effective signature is:

        process(self, input) -> output  # self contains hidden state
    """
    workflow_definition: ModelWorkflowDefinition | None  # Internal mutable state
```

**Normative Rule**:
- Implementations MUST treat `NodeOrchestrator` as a **stateful facade over a pure workflow execution core**.
- No code, tests, or documentation may assume `NodeOrchestrator.process` is pure.

### Deriving Pure Semantics from Impure API

The conceptual pure orchestrator:

```text
execute_workflow(definition, steps, workflow_id) -> (result, actions[])
```

Is derived from the concrete API as follows:

| Conceptual | Concrete Source |
|------------|-----------------|
| `definition` (input) | `self.workflow_definition` (injected by container/dispatcher as `ModelWorkflowDefinition`) |
| `steps` (input) | `input_data.steps` as `list[ModelWorkflowStep]` (fully typed Pydantic models) |
| `workflow_id` (input) | `input_data.workflow_id` |
| `result` (output) | `output.execution_status`, `output.completed_steps`, `output.skipped_steps`, etc. |
| `actions` (output) | `output.actions_emitted` |

**v1.0.2 Note**: `WorkflowExecutionResult` (pure executor output) is transformed to `ModelOrchestratorOutput` (facade output). The facade output MUST contain only data derivable from the pure result.

### Recommended Usage Patterns

Treat the pure workflow executor and NodeOrchestrator as **two different tools**.

**Pattern A: Pure Functions (Testing / Deterministic Pipelines)**

```python
from omnibase_core.utils.util_workflow_executor import execute_workflow

# Explicitly pass all state - fully pure
result = await execute_workflow(
    workflow_definition,
    workflow_steps,
    workflow_id,
    execution_mode=EnumExecutionMode.SEQUENTIAL,
)
```

**Pattern B: Instance per Request (Simple Services)**

```python
# Create fresh instance per request - no shared state concerns
async def handle_request(request):
    orchestrator = NodeOrchestrator(container)
    orchestrator.workflow_definition = workflow_def  # Injected, not loaded from contract
    return await orchestrator.process(input_data)
```

**Pattern C: External Workflow Store (Distributed Systems) - DEFAULT MENTAL MODEL**

```python
# Workflow definition stored externally, orchestrator is stateless adapter
async def handle_request(request, workflow_store):
    workflow_def = await workflow_store.get_definition(workflow_name)
    result = await execute_workflow(
        workflow_def,
        workflow_steps,
        workflow_id,
    )
    await workflow_store.record_result(workflow_id, result)
    return result
```

**Going forward, unless explicitly stated otherwise, Pattern C is the default mental model.**

---

## Repository Boundaries (v1.0.5 Informative)

The ONEX architecture uses a layered repository structure:

```text
omnibase_spi --> omnibase_core --> omnibase_infra
```

### Layer Responsibilities

| Repository | Responsibility | Dependency Direction |
|------------|----------------|---------------------|
| **omnibase_spi** | Protocol models + contract schema definitions | Never depends on Core |
| **omnibase_core** | Node implementations (Orchestrator, Reducer, etc.) | Never depends on Infra |
| **omnibase_infra** | Contract loading + routing + dispatch | Depends on Core and SPI |

### Implications for NodeOrchestrator

- **SPI**: Defines `ModelWorkflowStep`, `ModelWorkflowDefinition`, contract YAML schema
- **Core**: Implements `NodeOrchestrator`, `execute_workflow()`, validation algorithms
- **Infra**: Loads YAML contracts, resolves to typed models, injects into NodeOrchestrator

**Key Rule**: NodeOrchestrator (Core) receives fully-typed `ModelWorkflowStep` instances. It MUST NOT perform YAML parsing or dict-to-model coercion - that is Infra's responsibility.

---

## v1.0 Scope

### What's IN v1.0

| Feature | Description |
|---------|-------------|
| **Workflow Coordination** | Coordinate multi-step workflows with dependency resolution |
| **Sequential Mode** | Process steps one-by-one in topological order |
| **Parallel Mode** | Process independent steps in waves concurrently |
| **Batch Mode** | Process with batch metadata tracking |
| **Action Emission** | Emit actions for target nodes to execute |
| **Dependency Resolution** | Topological ordering via Kahn's algorithm |
| **Cycle Detection** | DFS-based cycle detection before processing |
| **Step Disabling** | Skip disabled steps without failure |
| **Failure Handling** | fail_fast, continue_on_error, error_action per step |
| **Lease Semantics** | lease_id and epoch on all emitted actions |
| **Timeout Configuration** | Per-step and global workflow timeouts |

### What's NOT in v1.0

| Feature | Deferred To | Rationale |
|---------|-------------|-----------|
| **Saga Patterns** | v1.1 | Compensation logic needs careful design |
| **Distributed Locks** | v1.2 | Requires distributed coordination primitives |
| **Complex Compensation** | v1.2 | Rollback/undo semantics add complexity |
| **Conditional Branching** | v1.1 | Expression-based routing requires condition language |
| **Streaming Mode** | v1.2 | Real-time processing needs streaming infrastructure |
| **Checkpoint/Resume** | v1.1 | Workflow persistence and recovery |
| **Sub-workflows** | v1.2 | Nested workflow invocation |
| **Real-time Coordination** | v1.3 | Multi-instance workflow synchronization |

---

## Reserved Fields (v1.0)

The following fields are **defined in models for forward-compatibility** but are **ignored by the v1.0 executor**. Do not rely on their behavior until the specified version.

### ModelWorkflowDefinition Reserved Fields

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `compensation_enabled` | `bool` | `False` | v1.2 |
| `saga_pattern` | `str \| None` | `None` | v1.2 |
| `checkpoint_enabled` | `bool` | `False` | v1.1 |

### ModelCoordinationRules Reserved Fields

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `synchronization_points` | `list[str]` | `[]` | v1.1 |
| `max_retries` | `int` | `3` | v1.1 |
| `retry_delay_ms` | `int` | `1000` | v1.1 |

### ModelWorkflowStep Reserved Fields

| Field | Type | Default | Implemented In |
|-------|------|---------|----------------|
| `compensation_action` | `str \| None` | `None` | v1.2 |
| `checkpoint_required` | `bool` | `False` | v1.1 |
| `idempotency_key` | `str \| None` | `None` | v1.1 |

### EnumExecutionMode Reserved Values

| Value | Implemented In | v1.0 Behavior |
|-------|----------------|---------------|
| `CONDITIONAL` | v1.1 | MUST raise `ModelOnexError` |
| `STREAMING` | v1.2 | MUST raise `ModelOnexError` |

**Implementation Note**: These fields are present to allow contracts to be written with future capabilities in mind. The v1.0 executor will accept contracts containing these fields but will not execute their associated logic. However, `CONDITIONAL` and `STREAMING` execution modes MUST be rejected at validation time.

---

## Core Models

### ModelOrchestratorInput

```python
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.orchestrator.model_workflow_step import ModelWorkflowStep


class ModelOrchestratorInput(BaseModel):
    """
    Input model for NodeOrchestrator operations.

    Strongly typed input wrapper for workflow coordination with comprehensive
    configuration for execution modes, parallelism, timeouts, and failure
    handling. Used by NodeOrchestrator to coordinate multi-step workflows.

    v1.0.2 Note: Steps MUST be typed ModelWorkflowStep instances.
    YAML is compiled into typed Pydantic models upstream during contract load by SPI/Infra.
    Core receives fully typed models. Core does NOT parse YAML. Core does NOT coerce dicts into models.

    Thread Safety:
        Mutable by default. If thread-safety is needed, create the instance
        with all required values and treat as read-only after creation.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=False,
    )

    workflow_id: UUID = Field(..., description="Unique workflow identifier")

    steps: list[ModelWorkflowStep] = Field(
        ..., description="Fully typed ModelWorkflowStep instances"
    )

    operation_id: UUID = Field(
        default_factory=uuid4, description="Unique operation identifier"
    )

    execution_mode: EnumExecutionMode = Field(
        default=EnumExecutionMode.SEQUENTIAL,
        description="Execution mode for workflow"
    )

    max_parallel_steps: int = Field(
        default=5, description="Maximum number of parallel steps"
    )

    global_timeout_ms: int = Field(
        default=300000, description="Global workflow timeout (5 minutes default)"
    )

    failure_strategy: str = Field(
        default="fail_fast", description="Strategy for handling failures"
    )

    load_balancing_enabled: bool = Field(
        default=False, description="Enable load balancing for operations"
    )

    dependency_resolution_enabled: bool = Field(
        default=True, description="Enable automatic dependency resolution"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional workflow metadata"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now, description="Workflow creation timestamp"
    )
```

### ModelOrchestratorOutput

```python
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.services.model_custom_fields import ModelCustomFields


class ModelOrchestratorOutput(BaseModel):
    """
    Type-safe orchestrator output.

    Provides structured output storage for orchestrator execution
    results with type safety and validation.

    v1.0.2 Note: This model contains only data derivable from
    WorkflowExecutionResult (pure executor output). The transformation
    is: WorkflowExecutionResult -> ModelOrchestratorOutput.

    Important (v1.0.2 Normative):
        v1.0 MUST set both start_time and end_time to identical value (completion timestamp).
        v1.1 MAY begin real timing with actual start and end timestamps.
        For the actual execution duration, use execution_time_ms instead.
    """

    # Execution summary
    execution_status: str = Field(
        default=..., description="Overall execution status"
    )

    execution_time_ms: int = Field(
        default=...,
        description="Total execution time in milliseconds (use this for duration)",
    )

    start_time: str = Field(
        default=...,
        description="Execution timestamp (ISO format). v1.0.2 Normative: Set to completion "
        "timestamp (same as end_time). v1.1 MAY implement real timing.",
    )

    end_time: str = Field(
        default=...,
        description="Execution timestamp (ISO format). v1.0.2 Normative: Set to completion "
        "timestamp (same as start_time). v1.1 MAY implement real timing.",
    )

    # Step results
    completed_steps: list[str] = Field(
        default_factory=list,
        description="List of completed step IDs",
    )

    failed_steps: list[str] = Field(
        default_factory=list,
        description="List of failed step IDs",
    )

    skipped_steps: list[str] = Field(
        default_factory=list,
        description="List of skipped step IDs (disabled steps)",
    )

    # Step outputs (step_id -> output data)
    step_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Outputs from each step",
    )

    # Final outputs
    final_result: Any | None = Field(
        default=None, description="Final orchestration result"
    )

    output_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Output variables from the orchestration",
    )

    # Error information
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of errors (each with 'step_id', 'error_type', 'message')",
    )

    # Metrics
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics",
    )

    # Parallel execution tracking
    parallel_executions: int = Field(
        default=0,
        description="Number of parallel execution batches completed",
    )

    # Actions tracking
    actions_emitted: list[Any] = Field(
        default_factory=list,
        description="List of actions emitted during workflow processing",
    )

    # Custom outputs for extensibility
    custom_outputs: ModelCustomFields | None = Field(
        default=None,
        description="Custom output fields for orchestrator-specific data",
    )
```

### ModelAction

```python
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_execution import EnumActionType


class ModelAction(BaseModel):
    """
    Orchestrator-issued Action with lease management for single-writer semantics.

    Represents an Action emitted by the Orchestrator to Compute/Reducer/Effect nodes
    with single-writer semantics enforced via lease_id and epoch. The lease_id
    proves Orchestrator ownership, while epoch provides optimistic concurrency
    control through monotonically increasing version numbers.

    This model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access from multiple threads or async tasks. Unknown
    fields are rejected (extra='forbid') to ensure strict schema compliance.

    Key Differences from ModelIntent (NodeReducer):
        - ModelIntent: Passive side effect declaration for Effect nodes
        - ModelAction: Active workflow action with lease semantics for any target node

    v1.0.2 Note: The `dependencies` field references action_ids, NOT step_ids.
    When creating actions from steps, the orchestrator maps step dependencies
    to the corresponding action_ids.

    Thread Safety:
        Immutable (frozen=True) after creation. Note: shallow immutability -
        mutable nested data (dict/list contents) can still be modified.
        Use model_copy(deep=True) for full isolation.

    To modify a frozen instance, use model_copy():
        >>> modified = action.model_copy(update={"priority": 5, "retry_count": 1})
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
    )

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this action",
    )

    action_type: EnumActionType = Field(
        default=...,
        description="Type of action for execution routing",
    )

    target_node_type: str = Field(
        default=...,
        description="Target node type for action execution",
        min_length=1,
        max_length=100,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Action payload data",
    )

    dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of action IDs this action depends on (NOT step IDs)",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    timeout_ms: int = Field(
        default=30000,
        description="Execution timeout in milliseconds",
        ge=100,
        le=300000,  # Max 5 minutes
    )

    # Lease management fields for single-writer semantics
    lease_id: UUID = Field(
        default=...,
        description="Lease ID proving Orchestrator ownership",
    )

    epoch: int = Field(
        default=...,
        description="Monotonically increasing version number",
        ge=0,
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for action execution",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when action was created",
    )
```

### WorkflowExecutionResult

```python
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_workflow_execution import EnumWorkflowState
from omnibase_core.models.orchestrator.model_action import ModelAction


class WorkflowExecutionResult:
    """
    Result of workflow execution.

    Pure data structure containing workflow outcome and emitted actions
    for workflow coordination.

    v1.0.2 Note: This is the pure executor output. It is transformed to
    ModelOrchestratorOutput by the facade. OrchestratorOutput MUST contain
    only data derivable from this pure result.

    Thread Safety:
        Instances should be treated as effectively immutable after creation.
    """

    def __init__(
        self,
        workflow_id: UUID,
        execution_status: EnumWorkflowState,
        completed_steps: list[str],
        failed_steps: list[str],
        skipped_steps: list[str],
        actions_emitted: list[ModelAction],
        execution_time_ms: int,
        metadata: dict[str, Any] | None = None,
    ):
        self.workflow_id = workflow_id
        self.execution_status = execution_status
        self.completed_steps = completed_steps
        self.failed_steps = failed_steps
        self.skipped_steps = skipped_steps
        self.actions_emitted = actions_emitted
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.now(UTC).isoformat()
```

**Output Mapping Table (v1.0.2)**:

| WorkflowExecutionResult Field | ModelOrchestratorOutput Field |
|------------------------------|------------------------------|
| `workflow_id` | (included in metadata) |
| `execution_status` | `execution_status` |
| `completed_steps` | `completed_steps` |
| `failed_steps` | `failed_steps` |
| `skipped_steps` | `skipped_steps` |
| `actions_emitted` | `actions_emitted` |
| `execution_time_ms` | `execution_time_ms` |
| `metadata` | `metrics` (partial) |
| `timestamp` | `start_time`, `end_time` |

---

## Workflow Subcontract Models

### ModelWorkflowDefinition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_coordination_rules import ModelCoordinationRules
from .model_execution_graph import ModelExecutionGraph
from .model_workflow_definition_metadata import ModelWorkflowDefinitionMetadata


class ModelWorkflowDefinition(BaseModel):
    """
    Complete workflow definition.

    Comprehensive workflow definition providing metadata, execution graph,
    and coordination rules for ORCHESTRATOR nodes.

    VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    workflow_metadata: ModelWorkflowDefinitionMetadata = Field(
        default=...,
        description="Workflow metadata",
    )

    execution_graph: ModelExecutionGraph = Field(
        default=...,
        description="Execution graph for the workflow (v1.0.2 Note: Defined for "
        "contract generation only. Executor MUST NOT consult this field - "
        "v1.0 executor uses only steps + dependencies)",
    )

    coordination_rules: ModelCoordinationRules = Field(
        default_factory=lambda: ModelCoordinationRules(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Rules for workflow coordination",
    )
```

### ModelWorkflowDefinitionMetadata

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflowDefinitionMetadata(BaseModel):
    """
    Metadata for a workflow definition.

    Contains workflow identification, versioning, and execution configuration.
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
        "from_attributes": True,
    }

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    workflow_name: str = Field(
        default=...,
        description="Name of the workflow",
        min_length=1,
    )

    workflow_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the workflow (MUST be provided in YAML contract)",
    )

    description: str = Field(
        default=...,
        description="Description of the workflow",
    )

    execution_mode: str = Field(
        default="sequential",
        description="Execution mode: sequential, parallel, or batch (v1.0). "
        "conditional and streaming are reserved for future versions.",
    )

    timeout_ms: int = Field(
        default=600000,
        description="Workflow timeout in milliseconds",
        ge=1000,
    )
```

### ModelWorkflowStep

```python
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelWorkflowStep(BaseModel):
    """
    Strongly-typed workflow step definition.

    Replaces dict[str, str | int | bool] patterns with proper Pydantic model
    providing runtime validation and type safety for workflow execution.

    ZERO TOLERANCE: No Any types or dict[str, Any] patterns allowed.

    v1.0.2 Note: Steps MUST arrive as typed ModelWorkflowStep instances.
    YAML is compiled into typed Pydantic models upstream during contract load by SPI/Infra.
    Core receives fully typed models. Core does NOT parse YAML. Core does NOT coerce dicts into models.

    Thread Safety:
        Immutable (frozen=True) after creation.
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
        "frozen": True,
    }

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking workflow step across operations",
    )

    step_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this workflow step",
    )

    step_name: str = Field(
        default=...,
        description="Human-readable name for this step",
        min_length=1,
        max_length=200,
    )

    step_type: Literal[
        "compute",
        "effect",
        "reducer",
        "orchestrator",
        "conditional",
        "parallel",
        "custom",
    ] = Field(
        default=...,
        description="Type of workflow step execution",
    )

    # Execution configuration
    timeout_ms: int = Field(
        default=30000,
        description="Step execution timeout in milliseconds",
        ge=100,
        le=300000,  # Max 5 minutes
    )

    retry_count: int = Field(
        default=3,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    # Conditional execution
    enabled: bool = Field(
        default=True,
        description="Whether this step is enabled for execution",
    )

    skip_on_failure: bool = Field(
        default=False,
        description="Whether to skip this step if previous steps failed",
    )

    # Error handling
    continue_on_error: bool = Field(
        default=False,
        description="Whether to continue workflow if this step fails",
    )

    error_action: Literal["stop", "continue", "retry", "compensate"] = Field(
        default="stop",
        description="Action to take when step fails",
    )

    # Performance requirements
    max_memory_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in megabytes",
        ge=1,
        le=32768,  # Max 32GB
    )

    max_cpu_percent: int | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
        ge=1,
        le=100,
    )

    # Priority and ordering
    priority: int = Field(
        default=100,
        description="Step execution priority (higher = more priority). "
        "Authoring-time hint (1-1000). Clamped to 1-10 for action priority.",
        ge=1,
        le=1000,
    )

    order_index: int = Field(
        default=0,
        description="Order index for step execution sequence",
        ge=0,
    )

    # Dependencies
    depends_on: list[UUID] = Field(
        default_factory=list,
        description="List of step IDs this step depends on",
    )

    # Parallel execution
    parallel_group: str | None = Field(
        default=None,
        description="Group identifier for parallel execution",
        max_length=100,
    )

    max_parallel_instances: int = Field(
        default=1,
        description="Maximum parallel instances of this step",
        ge=1,
        le=100,
    )
```

### ModelCoordinationRules

```python
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCoordinationRules(BaseModel):
    """
    Rules for workflow coordination.

    Defines synchronization, parallelism, and failure recovery strategies
    for workflow execution.
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    synchronization_points: list[str] = Field(
        default_factory=list,
        description="Named synchronization points in the workflow",
    )

    parallel_execution_allowed: bool = Field(
        default=True,
        description="Whether parallel execution is allowed",
    )

    failure_recovery_strategy: EnumFailureRecoveryStrategy = Field(
        default=EnumFailureRecoveryStrategy.RETRY,
        description="Strategy for handling failures",
    )
```

### ModelExecutionGraph

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_workflow_node import ModelWorkflowNode


class ModelExecutionGraph(BaseModel):
    """
    Execution graph for a workflow.

    Defines the nodes (steps) and their relationships in the workflow
    execution DAG (Directed Acyclic Graph).

    v1.0.2 Note: Defined for contract generation only. Executor MUST NOT consult
    this field. The v1.0 executor uses only steps + dependencies from
    ModelOrchestratorInput, not the execution_graph structure.
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    nodes: list[ModelWorkflowNode] = Field(
        default_factory=list,
        description="Nodes in the execution graph",
    )
```

---

## Enums

### EnumExecutionMode

```python
from enum import Enum


class EnumExecutionMode(Enum):
    """Execution modes for workflow steps."""

    SEQUENTIAL = "sequential"    # Process steps one-by-one in order
    PARALLEL = "parallel"        # Process independent steps concurrently
    CONDITIONAL = "conditional"  # Reserved for v1.1 (MUST raise ModelOnexError in v1.0)
    BATCH = "batch"              # Process with batch metadata
    STREAMING = "streaming"      # Reserved for v1.2 (MUST raise ModelOnexError in v1.0)
```

### EnumActionType

```python
from enum import Enum


class EnumActionType(Enum):
    """Types of Actions for orchestrated execution."""

    COMPUTE = "compute"          # Action for NodeCompute
    EFFECT = "effect"            # Action for NodeEffect
    REDUCE = "reduce"            # Action for NodeReducer
    ORCHESTRATE = "orchestrate"  # Action for nested NodeOrchestrator
    CUSTOM = "custom"            # Custom action type
```

### EnumWorkflowState

```python
from enum import Enum


class EnumWorkflowState(Enum):
    """Workflow execution states."""

    PENDING = "pending"      # Workflow not yet started
    RUNNING = "running"      # Workflow currently processing
    PAUSED = "paused"        # Workflow paused (v1.1)
    COMPLETED = "completed"  # Workflow completed successfully
    FAILED = "failed"        # Workflow failed
    CANCELLED = "cancelled"  # Workflow cancelled
```

### EnumFailureRecoveryStrategy

```python
from enum import Enum


class EnumFailureRecoveryStrategy(str, Enum):
    """Failure recovery strategies."""

    RETRY = "RETRY"            # Retry failed step
    ROLLBACK = "ROLLBACK"      # Rollback to previous state (v1.2)
    COMPENSATE = "COMPENSATE"  # Execute compensation action (v1.2)
    ABORT = "ABORT"            # Abort entire workflow
```

### EnumBranchCondition

```python
from enum import Enum


class EnumBranchCondition(Enum):
    """Conditional branching types (v1.1+)."""

    IF_TRUE = "if_true"        # Branch if condition is true
    IF_FALSE = "if_false"      # Branch if condition is false
    IF_ERROR = "if_error"      # Branch if step errored
    IF_SUCCESS = "if_success"  # Branch if step succeeded
    IF_TIMEOUT = "if_timeout"  # Branch if step timed out
    CUSTOM = "custom"          # Custom condition expression
```

---

## Contract Validation Invariants

### Cycle Detection Algorithm

Workflow validation MUST detect cycles using DFS-based cycle detection:

```python
def _has_dependency_cycles(
    workflow_steps: list[ModelWorkflowStep],
) -> bool:
    """
    Check if workflow contains dependency cycles.

    Uses DFS-based cycle detection.

    Args:
        workflow_steps: Workflow steps to check

    Returns:
        True if cycles detected, False otherwise
    """
    # Build adjacency list
    step_ids = {step.step_id for step in workflow_steps}
    edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id in step_ids:
                # Note: dependency is reversed - we go FROM dependent TO dependency
                edges[step.step_id].append(dep_id)

    # DFS-based cycle detection
    visited: set[UUID] = set()
    rec_stack: set[UUID] = set()

    def has_cycle_dfs(node: UUID) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in edges.get(node, []):
            if neighbor not in visited:
                if has_cycle_dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for step_id in step_ids:
        if step_id not in visited:
            if has_cycle_dfs(step_id):
                return True

    return False
```

### Dependency Validation

Workflow validation MUST verify all dependencies exist:

```python
def _validate_dependencies(
    workflow_steps: list[ModelWorkflowStep],
) -> list[str]:
    """
    Validate all step dependencies reference existing steps.

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[str] = []
    step_ids = {step.step_id for step in workflow_steps}

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id not in step_ids:
                errors.append(
                    f"Step '{step.step_name}' depends on non-existent step: {dep_id}"
                )

    return errors
```

### Duplicate Step Detection

Workflow validation MUST reject duplicate step IDs:

```python
def _validate_unique_step_ids(
    workflow_steps: list[ModelWorkflowStep],
) -> list[str]:
    """
    Validate all step IDs are unique.

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[str] = []
    seen_ids: set[UUID] = set()

    for step in workflow_steps:
        if step.step_id in seen_ids:
            errors.append(f"Duplicate step ID: {step.step_id}")
        seen_ids.add(step.step_id)

    return errors
```

### Execution Mode Validation (v1.0.2)

Workflow validation MUST reject reserved execution modes:

```python
def _validate_execution_mode(
    execution_mode: EnumExecutionMode,
) -> None:
    """
    Validate execution mode is supported in v1.0.

    Raises:
        ModelOnexError: If execution mode is reserved (CONDITIONAL, STREAMING)
    """
    reserved_modes = {EnumExecutionMode.CONDITIONAL, EnumExecutionMode.STREAMING}

    if execution_mode in reserved_modes:
        raise ModelOnexError(
            message=f"Execution mode '{execution_mode.value}' is reserved for future "
            "versions and MUST NOT be used in v1.0",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={"execution_mode": execution_mode.value},
        )
```

### DAG Invariant for Disabled Steps (v1.0.2)

```python
def _validate_dag_with_disabled_steps(
    workflow_steps: list[ModelWorkflowStep],
) -> list[str]:
    """
    Validate workflow remains a valid DAG with disabled step handling.

    Disabled steps count as automatically satisfied dependencies.
    Disabled steps MUST NOT create hidden cycles.

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[str] = []

    # Check that disabling steps doesn't create hidden cycles
    enabled_steps = [s for s in workflow_steps if s.enabled]

    if _has_dependency_cycles(enabled_steps):
        errors.append(
            "Workflow contains cycles among enabled steps"
        )

    return errors
```

---

## Execution Model

### Workflow Processing Flow

```text
+--------------------------------------------------------------------------+
|                        WORKFLOW PROCESSING FLOW                           |
+--------------------------------------------------------------------------+
|                                                                          |
|  1. VALIDATION                                                           |
|     +---------+    +-------------+    +---------------+                 |
|     | Input   |--->| Validate    |--->| Check Cycles  |                 |
|     | Workflow|    | Definition  |    | (DFS)         |                 |
|     +---------+    +-------------+    +---------------+                 |
|                                              |                           |
|                                              v                           |
|  2. ORDERING                         +---------------+                  |
|     +----------------------------->  | Topological   |                  |
|     |                                | Sort (Kahn's) |                  |
|     |                                +---------------+                  |
|     |                                       |                           |
|     |                                       v                           |
|  3. PROCESSING (by mode)             +---------------+                  |
|     |                                | Select Mode   |                  |
|     |                                +---------------+                  |
|     |                                 /     |     \                     |
|     |                    +-----------+      |      +-----------+        |
|     |                    v                  v                  v        |
|     |             +----------+       +----------+       +----------+   |
|     |             |SEQUENTIAL|       | PARALLEL |       |  BATCH   |   |
|     |             | One by   |       |  Waves   |       | With     |   |
|     |             | one      |       |          |       | Metadata |   |
|     |             +----------+       +----------+       +----------+   |
|     |                    |                 |                  |         |
|     |                    +-----------------+------------------+         |
|     |                                      v                            |
|  4. ACTION CREATION                  +---------------+                  |
|     |                               | Create Action |                   |
|     |                               | per Step      |                   |
|     |                               +---------------+                   |
|     |                                      |                            |
|     |                                      v                            |
|  5. RESULT                          +---------------+                   |
|     +----------------------------->| Workflow      |                   |
|                                     | Result        |                   |
|                                     +---------------+                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Topological Ordering (Kahn's Algorithm)

```python
def _get_topological_order(
    workflow_steps: list[ModelWorkflowStep],
) -> list[UUID]:
    """
    Get topological ordering of steps based on dependencies.

    Uses Kahn's algorithm for topological sorting.

    Args:
        workflow_steps: Workflow steps to order

    Returns:
        List of step IDs in topological order
    """
    from collections import deque

    # Build adjacency list and in-degree map
    step_ids = {step.step_id for step in workflow_steps}
    edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}
    in_degree: dict[UUID, int] = dict.fromkeys(step_ids, 0)

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id in step_ids:
                edges[dep_id].append(step.step_id)
                in_degree[step.step_id] += 1

    # Kahn's algorithm - use deque for O(1) queue operations
    queue: deque[UUID] = deque(
        step_id for step_id, degree in in_degree.items() if degree == 0
    )
    result: list[UUID] = []

    while queue:
        node = queue.popleft()
        result.append(node)

        for neighbor in edges.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result
```

### Sequential Processing

In SEQUENTIAL mode, steps are processed one-by-one in topological order:

```text
Step A --> Step B --> Step C --> Step D
```

- Each step's action is created before moving to the next
- Dependencies are naturally satisfied
- Simplest processing model

### Parallel (Wave) Processing

In PARALLEL mode, independent steps are processed concurrently in waves:

```text
Wave 1: Step A ----------------------------------->
        Step B ----------------------------------->
        (no dependencies)

Wave 2: Step C ----------------------------------->
        Step D ----------------------------------->
        (depend on A or B)

Wave 3: Step E ----------------------------------->
        (depends on C and D)
```

- Steps with met dependencies are processed concurrently
- New wave starts when all steps in current wave complete
- Uses `asyncio.gather` for concurrent action creation

### Batch Processing

In BATCH mode, processing follows sequential order with batch metadata:

```text
Same as SEQUENTIAL, but with batch metadata tracking:
- batch_size
- execution_mode = "batch"
```

### Processing Rules

| Rule | Behavior |
|------|----------|
| Disabled steps | Skipped (no action created, added to `skipped_steps`) |
| Dependency not met | Step not eligible; workflow fails if cannot progress |
| Action creation fails | Step added to `failed_steps` |
| Downstream node reports failure | Step added to `failed_steps` |
| Step error with `error_action="stop"` | Workflow stops |
| Step error with `error_action="continue"` | Workflow continues |
| Cycle detected | Workflow fails immediately |
| Timeout exceeded | Step fails (v1.1: per-step timeout) |

---

## Action Pattern

### ModelAction vs ModelIntent

| Aspect | ModelIntent (NodeReducer) | ModelAction (NodeOrchestrator) |
|--------|---------------------------|-------------------------------|
| **Purpose** | Passive side effect declaration | Active workflow action |
| **Target** | Effect nodes only | Any node type |
| **Lease** | Optional (lease_id, epoch) | Required (lease_id, epoch) |
| **Semantics** | "Something should happen" | "Execute this with ownership" |
| **Concurrency** | No guarantees | Single-writer via lease |

### Action Types and Routing

```python
# Map step type to action type
action_type_map = {
    "compute": EnumActionType.COMPUTE,
    "effect": EnumActionType.EFFECT,
    "reducer": EnumActionType.REDUCE,
    "orchestrator": EnumActionType.ORCHESTRATE,
    "custom": EnumActionType.CUSTOM,
}

# Map step type to target node type
target_node_type_map = {
    "compute": "NodeCompute",
    "effect": "NodeEffect",
    "reducer": "NodeReducer",
    "orchestrator": "NodeOrchestrator",
    "custom": "NodeCustom",
}
```

### Action Creation (v1.0.2)

```python
def _create_action_for_step(
    step: ModelWorkflowStep,
    workflow_id: UUID,
    step_to_action_map: dict[UUID, UUID],
) -> ModelAction:
    """
    Create action for workflow step.

    v1.0.2 Note: This function creates an action from a typed ModelWorkflowStep.
    The step_to_action_map is used to map step dependencies to action_ids.

    Args:
        step: Fully typed ModelWorkflowStep instance
        workflow_id: Parent workflow ID
        step_to_action_map: Mapping from step_id to action_id for dependency resolution

    Returns:
        ModelAction for step execution
    """
    action_type = action_type_map.get(step.step_type, EnumActionType.CUSTOM)
    target_node_type = target_node_type_map.get(step.step_type, "NodeCustom")

    # Cap priority to ModelAction's max value of 10 (required, no warning)
    action_priority = min(step.priority, 10) if step.priority else 1

    # Generate action_id for this step
    action_id = uuid4()

    # Map step dependencies to action dependencies
    action_dependencies = [
        step_to_action_map[dep_id]
        for dep_id in step.depends_on
        if dep_id in step_to_action_map
    ]

    return ModelAction(
        action_id=action_id,
        action_type=action_type,
        target_node_type=target_node_type,
        payload={
            "workflow_id": str(workflow_id),
            "step_id": str(step.step_id),
            "step_name": step.step_name,
        },
        dependencies=action_dependencies,  # action_ids, NOT step_ids
        priority=action_priority,
        timeout_ms=step.timeout_ms,
        lease_id=uuid4(),  # New lease per action
        epoch=0,           # Initial epoch
        retry_count=step.retry_count,
        metadata={
            "step_name": step.step_name,
            "correlation_id": str(step.correlation_id),
        },
        created_at=datetime.now(),
    )
```

### Lease-Based Single-Writer Semantics

Every `ModelAction` includes lease management fields:

**lease_id**:
- UUID proving Orchestrator ownership
- New UUID generated for each action
- Target node SHOULD verify lease before execution

**epoch**:
- Monotonically increasing version number
- Starts at 0 for new actions
- Increment on retry or state change
- Target node SHOULD check epoch for conflict detection

**v1.0.2 Note**: v1.0 uses per-action leases. Each action has its own independent lease. v1.1 may introduce hierarchical leases (workflow lease -> action leases) for improved coordination.

**Usage Pattern**:

```python
# Orchestrator creates action with lease
action = ModelAction(
    action_type=EnumActionType.COMPUTE,
    target_node_type="NodeCompute",
    lease_id=uuid4(),  # Orchestrator-owned lease
    epoch=0,
    payload={"...": "..."},
)

# Target node (NodeCompute) receives action
async def execute_action(action: ModelAction):
    # Verify lease (implementation-specific)
    if not verify_lease(action.lease_id):
        raise LeaseExpiredError()

    # Check epoch for conflicts
    current_epoch = get_current_epoch(action.action_id)
    if action.epoch < current_epoch:
        raise EpochConflictError()

    # Execute action
    result = await do_work(action.payload)

    # Update epoch on success
    set_epoch(action.action_id, action.epoch + 1)
    return result
```

---

## Orchestrator Metadata Contract

The `ModelOrchestratorOutput.metrics` dict has the following requirements:

### Required Keys (v1.0.2)

| Key | Type | Description |
|-----|------|-------------|
| `actions_count` | `float` | Number of actions emitted |
| `completed_count` | `float` | Number of completed steps |
| `failed_count` | `float` | Number of failed steps |
| `skipped_count` | `float` | Number of skipped steps |

### Optional Keys

| Key | Type | Description |
|-----|------|-------------|
| `execution_mode` | `str` | Execution mode used |
| `workflow_name` | `str` | Workflow name from definition |
| `parallel_waves` | `float` | Number of parallel processing waves |

### Metadata Construction

```python
def _build_output_metrics(
    workflow_result: WorkflowExecutionResult,
) -> dict[str, float]:
    """
    Build output metrics from workflow result.

    Returns:
        Metrics dict with required keys
    """
    return {
        "actions_count": float(len(workflow_result.actions_emitted)),
        "completed_count": float(len(workflow_result.completed_steps)),
        "failed_count": float(len(workflow_result.failed_steps)),
        "skipped_count": float(len(workflow_result.skipped_steps)),
    }
```

---

## Error Model (v1.0.5)

### Error Hierarchy (v1.0.5 Normative)

Errors are categorized into three levels:

1. **Structural Validation Errors** (raise immediately at load time)
   - Invalid YAML syntax
   - Missing required fields
   - Type mismatches
   - These are handled by SPI during contract load, not by NodeOrchestrator

2. **Semantic Validation Errors** (raise immediately at validation time)
   - Dependency cycles detected
   - Invalid dependency references
   - Duplicate step IDs
   - Reserved execution modes (`CONDITIONAL`, `STREAMING`)
   - Empty workflow name
   - These MUST raise `ModelOnexError` with code `VALIDATION_ERROR`

3. **Execution-Time Errors** (return FAILED result, except hard stops)
   - Action creation fails
   - Downstream node reports failure
   - Dependencies not met and workflow cannot progress
   - Timeout exceeded
   - These return `WorkflowExecutionResult` with `FAILED` status

**Hard Stops** (raise even during execution):
- Unexpected system errors (out of memory, etc.)
- Invariant violations that indicate implementation bugs

### When to Raise ModelOnexError

`ModelOnexError` MUST be raised for:

| Condition | Error Code |
|-----------|------------|
| Workflow definition not loaded | `VALIDATION_ERROR` |
| Dependency cycle detected | `VALIDATION_ERROR` |
| Invalid workflow definition | `VALIDATION_ERROR` |
| Invalid step dependency reference | `VALIDATION_ERROR` |
| Empty workflow name | `VALIDATION_ERROR` |
| Reserved execution mode (`CONDITIONAL`, `STREAMING`) | `VALIDATION_ERROR` |

### When to Return Failed Result

A failed `WorkflowExecutionResult` (not exception) SHOULD be returned for:

| Condition | Result Status |
|-----------|---------------|
| Action creation failed | `EnumWorkflowState.FAILED` |
| Downstream node reported failure | `EnumWorkflowState.FAILED` |
| Timeout exceeded | `EnumWorkflowState.FAILED` |
| Dependencies not met (workflow cannot progress) | `EnumWorkflowState.FAILED` |
| Workflow cancelled | `EnumWorkflowState.CANCELLED` |

### Error Code Reference

```python
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Contract validation errors
raise ModelOnexError(
    message="Workflow definition not loaded",
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
)

# Cycle detection errors
raise ModelOnexError(
    message="Cannot compute execution order: workflow contains cycles",
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    context={},
)

# Workflow validation errors
raise ModelOnexError(
    message=f"Workflow validation failed: {', '.join(validation_errors)}",
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    context={"workflow_id": str(workflow_id), "errors": validation_errors},
)

# Reserved execution mode errors
raise ModelOnexError(
    message=f"Execution mode '{mode.value}' is reserved for future versions",
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    context={"execution_mode": mode.value},
)
```

### Error Handling in Processing

```python
try:
    # Create action for step
    action = _create_action_for_step(step, workflow_id, step_to_action_map)
    all_actions.append(action)
    step_to_action_map[step.step_id] = action.action_id
    completed_steps.append(str(step.step_id))
except ModelOnexError as e:
    # Handle expected ONEX errors
    failed_steps.append(str(step.step_id))
    logging.warning(
        f"Action creation for step '{step.step_name}' failed: {e.message}",
        extra={"error_code": e.error_code.value if e.error_code else None},
    )
    if step.error_action == "stop":
        break
except Exception as e:
    # Handle unexpected errors
    # Broad exception catch justified: action creation may involve external code
    failed_steps.append(str(step.step_id))
    logging.exception(f"Action creation for step '{step.step_name}' failed: {e}")
    if step.error_action == "stop":
        break
```

---

## v1.0 NodeOrchestrator Behavior

### Initialization

```python
class NodeOrchestrator(NodeCoreBase, MixinWorkflowExecution):
    """
    Workflow-driven orchestrator node for coordination.

    v1.0.2 Behavior:
        - workflow_definition MUST be injected by container/dispatcher, NOT loaded from self.contract
        - workflow_definition MUST be set before process() is called
        - workflow_definition MUST be treated as immutable once injected
        - process() receives typed ModelWorkflowStep instances (fully typed Pydantic models)
        - Delegates to pure execute_workflow() function
        - Converts WorkflowExecutionResult to ModelOrchestratorOutput
        - MUST NOT perform I/O or write to external systems
        - MUST NOT modify step metadata including correlation_id
    """

    workflow_definition: ModelWorkflowDefinition | None

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

        # Initialize workflow_definition to None
        # MUST be injected by container or dispatcher layer before process()
        # v1.0.2: NodeOrchestrator MUST NOT load from self.contract
        # v1.0.2: workflow_definition MUST be treated as immutable once injected
        object.__setattr__(self, "workflow_definition", None)
```

### Process Method

```python
async def process(
    self,
    input_data: ModelOrchestratorInput,
) -> ModelOrchestratorOutput:
    """
    Process workflow using workflow-driven coordination.

    Pure workflow pattern: Processes steps, emits actions for deferred execution.

    v1.0.2 Note: input_data.steps MUST be typed ModelWorkflowStep instances.
    Core receives fully typed models. Core does NOT parse YAML. Core does NOT coerce dicts into models.

    Args:
        input_data: Orchestrator input with typed workflow steps and configuration

    Returns:
        Orchestrator output with processing results and emitted actions

    Raises:
        ModelOnexError: If workflow definition not loaded, validation fails,
            or reserved execution mode is used
    """
    if not self.workflow_definition:
        raise ModelOnexError(
            message="Workflow definition not loaded",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    # Validate execution mode (v1.0.2: reject reserved modes)
    _validate_execution_mode(input_data.execution_mode)

    # input_data.steps is already list[ModelWorkflowStep] - fully typed Pydantic models
    workflow_steps = input_data.steps

    # Execute workflow from contract
    workflow_result = await self.execute_workflow_from_contract(
        self.workflow_definition,
        workflow_steps,
        input_data.workflow_id,
        execution_mode=input_data.execution_mode,
    )

    # Convert WorkflowExecutionResult to ModelOrchestratorOutput
    return self._convert_workflow_result_to_output(workflow_result)
```

### State Management

`NodeOrchestrator` maintains internal state via:
- `workflow_definition`: The workflow definition (injected, mutable)

**Normative Rules**:
- `workflow_definition` MUST be injected before `process()` is called
- `workflow_definition` MUST NOT be loaded from `self.contract` by NodeOrchestrator
- `workflow_definition` MAY be changed between `process()` calls
- Changing `workflow_definition` during `process()` is undefined behavior
- All other state MUST be passed through pure functions

### Lifecycle

```text
+---------------------+
|   Container Init    |--> Receives ModelONEXContainer
+---------+-----------+
          |
          v
+---------------------+
|  Definition Inject  |--> workflow_definition injected by container/dispatcher
+---------+-----------+    (NOT loaded from self.contract)
          |
          v
+---------------------+
|    Node Ready       |--> workflow_definition set, ready for processing
+---------+-----------+
          |
          v
+---------------------+
|     process()       |--> Validates, processes workflow, emits actions
+---------------------+
```

---

## Thread Safety and State Management

### Summary Table

| Component | Thread-Safe? | Notes |
|-----------|-------------|-------|
| `execute_workflow()` | Yes | Pure function |
| `validate_workflow_definition()` | Yes | Pure function |
| `get_execution_order()` | Yes | Pure function |
| `ModelAction` | Yes | Frozen after creation |
| `ModelWorkflowStep` | Yes | Frozen after creation |
| `ModelOrchestratorInput` | No | Mutable |
| `ModelOrchestratorOutput` | No | Mutable |
| `NodeOrchestrator` | No | Stateful facade |

### What IS Thread-Safe (by contract)

The following are **thread-safe by contract**:

1. **Workflow Executor Functions**: `execute_workflow`, `get_execution_order`, `validate_workflow_definition`.

2. **Immutable Models**:
   - `ModelAction` (frozen=True)
   - `ModelWorkflowStep` (frozen=True)
   - `WorkflowExecutionResult` (effectively immutable)

**Caveat**: Nested containers (`dict`, `list`) are still structurally mutable, so executors MUST NOT mutate them in-place.

### What Is NOT Thread-Safe

`NodeOrchestrator` instances are **NOT thread-safe**:

- They MUST NOT be shared across threads or async tasks without explicit synchronization.
- The spec does not require or guarantee any internal locking.

**Normative Rule**:

```text
v1.0 NodeOrchestrator instances MUST be treated as single-thread affinity objects.
```

If an implementation chooses to share an instance across threads, it MUST provide its own locking. That is an implementation detail; the protocol does not require or rely on it.

### Concurrent Access Patterns

**Safe**:
```python
# Different instances, different threads - SAFE
async def handle_request(request):
    orchestrator = NodeOrchestrator(container)
    orchestrator.workflow_definition = workflow_def
    return await orchestrator.process(input_data)
```

**Unsafe**:
```python
# Same instance, multiple threads - UNSAFE
shared_orchestrator = NodeOrchestrator(container)

async def handle_request(request):
    # Race condition on workflow_definition
    shared_orchestrator.workflow_definition = workflow_def
    return await shared_orchestrator.process(input_data)  # UNSAFE
```

**TODO(v1.1)**: Add thread-local workflow state or explicit state passing for thread-safe concurrent execution.

---

## Example Contracts

### Data Processing Pipeline

```yaml
workflow_coordination:
  workflow_definition:
    version:
      major: 1
      minor: 0
      patch: 0

    workflow_metadata:
      version:
        major: 1
        minor: 0
        patch: 0
      workflow_name: data_processing_pipeline
      workflow_version:
        major: 1
        minor: 0
        patch: 0
      description: "Multi-stage data processing workflow"
      execution_mode: parallel
      timeout_ms: 300000

    execution_graph:
      version:
        major: 1
        minor: 0
        patch: 0
      nodes:
        - node_id: "fetch_data"
          node_type: effect
          description: "Fetch data from external sources"
        - node_id: "validate_schema"
          node_type: compute
          description: "Validate data schema"
        - node_id: "enrich_data"
          node_type: compute
          description: "Enrich with additional fields"
        - node_id: "persist_results"
          node_type: effect
          description: "Save to database"

    coordination_rules:
      version:
        major: 1
        minor: 0
        patch: 0
      parallel_execution_allowed: true
      failure_recovery_strategy: RETRY
```

### Usage Example (v1.0.2 - Typed Steps)

```python
from uuid import uuid4
from omnibase_core.nodes import NodeOrchestrator
from omnibase_core.models.orchestrator import ModelOrchestratorInput, ModelWorkflowStep
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode

# Create orchestrator
orchestrator = NodeOrchestrator(container)
orchestrator.workflow_definition = workflow_definition  # Injected by container

# Define workflow steps using typed constructors (v1.0.2: fully typed Pydantic models)
fetch_step_id = uuid4()
validate_step_id = uuid4()
enrich_step_id = uuid4()
persist_step_id = uuid4()

workflow_steps = [
    ModelWorkflowStep(
        step_id=fetch_step_id,
        step_name="Fetch Data",
        step_type="effect",
        timeout_ms=10000,
    ),
    ModelWorkflowStep(
        step_id=validate_step_id,
        step_name="Validate Schema",
        step_type="compute",
        depends_on=[fetch_step_id],
        timeout_ms=5000,
    ),
    ModelWorkflowStep(
        step_id=enrich_step_id,
        step_name="Enrich Data",
        step_type="compute",
        depends_on=[validate_step_id],
        timeout_ms=15000,
    ),
    ModelWorkflowStep(
        step_id=persist_step_id,
        step_name="Persist Results",
        step_type="effect",
        depends_on=[enrich_step_id],
        timeout_ms=10000,
    ),
]

# Execute workflow with typed steps
input_data = ModelOrchestratorInput(
    workflow_id=uuid4(),
    steps=workflow_steps,  # list[ModelWorkflowStep] - fully typed Pydantic models
    execution_mode=EnumExecutionMode.SEQUENTIAL,
)

result = await orchestrator.process(input_data)

print(f"Status: {result.execution_status}")
print(f"Completed steps: {len(result.completed_steps)}")
print(f"Skipped steps: {len(result.skipped_steps)}")
print(f"Actions emitted: {len(result.actions_emitted)}")
print(f"Execution time: {result.execution_time_ms}ms")
```

### ETL Workflow with Parallel Stages (v1.0.2 - Typed Steps)

```yaml
workflow_coordination:
  workflow_definition:
    version:
      major: 1
      minor: 0
      patch: 0

    workflow_metadata:
      version:
        major: 1
        minor: 0
        patch: 0
      workflow_name: etl_pipeline
      workflow_version:
        major: 2
        minor: 1
        patch: 0
      description: "ETL pipeline with parallel extraction"
      execution_mode: parallel
      timeout_ms: 600000

    execution_graph:
      version:
        major: 1
        minor: 0
        patch: 0
      nodes:
        # Parallel extraction phase
        - node_id: "extract_source_a"
          node_type: effect
          description: "Extract from source A"
        - node_id: "extract_source_b"
          node_type: effect
          description: "Extract from source B"
        - node_id: "extract_source_c"
          node_type: effect
          description: "Extract from source C"

        # Transform phase (depends on all extracts)
        - node_id: "transform_merge"
          node_type: compute
          description: "Merge and transform data"

        # Load phase
        - node_id: "load_warehouse"
          node_type: effect
          description: "Load to data warehouse"

    coordination_rules:
      version:
        major: 1
        minor: 0
        patch: 0
      parallel_execution_allowed: true
      failure_recovery_strategy: ABORT
```

```python
# ETL with parallel extraction using typed ModelWorkflowStep constructors
extract_a_id = uuid4()
extract_b_id = uuid4()
extract_c_id = uuid4()
transform_id = uuid4()
load_id = uuid4()

workflow_steps = [
    # Parallel extraction (no dependencies)
    ModelWorkflowStep(
        step_id=extract_a_id,
        step_name="Extract Source A",
        step_type="effect",
        timeout_ms=60000,
    ),
    ModelWorkflowStep(
        step_id=extract_b_id,
        step_name="Extract Source B",
        step_type="effect",
        timeout_ms=60000,
    ),
    ModelWorkflowStep(
        step_id=extract_c_id,
        step_name="Extract Source C",
        step_type="effect",
        timeout_ms=60000,
    ),
    # Transform (depends on all extracts)
    ModelWorkflowStep(
        step_id=transform_id,
        step_name="Transform Merge",
        step_type="compute",
        depends_on=[extract_a_id, extract_b_id, extract_c_id],
        timeout_ms=120000,
    ),
    # Load (depends on transform)
    ModelWorkflowStep(
        step_id=load_id,
        step_name="Load Warehouse",
        step_type="effect",
        depends_on=[transform_id],
        timeout_ms=60000,
    ),
]

# Execute in parallel mode
# Wave 1: extract_a, extract_b, extract_c (concurrent)
# Wave 2: transform (after all extracts complete)
# Wave 3: load (after transform completes)
```

### Conditional Error Handling (v1.0.2 - Typed Steps)

```python
# Steps with different error handling using typed constructors
workflow_steps = [
    ModelWorkflowStep(
        step_id=uuid4(),
        step_name="Critical Step",
        step_type="compute",
        error_action="stop",  # Stop workflow on failure
        retry_count=3,
    ),
    ModelWorkflowStep(
        step_id=uuid4(),
        step_name="Optional Enrichment",
        step_type="compute",
        error_action="continue",  # Continue even if this fails
        continue_on_error=True,
    ),
    ModelWorkflowStep(
        step_id=uuid4(),
        step_name="Final Persist",
        step_type="effect",
        error_action="retry",  # Retry on failure
        retry_count=5,
    ),
]
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

- [ ] Implement `execute_workflow()` pure function
- [ ] Implement Kahn's algorithm for topological ordering
- [ ] Implement DFS cycle detection
- [ ] Implement `validate_workflow_definition()`
- [ ] Implement execution mode validation (reject CONDITIONAL, STREAMING)
- [ ] Create `WorkflowExecutionResult` dataclass with `skipped_steps`

### Phase 2: NodeOrchestrator Integration (Week 2-3)

- [ ] Implement `NodeOrchestrator.process()` method (no dict coercion)
- [ ] Implement `MixinWorkflowExecution`
- [ ] Remove automatic contract loading from `__init__`
- [ ] Implement `_convert_workflow_result_to_output()`

### Phase 3: Execution Modes (Week 3-4)

- [ ] Implement sequential processing
- [ ] Implement parallel (wave) processing
- [ ] Implement batch processing with metadata
- [ ] Implement error handling strategies

### Phase 4: Testing & Documentation (Week 4-5)

- [ ] Unit tests for pure functions (>90% coverage)
- [ ] Integration tests for NodeOrchestrator
- [ ] Contract validation tests
- [ ] Performance benchmarks
- [ ] Documentation and examples

---

## Acceptance Criteria

### Conformance Tests

A v1.0.2 conforming implementation MUST pass:

1. **Pure Function Tests**:
   - `execute_workflow` produces same output for same input
   - No shared state mutation
   - Thread-safe concurrent execution

2. **Cycle Detection Tests**:
   - Detect simple cycles (A -> B -> A)
   - Detect complex cycles (A -> B -> C -> A)
   - Accept valid DAGs
   - Detect cycles with disabled steps

3. **Topological Ordering Tests**:
   - Correct order for linear dependencies
   - Correct order for diamond dependencies
   - Correct order for multiple roots

4. **Execution Mode Tests**:
   - Sequential processes in order
   - Parallel processes independent steps concurrently
   - Batch includes metadata
   - CONDITIONAL raises ModelOnexError
   - STREAMING raises ModelOnexError

5. **Action Emission Tests**:
   - One action per completed step
   - Actions have valid lease_id and epoch
   - Action routing matches step type
   - Action dependencies use action_ids (not step_ids)

6. **Error Handling Tests**:
   - `ModelOnexError` for validation failures
   - Failed result for action creation failures
   - Correct `error_action` behavior

7. **Typed Input Tests**:
   - `input_data.steps` accepts `list[ModelWorkflowStep]`
   - No dict-to-model coercion in NodeOrchestrator

8. **Skipped Steps Tests**:
   - Disabled steps appear in `skipped_steps`
   - Disabled steps treated as satisfied dependencies

### Performance Requirements

| Metric | Requirement |
|--------|-------------|
| Validation time | < 100ms for 100 steps |
| Topological sort | < 50ms for 1000 steps |
| Action creation | < 10ms per action |
| Memory overhead | < 10KB per step |

---

## Glossary

| Term | Definition |
|------|------------|
| **Workflow Executor** | Pure functions (`execute_workflow`, etc.) that perform stateless workflow logic |
| **NodeOrchestrator** | Stateful facade class that wraps workflow executor and maintains workflow definition |
| **Action** | Declaration of work to be executed by a target node (NodeCompute, NodeEffect, etc.) |
| **Intent** | Declaration of a side effect for NodeReducer (compare with Action) |
| **Workflow Step** | Single unit of work in a workflow (ModelWorkflowStep) |
| **Processing Wave** | Set of steps with met dependencies that are processed concurrently in parallel mode |
| **Topological Order** | Dependency-respecting order for step processing |
| **Lease** | UUID proving Orchestrator ownership of an action |
| **Epoch** | Monotonically increasing version number for optimistic concurrency |
| **DAG** | Directed Acyclic Graph - the workflow dependency structure |
| **Kahn's Algorithm** | Algorithm for topological sorting |
| **DFS** | Depth-First Search - algorithm used for cycle detection |
| **Entity** | A single workflow instance; multi-workflow scenarios require external workflow management |
| **SPI** | Service Provider Interface - defines protocols and contract schemas |
| **Core** | Core implementation layer - contains node implementations |
| **Infra** | Infrastructure layer - handles contract loading, routing, dispatch |

---

## Changelog

### v1.0.5 (2025-12-10)

**Additional Normative Rules (Fixes 53-58)**:

53. **Fix 53**: Added "Contract Loader Determinism (v1.0.5 Normative)" rule. YAML loader MUST preserve declaration order exactly as written. Contract loader MUST NOT sort or normalize lists of steps. Validation tests MUST load from YAML to confirm tie-breaking and step ordering. Python 3.7+ dict insertion order preservation is REQUIRED.

54. **Fix 54**: Added "Reserved Fields Governance (v1.0.5 Normative)" rule. Reserved fields MUST NOT be validated beyond structural type checking. Reserved fields MUST NOT be interpreted or influence any runtime decision. Reserved fields MUST NOT be logged (except at DEBUG level). Reserved fields MUST be preserved in round-trip serialization.

55. **Fix 55**: Added "Schema Generation Direction (v1.0.5 Normative)" rule. JSON Schema/YAML schemas in omnibase_spi MUST be generated FROM ModelWorkflowDefinition in omnibase_core. Schemas MUST NOT be manually authored. No SPI-generated artifacts may be imported back into Core. Schema generation is one-directional: Core -> SPI.

56. **Fix 56**: Added "Example Contract Location (v1.0.5 Normative)" rule. Example workflow contracts MUST NOT reside in omnibase_core. Examples belong in: docs/orchestrator_examples/ OR omnibase_infra/examples/. Core repo contains only runtime logic.

57. **Fix 57**: Added "Synchronous Execution in v1.0 (v1.0.5 Normative)" rule. execute_workflow MUST use async signature for API compatibility. v1.0 execution MUST be synchronous within the async context. Parallel waves are represented logically as metadata only. Actual concurrency is deferred to omnibase_infra in future versions.

58. **Fix 58**: Added "Step Type Routing Only (v1.0.5 Normative)" rule. step_type determines action routing target only. step_type MUST NOT change executor semantics in v1.0. Exception: step_type="conditional" MUST be rejected with ModelOnexError.

### v1.0.4 (2025-12-10)

**Additional Normative Rules (Fixes 41-52)**:

41. **Fix 41**: Added "Step Type Normalization (v1.0.4 Normative)" rule. `step_type` MUST be one of: `compute`, `effect`, `reducer`, `orchestrator`, `custom`, `parallel`. Any other value MUST raise `ModelOnexError` at validation time. Executor MUST NOT coerce unknown values to "custom".

42. **Fix 42**: Added "parallel_group Opaque Metadata (v1.0.4 Normative)" rule. `parallel_group` is a pure opaque label. No prefix, suffix, numeric pattern, or hierarchy MAY be interpreted. Only strict string equality MAY be used for comparison. Executor MUST NOT derive batching, ordering, or structure from it.

43. **Fix 43**: Added "continue_on_error vs error_action Precedence (v1.0.4 Normative)" rule. `error_action` controls behavior exclusively. `continue_on_error` is advisory in v1.0 and MUST NOT override `error_action`. If both are present, `error_action` determines execution semantics.

44. **Fix 44**: Added "Deterministic Validation Error Ordering (v1.0.4 Normative)" rule. Validation errors MUST be reported in contract declaration order: step-structural errors first, dependency errors second, cycle errors last. Implementations MAY include additional errors but MUST preserve ordering.

45. **Fix 45**: Added "workflow_metadata.execution_mode Advisory Only (v1.0.4 Normative)" rule. `workflow_metadata.execution_mode` is advisory ONLY. Precedence: `input_data.execution_mode` (highest), then `workflow_definition.workflow_metadata.execution_mode` (fallback). Executor MUST NOT use workflow_metadata directly if input_data provides execution_mode.

46. **Fix 46**: Added "global_timeout_ms vs step timeout_ms (v1.0.4 Normative)" rule. `global_timeout_ms` bounds total workflow duration ONLY. It MUST NOT clamp, override, or reduce any `step.timeout_ms`. If global timeout elapses mid-step, the step is assumed FAILED. Step timeout evaluation is otherwise independent.

47. **Fix 47**: Added "step_outputs JSON Serialization (v1.0.4 Normative)" rule. `step_outputs` MUST contain only JSON-serializable structures: dict, list, str, int, float, bool, null. Non-serializable values MUST raise `ModelOnexError`. Executor MUST NOT store arbitrary Python objects.

48. **Fix 48**: Added "Duplicate step_name Allowed (v1.0.4 Normative)" rule. Duplicate `step_name` values are permitted. Orchestrator MUST NOT use `step_name` as any unique identifier. Only `step_id` and `correlation_id` MAY be used for identity. Consumers MUST NOT assume uniqueness.

49. **Fix 49**: Added "skipped_steps Ordering (v1.0.4 Normative)" rule. `skipped_steps` MUST appear in the original contract declaration order. Disabled steps MUST NOT be reordered based on dependency resolution. This ensures deterministic reporting.

50. **Fix 50**: Added "Cross-Step Mutation Prohibition (v1.0.4 Normative)" rule. Executor MUST NOT mutate any nested object inside `ModelWorkflowStep`, `ModelWorkflowDefinition`, or `ModelCoordinationRules`. Any structure requiring mutation MUST be deep-copied first. Implementations MUST avoid side effects through shared references.

51. **Fix 51**: Added "Wave Boundary Internal Only (v1.0.4 Normative)" rule. Wave boundaries MUST NOT appear in `actions_emitted` metadata, `step_outputs`, orchestrator output metadata, or error structures. Wave structure MUST remain entirely internal to the orchestrator.

52. **Fix 52**: Added "order_index Action Creation Prohibition (v1.0.4 Normative)" rule. `order_index` MUST NOT influence `action_id` generation, action priority, dependency mapping, or creation ordering of actions within a wave. `order_index` is metadata-only and MUST NOT appear in `action.payload`.

### v1.0.3 (2025-12-10)

**Additional Normative Rules (Fixes 21-40)**:

21. **Fix 21**: Added "Failure Strategy Precedence (v1.0.3 Normative)" rule. Step-level `error_action` takes precedence over workflow-level `failure_strategy`. Workflow-level strategy applies only when step-level error_action is not set.

22. **Fix 22**: Added "Partial Parallel-Wave Failure Continuation (v1.0.3 Normative)" rule. If any step in a wave fails with `error_action="stop"`, all remaining steps in the same wave MUST be skipped and workflow ends with FAILED state. If `error_action="continue"`, remaining steps may execute only if dependencies are met.

23. **Fix 23**: Added "Orphan Step Handling (v1.0.3 Normative)" rule. Steps with no dependency path from any root MUST still be executed. Orphan detection MUST NOT cause validation failure in v1.0.

24. **Fix 24**: Added "Dependency List Ordering (v1.0.3 Normative)" rule. Orchestrator MUST treat `depends_on` list as semantically unordered. During DAG construction, dependencies MUST be sorted by step declaration index.

25. **Fix 25**: Added "Action Metadata Immutability (v1.0.3 Normative)" rule. `Action.metadata` MUST be treated as immutable after action creation. Executor MUST NOT mutate metadata post-creation.

26. **Fix 26**: Added "parallel_group vs depends_on Precedence (v1.0.3 Normative)" rule. `parallel_group` MAY NOT override `depends_on`. If parallel_group conflicts with dependency ordering, dependency ordering wins.

27. **Fix 27**: Added "parallel_group Non-Semantic in v1.0 (v1.0.3 Normative)" rule. `parallel_group` is ignored in v1.0 except as metadata. Executor MUST NOT enforce group-based batching.

28. **Fix 28**: Added "Retry Count Semantics (v1.0.3 Normative)" rule. Retries do NOT produce new actions in v1.0. `retry_count` is advisory metadata only. v1.1 MAY introduce retry-action chains.

29. **Fix 29**: Added "Empty Workflow Handling (v1.0.3 Normative)" rule. Empty workflow (steps=[]) MUST succeed immediately with COMPLETED state. No actions emitted.

30. **Fix 30**: Added "Action Payload Type Requirements (v1.0.3 Normative)" rule. `Action.payload` MUST contain only JSON-serializable values. Non-serializable values cause `ModelOnexError` during action creation.

31. **Fix 31**: Added "Cross-Step correlation_id Consistency (v1.0.3 Normative)" rule. `correlation_id` MUST uniquely identify step lineage. Orchestrator MUST NOT generate or modify `correlation_id`. `correlation_id` MUST appear in `action.metadata` exactly as in step.

32. **Fix 32**: Added "order_index Non-Semantic (v1.0.3 Normative)" rule. `order_index` MUST NOT influence execution order in v1.0. If provided, `order_index` is metadata only.

33. **Fix 33**: Added "action_id Global Uniqueness (v1.0.3 Normative)" rule. Every `action_id` MUST be globally unique. Reuse of `action_id` is non-conforming.

34. **Fix 34**: Added "workflow_id vs operation_id Semantics (v1.0.3 Normative)" rule. `workflow_id` identifies a workflow instance. `operation_id` identifies a single invocation of `orchestrator.process()`. Multiple operations MAY share `workflow_id`.

35. **Fix 35**: Added "Global Timeout Mid-Wave Behavior (v1.0.3 Normative)" rule. If global timeout elapses, all unprocessed steps MUST be marked failed, steps in-progress MUST be assumed failed, workflow ends with FAILED state.

36. **Fix 36**: Added "Input Metadata Immutability (v1.0.3 Normative)" rule. `input_data.metadata` MUST NOT be mutated during `process()`. If additional metadata is required, copy and extend internally.

37. **Fix 37**: Added "Step Iteration Order Stability (v1.0.3 Normative)" rule. All iteration over `workflow_steps` MUST preserve original step order exactly as loaded.

38. **Fix 38**: Added "Zero Timeout Validation (v1.0.3 Normative)" rule. `timeout_ms` MUST be >= 100 per schema. Any value <100 MUST raise `ModelOnexError` (structural validation).

39. **Fix 39**: Added "Execution Mode Override (v1.0.3 Normative)" rule. `input_data.execution_mode` overrides `workflow_definition.execution_mode`. Conflicts MUST NOT raise validation errors.

40. **Fix 40**: Added "Conditional Step Type Prohibition (v1.0.3 Normative)" rule. `step_type="conditional"` MUST raise `ModelOnexError` in v1.0. Conditional nodes are reserved for v1.1.

### v1.0.2 (2025-12-10)

**Additional Normative Rules and Clarifications**:

1. **Fix 1**: Removed all implicit "workflow_definition as dict" language. Core receives fully typed Pydantic models from Infra. Core does NOT parse YAML. Core does NOT coerce dicts into models.

2. **Fix 2**: Updated "Conceptual Modes" section to explicitly state that steps MUST ALWAYS be `ModelWorkflowStep` instances and definitions MUST ALWAYS be `ModelWorkflowDefinition`.

3. **Fix 3**: Added "Workflow Definition Injection (v1.0.2 Normative)" rule. NodeOrchestrator MUST treat `workflow_definition` as immutable once injected. Reassignment during `process()` is undefined behavior.

4. **Fix 4**: Added "Execution Graph Prohibition (v1.0.2 Normative)" rule. Executor MUST NOT consult `execution_graph` even if present. Executor MUST NOT check for equivalence between graph and step list. Executor MUST NOT log warnings if they disagree.

5. **Fix 5**: Added "Topological Ordering Tiebreaker (v1.0.2 Normative)" rule. If multiple steps have in-degree 0 at a given wave, order MUST follow contract declaration order.

6. **Fix 6**: Clarified step priority clamping applies to all modes. Added explicit statement that batch mode MUST clamp step priority to action priority exactly as in sequential and parallel modes.

7. **Fix 7**: Added "Skip on Failure Semantics (v1.0.2 Normative)" rule. `skip_on_failure` applies ONLY to failures of earlier steps. `skip_on_failure` does NOT override unmet dependency constraints. Unmet dependencies ALWAYS block execution.

8. **Fix 8**: Added "Epoch Increment Responsibility (v1.0.2 Normative)" rule. Orchestrator sets `epoch=0` for all new actions. Target node increments epoch after each successful execution. Orchestrator MUST NOT increment epoch.

9. **Fix 9**: Strengthened saga field handling. Replaced "SHOULD log warning" with "Saga-related fields MUST be ignored and MUST NOT influence control flow".

10. **Fix 10**: Added "Disabled Step Forward Compatibility (v1.0.2 Normative)" rule. v1.0 MUST treat disabled steps as automatically satisfied, even if they would be invalid in stricter future versions.

11. **Fix 11**: Added "Action Emission Wave Ordering (v1.0.2 Normative)" rule. Within a wave, actions MUST appear in YAML order. Across waves, actions MUST appear in wave order. All actions in wave N are emitted before any action in wave N+1.

12. **Fix 12**: Added "Action Creation Exception Handling (v1.0.2 Normative)" rule. Only `ModelOnexError` MAY be raised intentionally. All other exceptions MUST be caught and converted into FAILED steps.

13. **Fix 13**: Formalized `start_time`/`end_time` behavior as normative. v1.0 MUST set both to identical value (completion timestamp). v1.1 MAY begin real timing.

14. **Fix 14**: Added "Metadata Isolation (v1.0.2 Normative)" rule. `WorkflowExecutionResult.metadata` MUST NOT include orchestrator-internal fields. Prohibited: `step_to_action_map`, execution waves, dependency graph structures.

15. **Fix 15**: Added "UUID Stability (v1.0.2 Normative)" rule. UUID generation for steps comes from contract load, not execution. Orchestrator MUST NOT generate `step_id` values. `step_id` values are immutable once loaded.

16. **Fix 16**: Added "Expression Evaluation Prohibition (v1.0.2 Normative)" rule. v1.0 MUST NOT parse or evaluate any conditional expressions in contracts. Expression evaluation engine is reserved for v1.1.

17. **Fix 17**: Added "Step Metadata Immutability (v1.0.2 Normative)" rule. NodeOrchestrator MUST NOT modify `ModelWorkflowStep` metadata, including `correlation_id`. Metadata and correlation fields MUST NOT be altered during processing.

18. **Fix 18**: Added "Wave Boundary Guarantee" to Action Emission Wave Ordering. All actions in wave N are emitted before any action in wave N+1. This guarantees deterministic action ordering.

19. **Fix 19**: Added "Load Balancing Prohibition (v1.0.2 Normative)" rule. v1.0 MUST ignore `load_balancing_enabled` entirely. Load balancing logic MUST NOT exist inside Orchestrator.

20. **Fix 20**: Added "Validation Phase Separation (v1.0.2 Normative)" rule. Pure executor assumes `workflow_definition` is already valid. Validation happens BEFORE execution, not during. Executor MUST NOT re-validate `workflow_definition`.

### v1.0.1 (2025-12-10)

**Structural and Semantic Corrections**:

1. **Fix 1**: Removed dict->model coercion language. Steps MUST arrive as typed `ModelWorkflowStep` instances. Updated `ModelOrchestratorInput.steps` type from `list[dict[str, Any]]` to `list[ModelWorkflowStep]`.

2. **Fix 2**: Added "Contract Loading Responsibility" normative rule. NodeOrchestrator MUST NOT load `workflow_definition` from `self.contract`. Contract resolution occurs at container build time.

3. **Fix 3**: Marked `ModelExecutionGraph` as not used in v1.0 execution semantics. Added note: "Defined for contract generation; not referenced in v1.0 execution semantics."

4. **Fix 4**: Added "Subcontract Model Immutability" normative rule. Orchestrator MUST treat all subcontract models as immutable values.

5. **Fix 5**: Clarified stateful vs stateless semantics. v1.0 NodeOrchestrator is stateful ONLY for `workflow_definition`. All other state MUST be passed through pure functions.

6. **Fix 6**: Clarified step priority vs action priority. Step priority (1-1000) is authoring-time hint. Action priority (1-10) is execution-time constraint. Clamping is REQUIRED and MUST NOT emit warnings.

7. **Fix 7**: Added "Error Hierarchy" section with three levels: structural validation errors, semantic validation errors, and execution-time errors.

8. **Fix 8**: Replaced "execute step" language with "create action for step". Orchestrator issues actions; nodes execute.

9. **Fix 9**: Clarified lease semantics. v1.0 uses per-action leases. Added note about v1.1 potentially introducing hierarchical leases.

10. **Fix 10**: Replaced dict-based examples with typed `ModelWorkflowStep(...)` constructors throughout Example Contracts section.

11. **Fix 11**: Added "Repository Boundaries" informative section describing SPI -> Core -> Infra layering.

12. **Fix 12**: Updated "Reserved Fields Global Rule" to clarify: parsed by SPI, preserved by Core, ignored by executor deterministically.

13. **Fix 13**: Removed "accept with warning" for CONDITIONAL/STREAMING. These modes MUST raise `ModelOnexError` in v1.0.

14. **Fix 14**: Added WorkflowExecutionResult -> ModelOrchestratorOutput transformation note. OrchestratorOutput MUST contain only data derivable from the pure result.

15. **Fix 15**: Added "Side Effect Prohibition" normative rule. Orchestrator MUST NOT write to external systems directly.

16. **Fix 16**: Clarified `ModelAction.dependencies` references action_ids, NOT step_ids. Updated action creation to include step-to-action mapping.

17. **Fix 17**: Added `skipped_steps` to `WorkflowExecutionResult` and output mapping table.

18. **Fix 18**: Execution mode validation now explicitly rejects CONDITIONAL and STREAMING with `ModelOnexError`.

19. **Fix 19**: Added "Dependency Failure Semantics" normative rule. Workflow fails deterministically if cannot progress.

20. **Fix 20**: Added "DAG Invariant for Disabled Steps" normative rule. Disabled steps MUST NOT create hidden cycles.

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.5 | 2025-12-10 | 6 additional normative rules (fixes 53-58): contract loader determinism, reserved fields governance, schema generation direction, example contract location, synchronous execution in v1.0, step type routing only |
| 1.0.4 | 2025-12-10 | 12 additional normative rules (fixes 41-52): step type normalization, parallel_group opaque metadata, continue_on_error vs error_action precedence, deterministic validation error ordering, workflow_metadata.execution_mode advisory, global_timeout_ms vs step timeout_ms, step_outputs JSON serialization, duplicate step_name allowed, skipped_steps ordering, cross-step mutation prohibition, wave boundary internal only, order_index action creation prohibition |
| 1.0.3 | 2025-12-10 | 20 additional normative rules (fixes 21-40): failure strategy precedence, parallel-wave failure, orphan steps, dependency ordering, action metadata immutability, parallel_group semantics, retry semantics, empty workflow, payload serialization, correlation_id consistency, order_index semantics, action_id uniqueness, workflow/operation ID distinction, global timeout behavior, input metadata immutability, iteration order stability, timeout validation, execution mode override, conditional step prohibition |
| 1.0.2 | 2025-12-10 | 20 additional normative rules and clarifications (see Changelog) |
| 1.0.1 | 2025-12-10 | 20 structural and semantic corrections (see Changelog) |
| 1.0.0 | 2025-12-10 | Enhanced v1.0 specification with normative rules, purity boundary, glossary |

---

**Related Documents**:
- [CONTRACT_DRIVEN_NODEREDUCER_V1_0.md](CONTRACT_DRIVEN_NODEREDUCER_V1_0.md) - FSM-driven NodeReducer specification
- [ONEX_FOUR_NODE_ARCHITECTURE.md](ONEX_FOUR_NODE_ARCHITECTURE.md) - ONEX four-node architecture overview
- [docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md](../guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md) - Orchestrator node tutorial

---

**Last Updated**: 2025-12-10
**Version**: 1.0.5
**Status**: DRAFT - Ready for Implementation
