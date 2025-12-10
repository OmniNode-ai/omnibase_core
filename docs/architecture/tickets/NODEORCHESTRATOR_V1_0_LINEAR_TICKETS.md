# Contract-Driven NodeOrchestrator v1.0 - Linear Ticket Breakdown (Consolidated)

> **Spec Version**: 1.0.5
> **Linear Project**: OMN-496
> **Created**: 2025-12-10
> **Structure**: Consolidated tickets with internal checklists

---

## Executive Summary

This document defines the **Linear ticket breakdown** for implementing NodeOrchestrator v1.0, a workflow-driven coordination engine for the ONEX 4-node architecture.

**What NodeOrchestrator Does**:
- Receives a typed workflow definition with steps and dependencies
- Validates the workflow (cycles, dependencies, invariants)
- Computes topological execution order using Kahn's algorithm
- Emits `ModelAction` objects for target nodes to execute
- Returns structured results without performing side effects

**Key Properties**:
- **Pure function semantics**: Executor is stateless and deterministic
- **Synchronous execution**: v1.0 is single-threaded; async deferred to v1.1+
- **Wave-based ordering**: Steps grouped by dependency topology, not metadata
- **Action emission**: Work is delegated via lease-protected actions, not executed directly

**Document Structure**:
1. **Rules** (Normative): Layering, Reserved Semantics, Execution Model
2. **Tickets** (Implementation): MVP → Beta → Production milestones
3. **Reference** (Informative): Glossary, Examples, Revision History

---

## Formal Notation

This document uses RFC 2119 keywords with the following meanings:

| Keyword | Meaning |
|---------|---------|
| **MUST** | Absolute requirement. Violation is non-conforming. |
| **MUST NOT** | Absolute prohibition. Violation is non-conforming. |
| **SHOULD** | Recommended but not required. Deviation requires justification. |
| **SHOULD NOT** | Discouraged but not prohibited. Usage requires justification. |
| **MAY** | Optional. Implementation choice with no conformance impact. |

All normative rules use these keywords. Informative sections use lowercase equivalents.

---

## Normative vs Informative Classification

This document contains both **normative** (MUST/MUST NOT) and **informative** (SHOULD/MAY/advisory) content.

### Normative Sections (Enforcement Required)
- Layering & Dependency Rules
- Reserved Semantics Rule
- Execution Model Rules
- All checklist items marked with MUST/MUST NOT
- Error ordering matrix
- All invariants (contract versioning, step identity, etc.)

### Informative Sections (Guidance Only)
- Contract Linter utility (warnings only, no execution impact)
- Complexity Budget warnings (soft limits, no execution impact)
- Example Location Rule (organizational guidance)
- Benchmark baselines (regression-based, not absolute targets)

Contributors MUST NOT interpret informative guidance as hard requirements. Informative sections exist to improve developer experience without affecting correctness guarantees.

---

## Layering & Dependency Rules (Non-Negotiable)

| Layer | Repo | Owns | Depends On |
|-------|------|------|------------|
| **Core Runtime** | `omnibase_core` | **All runtime models and logic**: Workflow contracts, orchestrator contracts, Pydantic models, executors, NodeOrchestrator, tests | Lowest layer (no dependency on SPI) |
| **Protocol / SPI** | `omnibase_spi` | **Protocols and external-facing interfaces only**: `Protocol*` definitions, external IDL/JSON Schema that *reference* core models | **Depends on `omnibase_core`** for concrete types |
| **Infrastructure / Integrations** | `omnibase_infra` | Action routing, persistence backends, Effect node handlers, monitoring, concrete infra integrations | Depends on `omnibase_core` (+ optionally SPI) |

**Hard rules:**

1. **All Workflow and NodeOrchestrator contract models live in `omnibase_core`**.
   They do **not** move to `omnibase_spi`.
2. `omnibase_spi` may **reference** core models in protocol signatures, but must not redefine or fork them.
3. Any change that would require `omnibase_core` to depend on `omnibase_spi` is **invalid** and must be redesigned.

All tickets below respect this layering: repository assignments are explicit and never invert the dependency direction.

---

## Reserved Semantics Rule (v1.0.4 Normative)

All fields and enums marked reserved for v1.1 or later versions:

1. **MUST be parsed** by SPI during contract codegen
2. **MUST be preserved** by Core in typed models
3. **MUST NOT influence** validation, ordering, or execution in v1.0
4. **MUST NOT be logged** as warnings or errors if present
5. **MUST be ignored deterministically** by the executor
6. **MUST raise `ModelOnexError`** if used in a context implying semantic behavior

**Definition of "Semantic Use"** (testable criteria):

A reserved field is considered "used semantically" if it:
- Influences validation logic (causes pass/fail changes), or
- Modifies execution behavior (changes step processing), or
- Changes action creation, ordering, grouping, or dependencies, or
- Alters failure-handling paths (skip, retry, abort decisions)

Any such use MUST raise `ModelOnexError` with code `RESERVED_FIELD_SEMANTIC_USE`.

**Debug/Log Prohibition**:
- Reserved fields MUST NOT be included in any outbound debug or trace output unless explicitly requested in debug-mode
- This prevents tooling and logs from implying the fields have active semantics

**Affected Reserved Items**:
- `EnumBranchCondition` - defined but raises error if used
- `ModelExecutionGraph` - defined but not consulted by executor
- `ModelWorkflowNode` - defined but not executed
- Saga-related fields (compensation patterns)
- `parallel_group` semantics beyond "opaque label"
- `CONDITIONAL` and `STREAMING` execution modes

If an implementation executes reserved behavior in v1.0, it is **non-conforming**.

**Reference**: This rule is referenced by BETA-01 Fix 3, Fix 12; BETA-02 Fix 9; BETA-03 Fix 27; BETA-04 Fix 42 instead of repeating partial behavior specifications.

---

## Execution Model Rules (v1.0.4 Normative)

These rules govern v1.0 execution and MUST be visible at the top level:

### Synchronous Execution Guarantee

**The v1.0 Core Runtime executes synchronously.** Any async signature is a compatibility wrapper, not concurrency. This rule applies to:
- `execute_workflow` pure function
- `NodeOrchestrator.process()` method
- All validation and action creation utilities

Async variants may be added in v1.1+ without changing semantic behavior.

### Wave Formation Prohibition

Executors MUST NOT introduce wave boundaries based on:
- `step_type` field (including `step_type="parallel"`)
- `parallel_group` field
- Any metadata field not explicitly governing wave formation

Wave boundaries are determined **solely** by dependency topology in v1.0.

### Global Registry Prohibition

No implicit global registries or caches may participate in execution order:
- Step lookup caches MUST NOT affect ordering
- Action creation MUST NOT depend on global mutable state
- Validation MUST be stateless across invocations

**Explicitly Prohibited Patterns**:
- Module-level LRU caches (`@lru_cache` at module scope)
- Module-level dicts storing step/action lookups
- `functools.cached_property` relying on global state
- Singletons containing workflow metadata
- Any memoization that persists across `execute_workflow` calls

**CI Enforcement**: Build MUST fail if prohibited patterns are detected in executor or validation code.

This prevents ordering nondeterminism in single-threaded execution.

### Post-Validation Contract Integrity

After validation, infra MUST NOT mutate the contract before execution:
- Compute a stable SHA-256 hash of the typed contract after validation
- **Hash MUST include all reserved fields**, even those ignored in execution (prevents silent desync)
- Executor MUST check hash equality before running
- Any mismatch MUST raise `ModelOnexError` with code `CONTRACT_INTEGRITY_VIOLATION`

This blocks accidental or malicious mutation between phases.

### Contract Versioning Invariant

Given identical `workflow_definition.version` and identical contract contents:
- The executor MUST produce identical action sets
- The executor MUST produce identical action ordering
- This applies across all executions, CI runs, and environments

**Version Mismatch Warning**:
- If version differs but contract structure is byte-identical, executor MUST warn non-fatally
- This prevents version numbers from becoming meaningless while avoiding brittleness

**Deterministic Action IDs**:
- Given the same workflow run, `action_id` values MUST be identical across repeated executions
- This ensures strong replay semantics

### Step Identity Invariant

`step_id` is the canonical identifier throughout the system:
- All models, action mappings, and dependencies MUST use `step_id` as the source of truth
- `step_name` is for display only and MAY be duplicated
- Action dependencies reference `action_id` (derived from `step_id`), never `step_name`

**Duplicate step_name Rule**:
- If duplicate `step_name` values exist, `correlation_id` MUST NOT depend on `step_name`
- This ensures determinism in logs and observability

### Empty Dependency Rule

Steps with `depends_on=[]` (empty list):
- MUST appear in the first wave
- MUST respect declaration order within the first wave
- Are NOT orphan steps (they are explicit root nodes)

### Equal-Priority Action Ordering

When priority clamping creates collisions (multiple actions with same priority):
- Ordering MUST fall back to original contract declaration order **within the same wave**
- Across waves, wave boundaries supersede declaration order
- This applies only to intra-wave ordering
- Prevents nondeterministic batching

Contributors MUST NOT attempt to flatten waves when debugging priority collisions.

### Deterministic Error Ordering

Validation MUST emit errors in the following priority order (highest first):

| Priority | Error Class | Example |
|----------|-------------|---------|
| 1 | Structural errors | Missing required fields, invalid types |
| 2 | Dependency errors | Invalid dependency reference, missing step_id |
| 3 | Cycle errors | Dependency cycle detected |
| 4 | Action construction errors | Non-serializable payload, invalid action_type |
| 5 | Execution mode errors | CONDITIONAL/STREAMING used |
| 6 | Reserved semantics violations | Reserved field used semantically |

Validation MUST emit only the **highest-priority error class** encountered. Lower-priority errors are not reported until higher-priority errors are fixed.

### Forbidden Imports Enforcement

Layering is enforced via `/omnibase_core/forbidden_imports.txt`:
- Contains import prefixes banned from core (e.g., `omnibase_spi`, `omnibase_infra`)
- CI MUST fail if code or tests import these prefixes
- Reduces attack surface for accidental layering drift

### Environment/Filesystem Isolation

Execution order MUST NOT depend on:
- Process environment variables
- Filesystem state (temporary files, lock files)
- System clock (except for timestamps in output models)
- Network state or external services

This prevents subtle nondeterminism introduced by infrastructure.

### Side-Effect-Free Default Factories

Model `default_factory` functions MUST NOT:
- Generate random values
- Generate timestamps
- Generate UUIDs
- Perform I/O operations
- Access global mutable state

CI MUST check for prohibited default factories in all Core models.

---

## Identifier and Value Normalization Rules

### step_type Normalization

Input `step_type` values MUST be normalized before processing:
- Lowercase conversion: `"COMPUTE"` → `"compute"`
- Whitespace trimming: `" effect "` → `"effect"`
- Valid values after normalization: `compute`, `effect`, `reducer`, `orchestrator`, `custom`, `parallel`
- Invalid values after normalization MUST raise `ModelOnexError`

### correlation_id Production

When `correlation_id` is not provided in a step:
- MUST be generated deterministically from `step_id`
- Format: `{workflow_id}:{step_id}` (colon-separated)
- MUST NOT depend on `step_name`, timestamps, or random values
- MUST be identical across repeated executions of the same workflow

### action_id Format Specification

`action_id` values MUST follow a deterministic format:
- Format: `{workflow_id}:{step_id}:{action_sequence}` where `action_sequence` is a 0-indexed counter
- MUST be globally unique within a workflow execution
- MUST be identical across repeated executions of the same workflow with same inputs
- MUST NOT contain random components

### skipped_steps Ordering

`skipped_steps` in results MUST follow this ordering:
1. Steps disabled via `enabled: false` (in declaration order)
2. Steps skipped due to `skip_on_failure` (in declaration order)
3. Steps skipped due to mid-wave failure with `error_action="stop"` (in declaration order)

Within each category, original contract declaration order is preserved.

---

## Validation Phase Separation

Validation occurs in two distinct phases:

### Phase 1: Static Contract Validation (Before Execution)
- Structural validation (required fields, types)
- Dependency validation (references exist)
- Cycle detection
- Execution mode validation
- Reserved field semantic use detection

### Phase 2: Dynamic Execution Validation (During Execution)
- Action construction validation (JSON-serializability)
- Payload validation
- Timeout validation

Phase 1 errors MUST be raised before any Phase 2 processing begins.

---

## ModelOnexError Payload Shape

All `ModelOnexError` instances MUST include:

```python
{
    "error_code": str,        # From EnumCoreErrorCode
    "message": str,           # Human-readable description
    "context": {              # Structured context
        "workflow_id": str,   # Optional, if available
        "step_id": str,       # Optional, if step-specific
        "field": str,         # Optional, if field-specific
    },
    "timestamp": str,         # ISO-8601 format
}
```

This shape is enforced for API consistency across all error types.

---

## Formal Wave Algorithm

Waves are computed using **Kahn's algorithm** with the following specification:

```
Algorithm: ComputeWaves(steps, dependencies)
Input: List of steps, dependency graph
Output: List of waves (each wave is a list of steps)

1. Compute in_degree for each step
2. Initialize wave_0 with all steps where in_degree == 0
3. Sort wave_0 by declaration order (tiebreaker)
4. waves = [wave_0]
5. While unprocessed steps remain:
   a. For each step in current wave, decrement in_degree of dependents
   b. Collect steps with in_degree == 0 into next_wave
   c. Sort next_wave by declaration order (tiebreaker)
   d. Append next_wave to waves
6. Return waves
```

This algorithm is **canonical** and MUST NOT be replaced with alternative topological sort implementations.

---

## Canonical Tiebreaker Hierarchy

When ordering decisions require tiebreaking, apply this hierarchy in order:

| Priority | Criterion | Applies To |
|----------|-----------|------------|
| 1 | Dependency topology | Wave assignment |
| 2 | Declaration order (YAML/contract) | Intra-wave ordering |
| 3 | Step priority (after clamping) | Action scheduling hint |
| 4 | step_id lexicographic | Final fallback (never ambiguous) |

No two steps can have identical ordering after applying this hierarchy.

---

## Repository Import Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ALLOWED IMPORTS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   omnibase_infra ──────────────────────────────────────────┐    │
│         │                                                  │    │
│         │ imports                                          │    │
│         ▼                                                  │    │
│   omnibase_spi ────────────────────────────────────────┐   │    │
│         │                                              │   │    │
│         │ imports                                      │   │    │
│         ▼                                              ▼   ▼    │
│   omnibase_core ◄──────────────────────────────────────────────│
│         │                                                       │
│         │ imports                                               │
│         ▼                                                       │
│   Python stdlib only                                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                       FORBIDDEN IMPORTS                         │
├─────────────────────────────────────────────────────────────────┤
│   omnibase_core ──X──► omnibase_spi     (FORBIDDEN)            │
│   omnibase_core ──X──► omnibase_infra   (FORBIDDEN)            │
│   omnibase_spi  ──X──► omnibase_infra   (FORBIDDEN)            │
└─────────────────────────────────────────────────────────────────┘
```

CI enforces this via `/omnibase_core/forbidden_imports.txt` and `layering_test.py`.

---

## Workflow State Transitions

```
                    ┌─────────────┐
                    │   PENDING   │
                    └──────┬──────┘
                           │ start execution
                           ▼
                    ┌─────────────┐
              ┌─────│   RUNNING   │─────┐
              │     └──────┬──────┘     │
              │            │            │
         timeout/      all steps    step fails with
         cancel        complete     error_action=stop
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ CANCELLED│ │COMPLETED │ │  FAILED  │
       └──────────┘ └──────────┘ └──────────┘

State Transition Rules:
- PENDING → RUNNING: Only valid transition from PENDING
- RUNNING → COMPLETED: All steps processed successfully
- RUNNING → FAILED: Any step fails with error_action="stop"
- RUNNING → CANCELLED: Timeout or explicit cancellation
- Terminal states (COMPLETED, FAILED, CANCELLED): No outbound transitions
- PAUSED: Reserved for v1.1 (not implemented in v1.0)
```

---

## Ordering Composition Invariant

All deterministic ordering rules MUST compose without contradiction:

- **Invariant**: For any two distinct steps A and B, exactly one of the following is true:
  - A is ordered before B
  - B is ordered before A
  - A and B are in different waves (no ordering relationship required)

- **Test requirement**: Conformance tests MUST verify that no two ordering rules produce conflicting results for any valid contract.

---

## Reserved Field Deprecation Strategy

When a reserved field transitions to active semantics:

1. **Announce**: Document the change in the next minor version changelog
2. **Preserve**: Field behavior MUST remain no-op for one minor version after announcement
3. **Activate**: Field becomes semantically active in the following minor version
4. **Test**: Cross-version compatibility tests MUST verify that:
   - Old contracts without the field still work
   - Old contracts with the field (as reserved) produce warnings but work
   - New contracts with the field use new semantics

This prevents silent reactivation without adequate migration period.

---

## Semantic Equivalence and Caching

### Contract Semantic Equivalence

Two workflow contracts are **semantically equivalent** if:
- They produce identical action sets when executed
- They produce identical action ordering when executed
- They produce identical execution results (completed, failed, skipped sets)

**Cross-Version Equivalence**: Implementations MAY treat contracts with different version values as semantically equivalent for caching purposes, but MUST NOT assume semantic equivalence purely from version numbers.

**Caching Rule**: Implementations MAY cache execution results for semantically equivalent contracts without violating global registry prohibitions, provided:
- Cache keys are derived from contract hash (not mutable state)
- Cache entries do not affect ordering of uncached executions
- Cache invalidation occurs on any contract modification
- Caches MUST be scoped to the executor instance or explicit cache layer
- Caches MUST NOT modify wave computation, priority ordering, or dependency resolution
- Caches MAY store precomputed results for repeated identical inputs but MUST NOT be consulted for partial or incremental execution decisions

### Canonical Serialization Ordering (Implementation Guidance)

**Classification**: This section is implementation guidance. Conformance does not depend on exact encoding details, only on deterministic hash stability.

For SHA-256 hash stability across Python versions and YAML libraries:
- Dictionary keys MUST be sorted lexicographically
- Lists MUST preserve declaration order

**Implementation Note**: Exact low-level representation rules (numeric formatting, trailing zeros, encoding details) are implementation-defined but MUST be stable and deterministic. The canonical serializer implementation MUST be tested for hash stability across supported environments.

This ensures identical contracts produce identical hashes regardless of environment.

### Pydantic Validator Immutability (Implementation Guidance)

**Classification**: This section is implementation guidance. Conformance testing focuses on contract semantics, not internal validator behavior.

Validators MUST behave as pure transforms with respect to *contract semantics*: they MAY construct new values but MUST NOT mutate shared objects that are visible outside the model.

Recommended practices:
- All normalization SHOULD occur pre-model or via pure transforms
- Validators MAY reject invalid values but SHOULD NOT transform them in ways that affect execution semantics
- Use `@field_validator` with `mode="before"` for normalization, returning new values

**Test Note**: Spot-check this with a few "shared object reused in multiple steps" scenarios rather than attempting global enforcement.

This prevents subtle mutation bugs that could affect determinism.

---

## Contract Authoring Rules

### High Root Count Warning (Informative)

Contracts with more than 100 root steps (`depends_on=[]`) SHOULD emit a warning:
- High root count is often an antipattern indicating poor workflow structure
- Consider grouping related steps under common dependencies
- Warning does NOT affect execution

### Unknown Field Handling

When parsing YAML contracts:
- Unknown fields in **deterministic positions** (step definitions, dependencies) MUST raise `ModelOnexError`
- Unknown fields in **advisory positions** (metadata) SHOULD emit a warning and be preserved
- Unknown fields matching reserved field patterns (documented in spec) MAY be silently preserved

This prevents accidental typos from silently affecting workflows while allowing forward compatibility.

---

## Minimal Valid Contract Example

```yaml
# Minimal valid workflow contract (annotated)
version: "1.0"                    # [deterministic] Contract version
workflow_metadata:
  workflow_name: "minimal"        # [deterministic] Human-readable name
  workflow_version: "1.0.0"       # [deterministic] Semantic version
  execution_mode: "SEQUENTIAL"    # [advisory] Hint only in v1.0

steps:
  - step_id: "step-001"           # [deterministic] Canonical identifier
    step_name: "First Step"       # [advisory] Display name (may duplicate)
    step_type: "compute"          # [deterministic] Normalized to lowercase
    depends_on: []                # [deterministic] Empty = first wave
    enabled: true                 # [deterministic] Default true
    priority: 500                 # [advisory] Clamped to 1-10 for actions
    # parallel_group: "group-a"   # [reserved] Ignored in v1.0
```

Field annotations:
- `[deterministic]`: Affects execution ordering or action creation
- `[advisory]`: Metadata only, no execution impact in v1.0
- `[reserved]`: Parsed and preserved, no execution impact in v1.0

---

## step_type Semantics Reference

| step_type | v1.0 Semantics | v1.1+ Future Semantics |
|-----------|----------------|------------------------|
| `compute` | Routes to NodeCompute targets | May add batch optimization hints |
| `effect` | Routes to NodeEffect targets | May add retry policies |
| `reducer` | Routes to NodeReducer targets | May add aggregation hints |
| `orchestrator` | Routes to NodeOrchestrator targets | May add sub-workflow semantics |
| `custom` | Routes to custom node types | May add plugin discovery |
| `parallel` | **Metadata only** - no execution impact | May enable explicit parallelization |

**Critical Note**: In v1.0, `step_type` affects only action routing (which node type receives the action). It does NOT affect wave formation, execution ordering, or parallelization.

---

## Design Rationale: Waves as Internal-Only

**Why waves are not exposed in v1.0 APIs**:

1. **Implementation flexibility**: Keeping waves internal allows future optimizations (e.g., adaptive batching) without breaking API contracts

2. **Determinism guarantee**: External wave exposure would create expectations about concurrent execution that v1.0's synchronous model cannot satisfy

3. **Testing simplicity**: Internal-only waves mean tests verify ordering and action output, not intermediate scheduling structures

4. **Migration safety**: If wave semantics change in v1.1+, no external code depends on current behavior

**Contributor Guidance**: Do NOT add wave identifiers to:
- `ModelOrchestratorOutput`
- `WorkflowExecutionResult`
- Action metadata
- Log messages at INFO level or higher

Waves MAY appear in DEBUG-level logs when `ONEX_DEBUG_WAVES=true`.

---

## Troubleshooting Guide

### Common Errors and Solutions

| Error Code | Likely Cause | Solution |
|------------|--------------|----------|
| `CONTRACT_INTEGRITY_VIOLATION` | Contract was modified between validation and execution | Ensure immutability; check for middleware mutations |
| `VALIDATION_ERROR` (cycle) | Dependency cycle in workflow | Use `contract_linter.py` to visualize dependencies |
| `VALIDATION_ERROR` (mode) | Using CONDITIONAL or STREAMING | These modes are reserved; use SEQUENTIAL, PARALLEL, or BATCH |
| `RESERVED_FIELD_SEMANTIC_USE` | Reserved field influencing execution | Remove semantic dependency on reserved fields |
| `DEPENDENCY_NOT_FOUND` | Invalid step_id in depends_on | Check for typos; ensure referenced step exists |

### Debugging Checklist

1. **Determinism issues**: Run with `PYTHONHASHSEED=0` to eliminate hash randomization
2. **Ordering issues**: Enable `ONEX_DEBUG_WAVES=true` to see wave assignments
3. **Action issues**: Check action_id format matches `{workflow_id}:{step_id}:{sequence}`
4. **Hash mismatches**: Verify YAML uses consistent key ordering and encoding

### Performance Issues

- **Slow validation**: Check dependency depth (>50 is suspicious)
- **High memory**: Check step count (>500 may need review)
- **Slow action creation**: Check payload JSON-serializability

---

## Forward Compatibility Constraints

### Field Name Reuse Prohibition

New reserved fields MUST NOT reuse names of previously removed or deprecated fields:
- Prevents confusion in versioned contracts
- Ensures old contracts don't accidentally trigger new behavior
- Maintains clear audit trail of field evolution

### Non-Deterministic Field Prohibition

Future contract versions MUST NOT introduce:
- Fields with random default values
- Timestamp fields that affect ordering
- Environment-dependent fields
- Fields requiring network access for resolution

This ensures all future versions maintain the determinism guarantee.

---

## Core Module Boundaries

### Canonical Module Structure

```
omnibase_core/
├── models/           # All Pydantic models (workflow, action, result)
│   ├── workflow/     # ModelWorkflowDefinition, ModelWorkflowStep
│   ├── orchestrator/ # ModelOrchestratorInput, ModelOrchestratorOutput
│   └── action/       # ModelAction
├── executor/         # Pure execution functions
│   ├── execute.py    # execute_workflow() - single public entrypoint
│   └── internal/     # Wave computation, ordering (not exported)
├── validation/       # Contract validation
│   ├── validate.py   # validate_contract() - single public entrypoint
│   └── internal/     # Cycle detection, dependency checking
├── enums/            # All enumerations
└── errors/           # ModelOnexError and codes
```

**Import Rules**:
- External code imports from `omnibase_core.executor.execute` and `omnibase_core.validation.validate`
- Internal modules (`internal/`) MUST NOT be imported externally
- CI enforces these boundaries via import analysis

---

## Metadata Sanitization Rules (Implementation Guidance)

**Classification**: This section is implementation guidance. These rules are normative for Core models but do not replace infra-level sanitization. The primary purpose is preventing log injection and basic safety, not full input validation for external systems.

### Security Considerations

All metadata fields accepting developer-supplied strings MUST be sanitized:

| Field | Sanitization Required |
|-------|----------------------|
| `workflow_name` | Escape newlines, limit length to 255 |
| `step_name` | Escape newlines, limit length to 255 |
| `description` | Escape newlines, limit length to 1000 |
| `metadata` values | JSON-safe encoding, no control characters |

### Log Injection Prevention

Error messages referencing reserved fields MUST NOT include user-provided step fields without escaping:
- Use `repr()` for string values in error messages
- Truncate long values to prevent log flooding
- Never interpolate raw metadata into log format strings

### Input Validation

`workflow_id` and `operation_id` MUST be treated as untrusted input unless validated upstream:
- Validate UUID format before use
- Reject non-printable characters
- Limit length to 128 characters

---

## Debug Hooks Specification (Informative)

### Optional Debug Hooks

The following debug hooks MAY be enabled via environment variables:

| Hook | Environment Variable | Output |
|------|---------------------|--------|
| Wave visualization | `ONEX_DEBUG_WAVES=true` | Wave assignments in DEBUG logs |
| Priority sorting | `ONEX_DEBUG_PRIORITY=true` | Priority decisions in DEBUG logs |
| Dependency graph | `ONEX_DEBUG_DEPS=true` | DOT-format graph to stderr |
| Action trace | `ONEX_DEBUG_ACTIONS=true` | Action creation sequence |

**Guarantees**:
- Debug hooks MUST NOT affect execution ordering
- Debug hooks MUST NOT affect action creation
- Debug output is non-semantic and MAY change between versions
- Debug hooks MUST NOT introduce new side effects beyond logging and in-memory diagnostics
- Debug hooks MUST NOT write to disk or perform network I/O unless explicitly configured with a separate, opt-in setting

---

## Metrics Naming Conventions

### Standard Workflow Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `nodeorchestrator_execution_time_ms` | Histogram | Total execution time |
| `nodeorchestrator_step_count` | Gauge | Number of steps in workflow |
| `nodeorchestrator_action_count` | Gauge | Number of actions emitted |
| `nodeorchestrator_validation_time_ms` | Histogram | Contract validation time |
| `nodeorchestrator_wave_count` | Gauge | Internal wave count (debug only) |

**Note**: `wave_count` is internal telemetry only. It MUST NOT appear in public APIs or affect external behavior.

---

## Testing Infrastructure Requirements

### Hash Seed Stability Test

Conformance tests MUST include:
- Run same workflow 100+ times with random `PYTHONHASHSEED` values
- Assert identical action sets and ordering across all runs
- Detect any hash-dependent ordering bugs

### Reserved Field Fuzzing

Test suite MUST include:
- Generate random DAGs with reserved fields
- Verify reserved fields are preserved but not executed
- Verify semantic use detection catches all prohibited patterns

### Canonical Contract Snapshots

For the minimal valid contract example:
- Store serialized form as test fixture
- Assert no changes to serialized form without explicit version bump
- Prevent accidental drift in contract format

---

## Repository Classification

| Repository | Purpose | Ticket Labels |
|------------|---------|---------------|
| **omnibase_core** | Core models (Workflow contracts, orchestrator I/O, actions), enums, Workflow executor, NodeOrchestrator base class, all normative behavior + unit tests | `omnibase_core`, `nodeorchestrator-core` |
| **omnibase_spi** | Protocol interfaces and external contract views that **reference** core models (e.g., `ProtocolWorkflowExecutor`, `ProtocolOrchestrator`, JSON Schema for contracts) | `omnibase_spi`, `nodeorchestrator-spi` |
| **omnibase_infra** | Action routing, persistence backends, Effect node handlers, monitoring, **fully wired** example contracts that hit real handlers | `omnibase_infra`, `nodeorchestrator-infra` |
| **docs/orchestrator_examples/** | **Canonical home** for example YAML contracts and usage documentation (default location for all examples) | N/A (not standalone tickets) |

**Example Location Rule**: Example contracts belong in `docs/orchestrator_examples/` by default. Only move examples to `omnibase_infra/examples/` when they are wired to real infrastructure handlers and need to be tested as part of infra integration.

---

## Milestone Overview

| Milestone | Tickets | Est. Days | Focus |
|-----------|---------|-----------|-------|
| **MVP** | 6 | ~15 | Core functionality, sequential execution |
| **Beta** | 7 | ~19 | v1.0.1-v1.0.5 compliance, SPI protocols |
| **Production** | 4 | ~8 | Examples, benchmarks, docs, infra stubs |
| **Total** | **17** | ~42 | |

**Note**: Beta compliance tickets (BETA-01 through BETA-07) are estimated at 3d each with explicit timebox option. Estimates include implementation + tests.

---

## MVP Milestone - `omnibase_core`

> **Goal**: Get basic workflow-driven NodeOrchestrator working end-to-end with core functionality.
> **Success Criteria**: Can load workflow definition, execute workflow steps, emit actions, return structured results.

### MVP-01: Core Enums & Primitives [2d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `enums`, `nodeorchestrator-core`

**Checklist**:
- [ ] EnumExecutionMode (SEQUENTIAL, PARALLEL, BATCH; CONDITIONAL/STREAMING reserved)
  - **Note**: `EnumExecutionMode` controls wave construction only in v1.0. It does NOT affect step ordering within a wave.
- [ ] EnumActionType (COMPUTE, EFFECT, REDUCE, ORCHESTRATE, CUSTOM)
- [ ] EnumWorkflowState (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED; PAUSED reserved)
- [ ] EnumFailureRecoveryStrategy (RETRY, ABORT; ROLLBACK/COMPENSATE reserved)
- [ ] EnumBranchCondition (behavior governed by Reserved Semantics rule)
- [ ] Unit tests for all enum values and string representations

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Enums"

---

### MVP-02: Core I/O Models [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `models`, `nodeorchestrator-core`
**Blocked By**: MVP-01

**Checklist**:
- [ ] ModelOrchestratorInput (workflow_id, steps as `list[ModelWorkflowStep]`, operation_id, execution_mode, max_parallel_steps, global_timeout_ms, failure_strategy, metadata, timestamp)
- [ ] ModelOrchestratorOutput (execution_status, execution_time_ms, start_time, end_time, completed_steps, failed_steps, skipped_steps, step_outputs, actions_emitted, metrics)
- [ ] ModelAction frozen model (action_id, action_type, target_node_type, payload, dependencies as action_ids, priority 1-10, timeout_ms, lease_id, epoch, retry_count, metadata, created_at)
- [ ] WorkflowExecutionResult dataclass (pure executor output: workflow_id, execution_status, completed_steps, failed_steps, skipped_steps, actions_emitted, execution_time_ms, metadata, timestamp)
- [ ] Unit tests for serialization/deserialization, frozen behavior, validation

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Core Models"

---

### MVP-03: Workflow Contract Models [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `contracts`, `models`, `nodeorchestrator-core`
**Blocked By**: MVP-01

**Checklist**:
- [ ] ModelWorkflowDefinition (version, workflow_metadata, execution_graph reserved, coordination_rules)
- [ ] ModelWorkflowDefinitionMetadata (version, workflow_name, workflow_version, description, execution_mode, timeout_ms)
- [ ] ModelWorkflowStep frozen model (correlation_id, step_id, step_name, step_type, timeout_ms, retry_count, enabled, skip_on_failure, continue_on_error, error_action, priority 1-1000, order_index, depends_on, parallel_group, max_parallel_instances)
- [ ] ModelCoordinationRules (version, synchronization_points reserved, parallel_execution_allowed, failure_recovery_strategy)
- [ ] ModelExecutionGraph (reserved - defined but not executed in v1.0)
- [ ] ModelWorkflowNode (reserved - defined but not executed in v1.0)
- [ ] Unit tests for contract models, frozen behavior, reserved field handling

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Workflow Subcontract Models"

---

### MVP-04: Validation & DAG Utilities [2d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `validation`, `nodeorchestrator-core`
**Blocked By**: MVP-03

**Checklist**:
- [ ] DFS cycle detection algorithm (`_has_dependency_cycles`)
- [ ] Dependency validation (`_validate_dependencies` - verify all depends_on references exist)
- [ ] Duplicate step ID detection (`_validate_unique_step_ids`)
- [ ] Execution mode validation (reject CONDITIONAL/STREAMING with ModelOnexError)
- [ ] DAG validation with disabled steps (`_validate_dag_with_disabled_steps`)
- [ ] Contract validation invariants (all raise ModelOnexError on violation)
- [ ] **Deterministic error ordering**: Implement error priority matrix (structural > dependency > cycle > mode > reserved)
- [ ] **Empty depends_on handling**: Steps with `depends_on=[]` placed in first wave, declaration order preserved
- [ ] **Contract linter** (`contract_linter.py` - non-semantic, logs only):
  - Warn on unused `parallel_group`
  - Warn on duplicate `step_name`
  - Warn on unreachable steps
  - Warn on extremely large priority ranges before clamping
  - MUST NOT affect execution or validation
- [ ] Unit tests for all validation scenarios

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Contract Validation Invariants"

---

### MVP-05: Sequential Executor + NodeOrchestrator [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `executor`, `nodeorchestrator-core`
**Blocked By**: MVP-02, MVP-03, MVP-04

**Checklist**:
- [ ] `execute_workflow` pure function (**synchronous API in v1.0**; async variants may be added in v1.1+ without semantic changes)
- [ ] Topological ordering using Kahn's algorithm (`_get_topological_order`)
- [ ] Sequential execution mode only (parallel/batch as logical metadata in v1.0)
- [ ] Action creation for steps (`_create_action_for_step` - map step type to action type, clamp priority 1-1000 to 1-10, map step deps to action deps)
- [ ] NodeOrchestrator base class with workflow_definition property
- [ ] `process()` method implementation (validate mode, delegate to executor, convert result)
- [ ] workflow_definition injection (immutable once set, NOT loaded from self.contract)
- [ ] Context construction (`_build_workflow_context`)
- [ ] **Single-threaded runtime**: The v1.0 executor and NodeOrchestrator are defined as single-threaded. Any parallelism is handled by downstream consumers or infra, not by the core runtime.
- [ ] **Wave/output invariant**: ModelOrchestratorOutput and WorkflowExecutionResult MUST NOT expose any wave identifiers or structures (waves are internal only)
- [ ] **JSON payload validator** (`_validate_json_payload(obj)`):
  - Called during action creation
  - Raises `ModelOnexError` early if payload is not JSON-serializable
  - Prevents late runtime surprises
- [ ] **Equal-priority ordering**: When priority clamping creates collisions, fall back to contract declaration order
- [ ] **Contract integrity check**: Verify contract hash before execution (tamper detection)
- [ ] Unit tests for executor, ordering, action creation

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Execution Model", "NodeOrchestrator Behavior"

---

### MVP-06: MVP Conformance Tests [2d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `testing`, `nodeorchestrator-core`
**Blocked By**: MVP-05

**Checklist**:
- [ ] Enum value tests (all modes, types, states, strategies)
- [ ] Model serialization/deserialization tests
- [ ] Validation tests (cycles, dependencies, invariants, duplicate IDs)
- [ ] Sequential execution tests (single step, linear chain, diamond dependency)
- [ ] Action creation tests (priority clamping, dependency mapping, action_id generation)
- [ ] YAML contract loading tests (order preservation, typed conversion)
  - [ ] YAML loader tests verify that declaration order is preserved and used for tiebreakers
- [ ] **YAML round-trip stability tests**:
  - YAML → model → YAML round trip MUST preserve:
    - step ordering
    - step_id values
    - dependency sets
    - reserved fields (untouched)
    - **YAML scalar type preservation** (e.g., `"1"` vs `1`)
    - **Ordered mappings stay ordered**
    - **No new fields created with null values**
  - Round-trip MUST NOT introduce type coercion
  - Prevents serialization bugs that mutate contracts
- [ ] **Contract versioning invariant tests**: Same version + same contents = identical output
- [ ] End-to-end test: load definition -> validate -> execute -> verify actions

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Acceptance Criteria"

---

## Integration Gate (Required Before Beta)

Before starting the Beta milestone, the following gates MUST be satisfied:

- [ ] **Real-world integration**: At least one real orchestrator node in the existing system uses the new NodeOrchestrator in a test environment
- [ ] **Failure scenario coverage**: Integration MUST include at least one failure scenario (step failure, dependency failure, or timeout)
- [ ] **Happy path validation**: At least one multi-step workflow completes successfully end-to-end
- [ ] **Reversion test** (nondeterminism detection):
  - Re-run the exact same workflow + input twice
  - Assert action sets remain identical
  - Assert action ordering remains identical
  - **Timestamp handling**: Reversion test MUST ignore timestamps or test stabilized timestamp fields
  - `WorkflowExecutionResult` timestamps MUST be monotonic but not externally observable for ordering comparison
  - This protects against nondeterminism creeping in via refactors

This gate forces meaningful integration validation before spending time on normative compliance work. A gate that passes only on happy paths is trivial and provides false confidence.

---

## Beta Milestone - `omnibase_core` + `omnibase_spi`

> **Goal**: Full v1.0.4 normative compliance with comprehensive test coverage and SPI protocols.
> **Success Criteria**: Pass all v1.0.4 conformance checklist items. Integration tests pass.

### BETA-01: v1.0.1 Compliance [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `v1.0.1`, `compliance`, `nodeorchestrator-core`
**Blocked By**: MVP-06

**Estimate Note**: 3d (includes implementation + tests) or timebox to 2d with explicit carryover if incomplete.

**Checklist** (20 items from spec v1.0.1):
- [ ] Fix 1: No dict coercion - steps as typed ModelWorkflowStep instances
- [ ] Fix 2: Contract loading responsibility (Infra loads, Core receives typed models)
- [ ] Fix 3: ExecutionGraph not used in v1.0 (behavior governed by Reserved Semantics rule)
- [ ] Fix 4: Subcontract model immutability (frozen=True)
- [ ] Fix 5: Stateful only for workflow_definition property
- [ ] Fix 6: Step priority (1-1000) to Action priority (1-10) clamping
- [ ] Fix 7: Error hierarchy (structural -> semantic -> execution)
- [ ] Fix 8: "Create action for step" not "execute step"
- [ ] Fix 9: Per-action leases in v1.0
- [ ] Fix 10: Typed constructors in examples
- [ ] Fix 11: Repository boundaries (SPI->Core->Infra dependency direction)
- [ ] Fix 12: Reserved fields: behavior governed by Reserved Semantics rule
- [ ] Fix 13: CONDITIONAL/STREAMING raise ModelOnexError (not warning)
- [ ] Fix 14: WorkflowExecutionResult to ModelOrchestratorOutput transformation
- [ ] Fix 15: Side effect prohibition in executor
- [ ] Fix 16: Action.dependencies uses action_ids not step_ids
- [ ] Fix 17: skipped_steps in result
- [ ] Fix 18: Execution mode validation rejects reserved modes
- [ ] Fix 19: Dependency failure semantics
- [ ] Fix 20: DAG invariant for disabled steps

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Changelog v1.0.1

---

### BETA-02: v1.0.2 Compliance [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `v1.0.2`, `compliance`, `nodeorchestrator-core`
**Blocked By**: BETA-01

**Estimate Note**: 3d (includes implementation + tests) or timebox to 2d with explicit carryover if incomplete.

**Checklist** (20 items from spec v1.0.2):
- [ ] Fix 1-2: Typed Pydantic models (no dict coercion anywhere)
- [ ] Fix 3: workflow_definition immutability (reassignment is undefined behavior)
- [ ] Fix 4: execution_graph prohibition (MUST NOT consult, MUST NOT log warnings)
- [ ] Fix 5: Topological ordering tiebreaker (YAML/declaration order)
- [ ] Fix 6: Priority clamping applies to all execution modes
- [ ] Fix 7: skip_on_failure semantics (only for earlier step failures)
- [ ] Fix 8: Epoch increment responsibility (orchestrator sets 0, target increments)
- [ ] Fix 9: Saga fields ignored (behavior governed by Reserved Semantics rule)
- [ ] Fix 10: Disabled step forward compatibility
- [ ] Fix 11: Action emission wave ordering (YAML order within wave)
- [ ] Fix 12: Action creation exception handling
- [ ] Fix 13: start_time/end_time normative requirements
- [ ] Fix 14: Metadata isolation (no internal fields in result.metadata)
- [ ] Fix 15: UUID stability (step_id from contract, not generated)
- [ ] Fix 16: Expression evaluation prohibition (no custom expressions in v1.0)
- [ ] Fix 17: Step metadata immutability
- [ ] Fix 18: Wave boundary guarantee (all wave N before any wave N+1)
- [ ] Fix 19: Load balancing prohibition (deterministic ordering only)
- [ ] Fix 20: Validation phase separation (validate BEFORE execute)
- [ ] **Wave semantics note**: Waves are a logical construct in v1.0, not a concurrency guarantee. Wave semantics are tested via internal utilities and deterministic ordering, not via observable concurrency.
- [ ] **Thread safety**: Confirm no shared mutable global state in Core executor or validation utilities
- [ ] **YAML loader**: Topological ordering tests MUST be driven from YAML contracts, not only from in-memory model construction

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Changelog v1.0.2

---

### BETA-03: v1.0.3 Compliance [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `v1.0.3`, `compliance`, `nodeorchestrator-core`
**Blocked By**: BETA-02

**Estimate Note**: 3d (includes implementation + tests) or timebox to 2d with explicit carryover if incomplete.

**Checklist** (20 items from spec v1.0.3):
- [ ] Fix 21: Failure strategy precedence (step error_action > workflow failure_strategy)
- [ ] Fix 22: Partial wave failure (error_action="stop" skips remaining, workflow FAILED)
- [ ] Fix 23: Orphan step handling (no dependency path still executes, no validation failure)
- [ ] Fix 24: Dependency list ordering (depends_on semantically unordered, sort by declaration index)
- [ ] Fix 25: Action metadata immutability
- [ ] Fix 26: parallel_group vs depends_on (parallel_group for grouping, depends_on for ordering)
- [ ] Fix 27: parallel_group non-semantic in v1.0 (behavior governed by Reserved Semantics rule)
- [ ] Fix 28: Retry count semantics (retry_count on ModelAction)
- [ ] Fix 29: Empty workflow handling (steps=[] succeeds immediately with COMPLETED)
- [ ] Fix 30: Action payload type requirements (JSON-serializable)
- [ ] Fix 31: Cross-step correlation_id consistency
- [ ] Fix 32: order_index non-semantic (for display only)
- [ ] Fix 33: action_id global uniqueness
- [ ] Fix 34: workflow_id vs operation_id semantics
- [ ] Fix 35: Global timeout mid-wave behavior (unprocessed failed, in-progress assumed failed)
- [ ] Fix 36: Input metadata immutability
- [ ] Fix 37: Step iteration order stability (declaration order preserved)
- [ ] Fix 38: Zero timeout validation
- [ ] Fix 39: Execution mode override (input_data.execution_mode > workflow_definition)
- [ ] Fix 40: Conditional step type prohibition (raises ModelOnexError in v1.0)
- [ ] **Wave semantics note**: Waves are a logical construct in v1.0, not a concurrency guarantee. Wave semantics are tested via internal utilities and deterministic ordering, not via observable concurrency.

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Changelog v1.0.3

---

### BETA-04: v1.0.4 Compliance [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `v1.0.4`, `compliance`, `nodeorchestrator-core`
**Blocked By**: BETA-03

**Estimate Note**: 3d (includes implementation + tests) or timebox to 2d with explicit carryover if incomplete.

**Checklist** (12 items from spec v1.0.4):
- [ ] Fix 41: Step type normalization (compute, effect, reducer, orchestrator, custom, parallel only)
- [ ] Fix 42: parallel_group opaque metadata (behavior governed by Reserved Semantics rule)
- [ ] Fix 43: continue_on_error vs error_action precedence (error_action controls exclusively)
- [ ] Fix 44: Deterministic validation error ordering (step-structural, then dependency, then cycle)
- [ ] Fix 45: workflow_metadata.execution_mode advisory only
- [ ] Fix 46: global_timeout_ms vs step timeout_ms semantics
- [ ] Fix 47: step_outputs JSON serialization (non-serializable raises ModelOnexError)
- [ ] Fix 48: Duplicate step_name allowed (only step_id must be unique)
- [ ] Fix 49: skipped_steps ordering (original contract declaration order)
- [ ] Fix 50: Cross-step mutation prohibition
- [ ] Fix 51: Wave boundary internal only - Ensure no public API relies on wave index or wave count; waves are only an internal scheduling concept. Tested via internal helpers only; public models are wave-agnostic.
- [ ] Fix 52: order_index action creation prohibition (MUST NOT influence action ordering)
- [ ] **step_type clarification**: `step_type="parallel"` is treated as a purely routing/metadata flag in v1.0. It MUST NOT alter execution mode or DAG structure.
- [ ] Confirm that step_type has no effect on execution order or wave formation in v1.0

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Changelog v1.0.4

---

### BETA-05: SPI Protocol Definitions [2d]

**Repository**: `omnibase_spi`
**Labels**: `nodeorchestrator-v1.0`, `protocols`, `nodeorchestrator-spi`
**Blocked By**: BETA-04

**Note**: This ticket implements Fix 55 (Schema Generation Direction) - schemas MUST be generated FROM Core models, not manually authored.

**Checklist**:
- [ ] ProtocolWorkflowExecutor interface (references Core types: ModelWorkflowDefinition, ModelWorkflowStep, WorkflowExecutionResult)
- [ ] ProtocolOrchestrator interface (references Core types: ModelOrchestratorInput, ModelOrchestratorOutput)
- [ ] Workflow YAML schema (generated from ModelWorkflowDefinition, not manually authored)
- [ ] CI layering enforcement (layering_test.py pattern to prevent dependency inversion)
- [ ] Unit tests for protocol compliance
- [ ] **JSON Schema Generation Rule**: Schema generation is a one-way step:
  - `omnibase_spi` imports `omnibase_core` to generate schemas
  - Generated artifacts (JSON Schema, IDL) are NEVER imported back into `omnibase_core`
  - [ ] No generated schema or IDL artifact is ever imported into Core
  - [ ] **Manual edit prohibition**: Generated JSON Schema files MUST NOT be manually modified; CI MUST regenerate and compare

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Repository Boundaries"

---

### BETA-07: v1.0.5 Compliance [3d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `v1.0.5`, `compliance`, `nodeorchestrator-core`
**Blocked By**: BETA-04

**Estimate Note**: 3d (includes implementation + tests) or timebox to 2d with explicit carryover if incomplete.

**Checklist** (6 items from spec v1.0.5):
- [ ] Fix 53: Contract Loader Determinism - YAML loader MUST preserve declaration order exactly as written. Contract loader MUST NOT sort or normalize lists of steps. Validation tests MUST load from YAML to confirm tie-breaking and step ordering. Python 3.7+ dict insertion order preservation is REQUIRED.
- [ ] Fix 54: Reserved Fields Governance - Reserved fields MUST NOT be validated beyond structural type checking. Reserved fields MUST NOT be interpreted or influence any runtime decision. Reserved fields MUST NOT be logged (except at DEBUG level). Reserved fields MUST be preserved in round-trip serialization.
- [ ] Fix 55: Schema Generation Direction - JSON Schema/YAML schemas in omnibase_spi MUST be generated FROM ModelWorkflowDefinition in omnibase_core. Schemas MUST NOT be manually authored. No SPI-generated artifacts may be imported back into Core. Schema generation is one-directional: Core -> SPI.
- [ ] Fix 56: Example Contract Location - Example workflow contracts MUST NOT reside in omnibase_core. Examples belong in: docs/orchestrator_examples/ OR omnibase_infra/examples/. Core repo contains only runtime logic.
- [ ] Fix 57: Synchronous Execution in v1.0 - execute_workflow MUST use async signature for API compatibility. v1.0 execution MUST be synchronous within the async context. Parallel waves are represented logically as metadata only. Actual concurrency is deferred to omnibase_infra in future versions.
- [ ] Fix 58: Step Type Routing Only - step_type determines action routing target only. step_type MUST NOT change executor semantics in v1.0. Exception: step_type="conditional" MUST be rejected with ModelOnexError.

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Changelog v1.0.5

---

### BETA-06: Beta Integration Tests [2d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `testing`, `integration`, `nodeorchestrator-core`
**Blocked By**: BETA-07, BETA-05

**Checklist**:
- [ ] Full workflow execution test (YAML -> typed models -> execution -> result)
- [ ] v1.0.5 conformance test suite (all 58 normative fixes tested)
- [ ] Action emission ordering tests (within wave, across waves)
- [ ] Wave boundary tests (internal implementation detail validation via internal helpers only; public models are wave-agnostic)
- [ ] Edge case tests (empty workflow, orphan steps, timeout mid-wave, disabled steps)
- [ ] Error model tests (MUST raise vs MUST NOT raise scenarios)

**Conformance Test Structure** (internal organization):
- [ ] One test module per spec version (`test_v1_0_1.py`, `test_v1_0_2.py`, `test_v1_0_3.py`, `test_v1_0_4.py`, `test_v1_0_5.py`)
- [ ] Each module contains tests named by fix: `test_fix_01_typed_steps`, `test_fix_02_contract_loading`, etc.
- [ ] A meta-test asserts that all 58 fixes have at least one corresponding test function
- [ ] YAML loader tests verify that declaration order is preserved and used for tiebreakers
- [ ] **Cross-version invariant test**: For any YAML contract that was valid in v1.0.0, v1.0.5 MUST NOT change execution ordering unless mandated by a normative fix
- [ ] **Cross-version failure semantics invariant**: For any contract valid in both versions, failure classification (FAILED, SKIPPED, COMPLETED) MUST NOT change unless explicitly defined by a normative fix
- [ ] **Cross-layer tests**: Fixes that apply to multiple layers (e.g., Fix 11 repository boundaries) MUST include tests in both SPI and Core
- [ ] **Complexity budget warning test**: Verify soft limit warnings are emitted for workflows exceeding thresholds (MUST NOT affect execution):
  - N = 500 steps (configurable via `ONEX_WORKFLOW_STEP_LIMIT`)
  - M = dependency depth > 50 (configurable via `ONEX_WORKFLOW_DEPTH_LIMIT`)
- [ ] **Fixture mutability test**: `workflow_definition` MUST NOT mutate during execution (prevents caching metadata on the model)
- [ ] **Deterministic action_id test**: Same workflow run produces identical `action_id` values across repeated executions

**Determinism Infrastructure Tests** (from Testing Infrastructure Requirements):
- [ ] **Hash-seed stability test suite**: Run same workflow 100+ times with random `PYTHONHASHSEED` values; assert identical action sets and ordering across all runs
- [ ] **Reserved field fuzzing tests**: Generate random DAGs with reserved fields; verify reserved fields are preserved but not executed; verify semantic use detection catches all prohibited patterns
- [ ] **Canonical contract snapshot tests**: Store serialized form of minimal valid contract as test fixture; assert no changes without explicit version bump
- [ ] **Metadata sanitization tests**: Verify field length limits and escaping rules are enforced for `workflow_name`, `step_name`, `description`, and `metadata` values

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Acceptance Criteria"

---

## Production Milestone - All Repos

> **Goal**: Production-ready with examples, documentation, conformance suite, and monitoring.
> **Success Criteria**: Complete v1.0.5 conformance test suite passes. Documentation complete.

### PROD-01: Example Contracts [2d]

**Repository**: `docs/orchestrator_examples/`
**Labels**: `nodeorchestrator-v1.0`, `examples`, `documentation`
**Blocked By**: BETA-06

**Note**: This ticket implements Fix 56 (Example Contract Location) - examples MUST NOT reside in omnibase_core.

**IMPORTANT**: Examples are **illustrative, not normative**. They demonstrate usage patterns but do not define behavior. All normative tests live in `omnibase_core/tests/`. Examples MUST NOT become a shadow test suite.

**Checklist**:
- [ ] data_processing_pipeline.yaml (fetch_data -> validate_schema -> enrich_data -> persist_results)
- [ ] etl_pipeline.yaml (parallel extraction: extract_source_a/b/c -> transform_merge -> load_warehouse)
- [ ] parallel_execution.yaml (demonstrates wave construction and ordering)
- [ ] error_handling.yaml (error_action="stop", "continue", "retry" patterns)
- [ ] Each example includes inline documentation and expected behavior
- [ ] Examples explicitly marked as "illustrative" in their headers

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Example Contracts"

---

### PROD-02: Performance Benchmarks [2d]

**Repository**: `omnibase_core`
**Labels**: `nodeorchestrator-v1.0`, `performance`, `nodeorchestrator-core`
**Blocked By**: BETA-06

**IMPORTANT**: Absolute benchmarks are fragile (depend on Python version, machine specs, CI load). Use **regression-based bounds** instead.

**Checklist**:
- [ ] Validation benchmark baseline: establish baseline for 100 steps (cycles, dependencies, invariants)
- [ ] Topological sort benchmark baseline: establish baseline for 1000 steps (Kahn's algorithm)
- [ ] Action creation benchmark baseline: establish baseline per action (priority clamping, dependency mapping)
- [ ] Memory benchmark baseline: establish baseline per step overhead
- [ ] **Regression detection**: Benchmarks MUST maintain ≤10% regression from baseline across commits
- [ ] Benchmark harness with repeatable measurement methodology (warm-up runs, statistical aggregation)
- [ ] Performance regression test in CI with configurable tolerance

**Acceptance**: Performance is acceptable if regression bounds hold, not if absolute numbers are met.

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Acceptance Criteria" (non-functional)

---

### PROD-03: Documentation Updates [2d]

**Repository**: `omnibase_core` (docs/)
**Labels**: `nodeorchestrator-v1.0`, `documentation`
**Blocked By**: BETA-06

**Checklist**:
- [ ] Update ONEX Four-Node Architecture doc (NodeOrchestrator v1.0.4 details, action pattern)
- [ ] Update Orchestrator Node Tutorial (docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)
- [ ] Create migration guide from v0.x orchestrators
  - [ ] **Migration invariant**: Upgrading from v0.x to v1.0 MUST NOT change output action sets for workflows without reserved fields
- [ ] Add YAML contract authoring guide (best practices, common patterns)
- [ ] Update API reference documentation
- [ ] Add glossary of terms (wave, contract, executor, coordination rules, etc.)

**Spec Reference**: All documentation sections

---

### PROD-04: Infrastructure Stubs [2d]

**Repository**: `omnibase_infra`
**Labels**: `nodeorchestrator-v1.0`, `nodeorchestrator-infra`, `infrastructure`
**Blocked By**: BETA-05

**Checklist**:
- [ ] Action router stub (dispatches ModelAction to target nodes based on action_type)
- [ ] Effect node action handler example (processing ModelAction in NodeEffect)
- [ ] Workflow persistence handler example (persisting workflow state and action results)
- [ ] Monitoring/metrics stub (workflow execution metrics collection)
- [ ] Each stub includes integration test and usage documentation

**Spec Reference**: CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md: Section "Action Pattern"

---

## Dependency Graph

```
MVP-01 (Enums) ─────────────────────────────────────┐
                                                    │
MVP-03 (Workflow Models) ◄──────────────────────────┤
        │                                           │
        ▼                                           │
MVP-02 (Core I/O) ◄─────────────────────────────────┤
        │                                           │
        ▼                                           │
MVP-04 (Validation) ◄───────────────────────────────┘
        │
        ▼
MVP-05 (Executor + NodeOrchestrator)
        │
        ▼
MVP-06 (MVP Tests)
        │
        ▼
[INTEGRATION GATE] ◄─────────────────────────────────── Must pass before Beta
        │
        ▼
BETA-01 (v1.0.1) ──► BETA-02 (v1.0.2) ──► BETA-03 (v1.0.3) ──► BETA-04 (v1.0.4) ──► BETA-07 (v1.0.5)
                                                                                           │
                                                    ┌──────────────────────────────────────┴───┐
                                                    │                                        │
                                                    ▼                                        ▼
                                            BETA-05 (SPI)                          BETA-06 (Integration)
                                                    │                      │
                        ┌───────────────────────────┼──────────────────────┘
                        │                           │
                        ▼                           ▼
                PROD-04 (Infra) ◄───────────BETA-05 (explicit dependency)
                                                    │
                                            PROD-01 (Examples)
                                                    │
                        ┌───────────────────────────┤
                        │                           │
                        ▼                           ▼
                PROD-02 (Benchmarks)       PROD-03 (Docs)
```

**Note**: PROD-04 depends on BETA-05 (SPI protocols) for action routing interfaces. This dependency is explicit to prevent layering confusion. BETA-06 depends on BETA-07 to ensure all v1.0.5 fixes are tested.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Contract loader field reordering | Medium | High | YAML-based end-to-end tests with order validation |
| v1.1 feature scope creep | Medium | Medium | Strict reserved-field no-op policy, reject at runtime |
| Dependency inversion | Medium | High | CI layering_test.py in each repo, fail build on violation |
| Wave-based parallelism complexity | Medium | Medium | Wave boundaries internal only, comprehensive ordering tests |
| Action dependency mapping confusion | Medium | Low | Clear documentation: action_ids NOT step_ids |
| Thread safety confusion | High | Medium | Clear documentation, single-thread affinity enforced |

---

## Success Metrics

### MVP
- [ ] Basic workflow definition loads without errors
- [ ] Steps processed in topological order
- [ ] Actions emitted with valid lease_id and epoch=0
- [ ] ModelOnexError raised on cycles/invalid state
- [ ] Priority clamping works (1000 -> 10, 50 -> 5)

### Beta
- [ ] All v1.0.5 conformance checklist items pass (58 fixes)
- [ ] Integration tests cover full workflow (YAML -> execution -> actions)
- [ ] Code coverage > 90%
- [ ] Layer dependency CI check passes
- [ ] SPI protocols reference Core types correctly
- [ ] **Per-fix test coverage**: For every normative fix in the Appendix, there is at least one test that would fail if the fix were reverted
- [ ] **Meta-test validation**: A meta-test confirms all 58 fixes have corresponding test functions
- [ ] **Layering stability**: No dependency inversion detected across all repos for three consecutive PRs
- [ ] **Cross-version invariant**: v1.0.5 does not change execution ordering for v1.0.0-valid contracts unless mandated by a normative fix

### Production
- [ ] Example contracts work end-to-end
- [ ] Conformance test suite fully green
- [ ] Documentation complete and reviewed
- [ ] Performance benchmarks meet targets
- [ ] Infrastructure stubs demonstrate action handling

---

## Immediate Implementation Order

1. **MVP-01**: Enums + primitives (foundation for all models)
2. **MVP-03**: Workflow contract models (needed by I/O models for steps type)
3. **MVP-02**: Core I/O models (depends on workflow models for ModelWorkflowStep)
4. **MVP-04**: Validation (cycles, dependencies, invariants)
5. **MVP-05**: Sequential executor + NodeOrchestrator (core implementation)
6. **MVP-06**: Minimal conformance tests (validates MVP complete)

**Defer to Beta/Production**:
- Async execution internals and async API variants are out of scope for v1.0
- ExecutionGraph semantics (reserved, not executed)
- Branch conditions (reserved for v1.1)
- Saga fields (reserved for future)
- parallel_group beyond "opaque label" (v1.1+)

---

## Appendix: Normative Fix Mapping

| Spec Fix | Description | Ticket ID |
|----------|-------------|-----------|
| **v1.0.1 Fixes (1-20)** | | |
| Fix 1 | Typed ModelWorkflowStep (no dict coercion) | BETA-01 |
| Fix 2 | Contract Loading Responsibility | BETA-01 |
| Fix 3 | ModelExecutionGraph not used in v1.0 | MVP-03, BETA-01 |
| Fix 4 | Subcontract Model Immutability | MVP-03, BETA-01 |
| Fix 5 | Stateful vs stateless semantics | MVP-05, BETA-01 |
| Fix 6 | Step priority vs action priority | MVP-05, BETA-01 |
| Fix 7 | Error Hierarchy | MVP-04, BETA-01 |
| Fix 8 | "execute step" -> "create action" | MVP-05, BETA-01 |
| Fix 9 | Per-action leases | MVP-02, BETA-01 |
| Fix 10 | Typed ModelWorkflowStep constructors | MVP-03, BETA-01 |
| Fix 11 | Repository Boundaries | BETA-05 |
| Fix 12 | Reserved Fields Global Rule | MVP-03, BETA-01 |
| Fix 13 | CONDITIONAL/STREAMING rejection | MVP-04, BETA-01 |
| Fix 14 | WorkflowExecutionResult -> ModelOrchestratorOutput | MVP-02, BETA-01 |
| Fix 15 | Side Effect Prohibition | MVP-05, BETA-01 |
| Fix 16 | action_ids NOT step_ids | MVP-05, BETA-01 |
| Fix 17 | skipped_steps in result | MVP-02, BETA-01 |
| Fix 18 | Execution mode validation | MVP-04, BETA-01 |
| Fix 19 | Dependency Failure Semantics | MVP-04, BETA-01 |
| Fix 20 | DAG Invariant for Disabled Steps | MVP-04, BETA-01 |
| **v1.0.2 Fixes (1-20)** | | |
| Fix 1-2 | Typed Pydantic models | BETA-02 |
| Fix 3 | workflow_definition immutability | BETA-02 |
| Fix 4 | execution_graph prohibition | BETA-02 |
| Fix 5 | Topological ordering tiebreaker | BETA-02 |
| Fix 6 | Priority clamping all modes | BETA-02 |
| Fix 7 | skip_on_failure semantics | BETA-02 |
| Fix 8 | Epoch increment responsibility | BETA-02 |
| Fix 9 | Saga fields ignored | BETA-02 |
| Fix 10 | Disabled step forward compatibility | BETA-02 |
| Fix 11 | Action emission wave ordering | BETA-02 |
| Fix 12 | Action creation exception handling | BETA-02 |
| Fix 13 | start_time/end_time normative | BETA-02 |
| Fix 14 | Metadata isolation | BETA-02 |
| Fix 15 | UUID stability | BETA-02 |
| Fix 16 | Expression evaluation prohibition | BETA-02 |
| Fix 17 | Step metadata immutability | BETA-02 |
| Fix 18 | Wave boundary guarantee | BETA-02 |
| Fix 19 | Load balancing prohibition | BETA-02 |
| Fix 20 | Validation phase separation | BETA-02 |
| **v1.0.3 Fixes (21-40)** | | |
| Fix 21 | Failure strategy precedence | BETA-03 |
| Fix 22 | Partial parallel-wave failure | BETA-03 |
| Fix 23 | Orphan step handling | BETA-03 |
| Fix 24 | Dependency list ordering | BETA-03 |
| Fix 25 | Action metadata immutability | BETA-03 |
| Fix 26 | parallel_group vs depends_on | BETA-03 |
| Fix 27 | parallel_group non-semantic in v1.0 | BETA-03 |
| Fix 28 | Retry count semantics | BETA-03 |
| Fix 29 | Empty workflow handling | BETA-03 |
| Fix 30 | Action payload type requirements | BETA-03 |
| Fix 31 | Cross-step correlation_id consistency | BETA-03 |
| Fix 32 | order_index non-semantic | BETA-03 |
| Fix 33 | action_id global uniqueness | BETA-03 |
| Fix 34 | workflow_id vs operation_id semantics | BETA-03 |
| Fix 35 | Global timeout mid-wave behavior | BETA-03 |
| Fix 36 | Input metadata immutability | BETA-03 |
| Fix 37 | Step iteration order stability | BETA-03 |
| Fix 38 | Zero timeout validation | BETA-03 |
| Fix 39 | Execution mode override | BETA-03 |
| Fix 40 | Conditional step type prohibition | BETA-03 |
| **v1.0.4 Fixes (41-52)** | | |
| Fix 41 | Step type normalization | BETA-04 |
| Fix 42 | parallel_group opaque metadata | BETA-04 |
| Fix 43 | continue_on_error vs error_action | BETA-04 |
| Fix 44 | Deterministic validation error ordering | BETA-04 |
| Fix 45 | workflow_metadata.execution_mode advisory | BETA-04 |
| Fix 46 | global_timeout_ms vs step timeout_ms | BETA-04 |
| Fix 47 | step_outputs JSON serialization | BETA-04 |
| Fix 48 | Duplicate step_name allowed | BETA-04 |
| Fix 49 | skipped_steps ordering | BETA-04 |
| Fix 50 | Cross-step mutation prohibition | BETA-04 |
| Fix 51 | Wave boundary internal only | BETA-04, BETA-06 |
| Fix 52 | order_index action creation prohibition | BETA-04 |
| **v1.0.5 Fixes (53-58)** | | |
| Fix 53 | Contract Loader Determinism | BETA-07 |
| Fix 54 | Reserved Fields Governance | BETA-07 |
| Fix 55 | Schema Generation Direction | BETA-05, BETA-07 |
| Fix 56 | Example Contract Location | PROD-01, BETA-07 |
| Fix 57 | Synchronous Execution in v1.0 | MVP-05, BETA-07 |
| Fix 58 | Step Type Routing Only | BETA-04, BETA-07 |

---

## Linear Project Structure

```
Project: Contract-Driven Node Specs (OMN-496)
├── Milestone: NodeOrchestrator v1.0 MVP
│   ├── MVP-01: Core Enums & Primitives
│   ├── MVP-02: Core I/O Models
│   ├── MVP-03: Workflow Contract Models
│   ├── MVP-04: Validation & DAG Utilities
│   ├── MVP-05: Sequential Executor + NodeOrchestrator
│   └── MVP-06: MVP Conformance Tests
├── Milestone: NodeOrchestrator v1.0 Beta
│   ├── BETA-01: v1.0.1 Compliance
│   ├── BETA-02: v1.0.2 Compliance
│   ├── BETA-03: v1.0.3 Compliance
│   ├── BETA-04: v1.0.4 Compliance
│   ├── BETA-05: SPI Protocol Definitions
│   ├── BETA-06: Beta Integration Tests
│   └── BETA-07: v1.0.5 Compliance
└── Milestone: NodeOrchestrator v1.0 Production
    ├── PROD-01: Example Contracts
    ├── PROD-02: Performance Benchmarks
    ├── PROD-03: Documentation Updates
    └── PROD-04: Infrastructure Stubs
```

---

**Document Version**: 2.8
**Last Updated**: 2025-12-10
**Spec Version**: 1.0.5
**Author**: Generated from CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md (v1.0.5), consolidated structure
**v2.8 Changes**: Added v1.0.5 compliance (BETA-07 ticket, fixes 53-58); updated spec version references; updated test counts from 52 to 58 fixes
**v2.7 Changes**: Applied feedback - advisory classifications for over-specified rules; expanded BETA-06 tests; collapsed revision summaries

---

## Glossary

| Term | Definition |
|------|------------|
| **Wave** | A group of steps with no inter-dependencies that can logically execute together. Wave boundaries are determined by dependency topology, not metadata. Internal concept only—not exposed in public APIs. |
| **Contract** | A YAML or typed model definition describing a workflow's structure, steps, dependencies, and execution parameters. |
| **Executor** | The pure function (`execute_workflow`) that processes a workflow definition and emits actions. Stateless and side-effect-free. |
| **Orchestrator** | The `NodeOrchestrator` class—a stateful facade around the executor that holds `workflow_definition`. |
| **Action** | A `ModelAction` instance emitted by the executor representing work to be performed by a target node (NodeCompute, NodeEffect, NodeReducer). |
| **Step** | A `ModelWorkflowStep` instance representing a single unit of work within a workflow. |
| **Coordination Rules** | The `ModelCoordinationRules` model defining workflow-level policies (failure strategy, parallelism). |
| **Topological Order** | The dependency-respecting execution order of steps, computed using Kahn's algorithm. |
| **Lease** | A UUID proving orchestrator ownership of an action. Enables single-writer semantics. |
| **Epoch** | A monotonically increasing version number on actions. Used for optimistic concurrency control. |
| **Reserved Field** | A field defined in the spec but not semantically active in v1.0. Must be preserved but not executed. |

---

## Document Changelog

| Version | Theme | Key Changes |
|---------|-------|-------------|
| **v2.7** | Feedback Integration | Advisory classifications for over-specified rules; expanded BETA-06 test checklist; cross-version semantic equivalence; caching scope clarification; debug hook side-effect prohibition |
| **v2.6** | Comprehensive Enhancement | Semantic equivalence; canonical serialization; Pydantic immutability; step_type semantics table; troubleshooting guide; forward compatibility; debug hooks; testing infrastructure |
| **v2.5** | Structural Formalization | Executive summary; RFC 2119 notation; identifier normalization rules; formal wave algorithm; canonical tiebreaker hierarchy; state transition diagram; minimal contract example |
| **v2.4** | Final Polish | Normative vs informative classification; deterministic action_id; YAML type preservation; environment isolation; complexity thresholds; fixture mutability test |
| **v2.3** | Determinism Hardening | Semantic use definition; contract hashing; banned global state patterns; versioning invariant; error ordering matrix; JSON payload validator; reversion test |
| **v2.2** | Execution Model | Execution Model Rules section; wave formation prohibition; global registry prohibition; cross-version tests; regression-based benchmarks; glossary |
| **v2.1** | Layering & Wave Semantics | Repo boundaries; synchronous execution; wave logical construct notes; Reserved Semantics Rule; BETA ticket estimates; integration gate |
| **v2.0** | Initial Consolidated | Initial consolidated ticket breakdown from spec v1.0.4 |

For detailed change lists, see the git history of this document
