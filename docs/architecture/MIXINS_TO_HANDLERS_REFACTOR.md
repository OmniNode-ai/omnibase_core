# Mixins to Handlers Refactor

**Status**: Draft
**Version**: 0.1.0
**Last Updated**: 2025-12-30
**Related Tickets**: OMN-1113, OMN-1114, OMN-1116, OMN-1162

---

## Table of Contents

1. [Current Mixin Architecture](#section-1-current-mixin-architecture)
2. [Handler Architecture Vision](#section-2-handler-architecture-vision)
3. [Migration Strategy](#section-3-migration-strategy)
4. [Canonical Hooks](#section-4-canonical-hooks)
5. [Handler Type Categories](#section-5-handler-type-categories)
6. [Contract Integration](#section-6-contract-integration)
7. [Determinism and Replay Invariants](#section-7-determinism-and-replay-invariants)
8. [Capability Activation](#section-8-capability-activation)
9. [The Manifest](#section-9-the-manifest)
10. [Ordering Guarantees](#section-10-ordering-guarantees)
11. [Testing Strategy](#section-11-testing-strategy)

---

## Section 1: Current Mixin Architecture

### Overview

The current ONEX system uses Python mixins for cross-cutting concerns:

```text
src/omnibase_core/mixins/
├── mixin_circuit_breaker.py
├── mixin_discovery_responder.py
├── mixin_event_handler.py
├── mixin_event_listener.py
├── mixin_health_check.py
├── mixin_introspection.py
├── mixin_metrics.py
├── mixin_node_executor.py
├── mixin_node_lifecycle.py
├── mixin_request_response_introspection.py
├── mixin_retry.py
├── mixin_service_resolution.py
└── mixin_workflow_execution.py
```

### Pain Points

1. **Tight Coupling**: Mixins inherit from node classes, creating inheritance hierarchies
2. **Testing Challenges**: Hard to test mixins in isolation
3. **Ordering Ambiguity**: MRO (Method Resolution Order) determines behavior, not explicit configuration
4. **Composition Complexity**: Diamond inheritance problems with multiple mixins
5. **Runtime Introspection**: Difficult to understand what capabilities are active

---

## Section 2: Handler Architecture Vision

### Capability/Handler Pattern

Replace inheritance-based mixins with composition-based handlers:

```python
# OLD: Mixin-based
class MyNode(NodeCompute, MixinRetry, MixinCircuitBreaker, MixinMetrics):
    pass

# NEW: Handler-based
pipeline = PipelineRunner(
    hooks=[
        RetryHook(max_attempts=3),
        CircuitBreakerHook(threshold=5),
        MetricsHook(namespace="my_node"),
    ]
)
result = await pipeline.execute(node, envelope)
```

### Benefits

1. **Loose Coupling**: Handlers are independent, composable units
2. **Testability**: Each handler tested in isolation
3. **Explicit Ordering**: Configuration determines execution order
4. **Runtime Visibility**: Manifest records exactly what ran and why
5. **Determinism**: Same inputs → same outputs (for replay)

---

## Section 3: Migration Strategy

### Phase 1: Infrastructure (Current)

**Tickets**: OMN-1114 (Pipeline Runner & Hook Registry)

- Implement `PipelineRunner` core execution engine
- Implement `HookRegistry` for hook discovery and ordering
- Define `ModelPipelineHook` and `ModelExecutionPlan`
- Integration with `ModelExecutionProfile`

### Phase 2: Handler Abstractions

- Define handler protocols in `omnibase_spi`
- Create adapter layer for existing mixins
- Gradual migration of individual capabilities

### Phase 3: Gradual Mixin Deprecation

- Mark mixins as deprecated
- Provide migration guides
- Dual-mode support (mixin OR handler)

### Phase 4: Full Handler Adoption

- Remove mixin inheritance
- All capabilities via handlers
- Complete manifest coverage

---

## Section 4: Canonical Hooks

### Hook Phases

Hooks execute in strict phase order:

| Phase | Purpose | Example Hooks |
|-------|---------|---------------|
| **PREFLIGHT** | Validation, authorization | AuthHook, SchemaValidationHook |
| **BEFORE** | Setup, context preparation | ContextSetupHook, CacheWarmHook |
| **EXECUTE** | Core logic wrapping | RetryHook, CircuitBreakerHook, TimeoutHook |
| **AFTER** | Post-processing, cleanup | MetricsHook, AuditHook |
| **EMIT** | Event publishing | EventEmitHook, NotificationHook |
| **FINALIZE** | Guaranteed cleanup | ResourceCleanupHook, SpanCloseHook |

### Hook Interface

```python
class ProtocolPipelineHook(Protocol):
    """Hook that wraps pipeline execution."""

    @property
    def hook_id(self) -> str:
        """Unique identifier for this hook instance."""
        ...

    @property
    def phase(self) -> EnumExecutionPhase:
        """Which phase this hook executes in."""
        ...

    @property
    def priority(self) -> int:
        """Ordering within phase (lower = earlier)."""
        ...

    async def execute(
        self,
        context: ModelHookContext,
        next_hook: Callable[..., Awaitable[ModelHookResult]],
    ) -> ModelHookResult:
        """Execute hook logic, calling next_hook to continue chain."""
        ...
```

---

## Section 5: Handler Type Categories

### EnumHandlerTypeCategory

```python
class EnumHandlerTypeCategory(str, Enum):
    COMPUTE = "compute"  # Deterministic, no I/O, replay-safe
    EFFECT = "effect"    # External I/O, requires stubbing for replay
    NONDETERMINISTIC_COMPUTE = "nondeterministic_compute"  # Internal randomness
```

### Category Implications

| Category | Deterministic | I/O | Replay Behavior |
|----------|---------------|-----|-----------------|
| COMPUTE | Yes | No | Re-execute |
| EFFECT | No | Yes | Stub from recording |
| NONDETERMINISTIC_COMPUTE | No | No | Stub RNG seed |

### Cross-Cutting Handlers

Some handlers apply across categories:

- **MetricsHook**: Records to all handler types
- **LoggingHook**: Logs all executions
- **TracingHook**: Spans all handlers

---

## Section 6: Contract Integration

### Contract-Driven Hook Registration

Hooks can be declared in contracts:

```yaml
# node contract
execution_profile:
  phases:
    preflight:
      hooks:
        - hook_id: "auth_check"
          priority: 100
    execute:
      hooks:
        - hook_id: "retry"
          config:
            max_attempts: 3
            backoff_ms: 100
```

### Execution Profile Mapping

`ModelExecutionProfile` maps directly to hook phases:

```python
class ModelExecutionProfile(BaseModel):
    preflight: ModelPhaseConfig
    before: ModelPhaseConfig
    execute: ModelPhaseConfig
    after: ModelPhaseConfig
    emit: ModelPhaseConfig
    finalize: ModelPhaseConfig
```

---

## Section 7: Determinism and Replay Invariants

**Reference Ticket**: OMN-1116 (Replay Infrastructure)

### Determinism Requirements

For replay to work, executions must be deterministic given:

1. **Same Input Envelope**: Identical payload and metadata
2. **Same Contract**: Identical hook configuration
3. **Same Time**: Injected time source
4. **Same RNG**: Injected random seed
5. **Stubbed Effects**: External calls replaced with recordings

### Replay Invariants

```python
# Invariant: Same inputs → Same manifest
manifest_1 = await pipeline.execute(node, envelope, time=T, rng=R, effects=STUBS)
manifest_2 = await pipeline.execute(node, envelope, time=T, rng=R, effects=STUBS)
assert manifest_1.hook_trace == manifest_2.hook_trace
assert manifest_1.ordering == manifest_2.ordering
```

### Time Injection

```python
class TimeInjector:
    def __init__(self, fixed_time: datetime | None = None):
        self._fixed = fixed_time

    def now(self) -> datetime:
        return self._fixed or datetime.utcnow()
```

### RNG Injection

```python
class RNGInjector:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def random(self) -> float:
        return self._rng.random()
```

---

## Section 8: Capability Activation

### Activation Reasons

Every activated capability must record WHY it activated:

```python
class ModelActivationReason(BaseModel):
    """Why a capability was activated."""

    predicate_name: str | None = None
    """Name of the predicate that matched (e.g., 'contract_requires_retry')."""

    predicate_result: bool
    """Result of predicate evaluation."""

    inputs_used: dict[str, Any] = {}
    """Inputs that influenced the decision."""

    source: ModelActivationSource
    """Where the activation came from."""

class ModelActivationSource(BaseModel):
    """Source of capability activation."""

    contract_path: str | None = None
    """Path to contract file if contract-driven."""

    config_source: str | None = None
    """Configuration source (env, file, default)."""

    activation_type: Literal["static", "dynamic"]
    """Static (contract) vs dynamic (runtime condition)."""
```

### Activation Flow

1. Load contract
2. Evaluate predicates for each potential capability
3. Record activation reason for each activated capability
4. Build execution plan with ordering

---

## Section 9: The Manifest

**Reference Ticket**: OMN-1113 (Manifest Generation & Observability)

### Purpose

The execution manifest answers: **"What ran, why, in what order, and what happened?"**

It is:
- **Deterministic**: Same inputs produce same manifest structure
- **Replay-friendly**: Contains all information needed for replay
- **Ledger-safe**: Fully serializable for persistence and audit

### Non-Goals

The manifest is NOT:
- Docker Compose metadata
- Mixin definitions
- Configuration files

It IS:
- Runtime execution trace
- Activation proof
- Ordering record
- Failure log

### Manifest Structure

```python
class ModelExecutionManifest(BaseModel):
    """Complete execution manifest for a pipeline run."""

    # === Identity ===
    manifest_id: str
    """Unique identifier for this manifest (UUID)."""

    created_at: datetime
    """When the manifest was created."""

    correlation_id: str
    """Correlation ID from the input envelope."""

    pipeline_id: str
    """Identifier for the pipeline configuration."""

    # === Runtime Identity ===
    runtime_identity: ModelRuntimeIdentity
    """Identity of the runtime that executed this."""

    # === Node Identity ===
    node_identity: ModelNodeIdentity
    """Identity of the node that was executed."""

    # === Contract Identity ===
    contract_identity: ModelContractIdentity
    """Identity of the contract that governed execution."""

    # === Activation ===
    activation_summary: ModelActivationSummary
    """Summary of activated capabilities and reasons."""

    # === Ordering ===
    ordering_summary: ModelOrderingSummary
    """Resolved ordering of hooks and phases."""

    # === Execution Trace ===
    hook_trace: list[ModelHookTraceEntry]
    """Per-hook execution trace."""

    # === Emissions ===
    emissions_summary: ModelEmissionsSummary
    """Summary of emitted events, intents, projections."""

    # === Metrics ===
    metrics_summary: ModelMetricsSummary
    """Execution metrics and timing."""

    # === Failures ===
    failures: list[ModelFailureEntry]
    """Any failures that occurred."""
```

### Identity Models

```python
class ModelRuntimeIdentity(BaseModel):
    """Identity of the runtime environment."""
    runtime_id: str
    runtime_version: str
    host_id: str | None = None

class ModelNodeIdentity(BaseModel):
    """Identity of the executed node."""
    node_id: str
    node_kind: EnumNodeKind
    node_version: str | None = None
    handler_id: str | None = None

class ModelContractIdentity(BaseModel):
    """Identity of the governing contract."""
    contract_type: str
    contract_id: str
    contract_path: str | None = None
    contract_version: str
    contract_hash: str | None = None
```

### Activation Summary

```python
class ModelActivationSummary(BaseModel):
    """Summary of capability activations."""

    activated_capabilities: list[ModelActivatedCapability]
    """List of capabilities that were activated."""

    skipped_capabilities: list[ModelSkippedCapability]
    """List of capabilities that were not activated (with reasons)."""

class ModelActivatedCapability(BaseModel):
    """A capability that was activated."""
    capability_id: str
    activation_reason: ModelActivationReason
    source: ModelActivationSource
    ordering: ModelCapabilityOrdering

class ModelCapabilityOrdering(BaseModel):
    """Ordering information for a capability."""
    phase: EnumExecutionPhase
    priority: int
    dependencies_resolved: list[str]
```

### Hook Trace

```python
class ModelHookTraceEntry(BaseModel):
    """Trace entry for a single hook execution."""

    hook_id: str
    """Unique identifier for the hook instance."""

    phase: EnumExecutionPhase
    """Phase the hook executed in."""

    handler_type_category: EnumHandlerTypeCategory | None = None
    """Handler type category if applicable."""

    capability_id: str | None = None
    """Owning capability if part of a capability."""

    # === Execution Status ===
    status: Literal["success", "failed", "skipped"]
    """Final status of hook execution."""

    # === Timing ===
    start_ts: datetime
    """When hook execution started."""

    end_ts: datetime
    """When hook execution ended."""

    duration_ms: float
    """Duration in milliseconds."""

    # === Skip Reason ===
    skip_reason: str | None = None
    """If skipped, why."""

    # === Error ===
    error: ModelHookError | None = None
    """If failed, error details."""

class ModelHookError(BaseModel):
    """Error information for a failed hook."""
    error_type: str
    message: str
    traceback_ref: str | None = None
    """Reference to full traceback (not inline)."""
```

### Ordering Summary

```python
class ModelOrderingSummary(BaseModel):
    """Summary of resolved execution ordering."""

    phases_in_order: list[EnumExecutionPhase]
    """Canonical phase ordering."""

    per_phase_ordering: dict[str, list[ModelPhaseHookOrder]]
    """Ordered hooks within each phase."""

    dependency_graph: dict[str, list[str]]
    """Dependency edges between hooks."""

    topological_order: list[str]
    """Final resolved topological ordering."""

class ModelPhaseHookOrder(BaseModel):
    """Hook ordering within a phase."""
    hook_id: str
    priority: int
    depends_on: list[str]
```

### Emissions Summary

```python
class ModelEmissionsSummary(BaseModel):
    """Summary of emissions (events, intents, projections)."""

    emitted_events: ModelEmittedItems
    emitted_intents: ModelEmittedItems
    emitted_projections: ModelEmittedItems

class ModelEmittedItems(BaseModel):
    """Summary of emitted items."""
    count: int
    ids: list[str]
    """IDs or hashes of emitted items."""
    types: list[str]
    """Types of emitted items."""
    topics: list[str] = []
    """Topics if applicable."""
```

### Metrics Summary

```python
class ModelMetricsSummary(BaseModel):
    """Execution metrics."""

    total_duration_ms: float
    """Total execution time."""

    per_phase_duration_ms: dict[str, float]
    """Duration per phase."""

    hooks_executed: int
    """Number of hooks executed."""

    hooks_skipped: int
    """Number of hooks skipped."""

    hooks_failed: int
    """Number of hooks that failed."""
```

### Failure Entry

```python
class ModelFailureEntry(BaseModel):
    """A failure that occurred during execution."""

    failure_id: str
    """Unique identifier for this failure."""

    hook_id: str | None = None
    """Hook that failed, if applicable."""

    phase: EnumExecutionPhase | None = None
    """Phase where failure occurred."""

    error_type: str
    """Type of error."""

    message: str
    """Error message (may be truncated)."""

    traceback_ref: str | None = None
    """Reference to full traceback."""

    occurred_at: datetime
    """When the failure occurred."""

    recoverable: bool = False
    """Whether execution continued after this failure."""
```

### Determinism Guarantee

The manifest MUST be deterministic given:

1. Same contract + registry + rules → same `activation_summary`
2. Same hooks + priorities + dependencies → same `ordering_summary`
3. Same inputs + stubbed effects → same `hook_trace` (status, timing patterns)

Record the ordering inputs explicitly:

```python
class ModelOrderingInputs(BaseModel):
    """Inputs that determined ordering."""
    hook_set: list[str]
    priorities: dict[str, int]
    dependency_edges: dict[str, list[str]]
    selected_phases: list[EnumExecutionPhase]
```

---

## Section 10: Ordering Guarantees

### Phase Ordering

Phases execute in strict order:

```text
PREFLIGHT → BEFORE → EXECUTE → AFTER → EMIT → FINALIZE
```

### Within-Phase Ordering

Within each phase:

1. Sort by `priority` (ascending, lower = earlier)
2. Stable sort by definition order (for equal priority)
3. Respect explicit dependencies

### Dependency Resolution

```python
# Hook B depends on Hook A
hook_a = RetryHook(hook_id="retry", priority=100)
hook_b = MetricsHook(hook_id="metrics", priority=200, depends_on=["retry"])

# Execution order: retry → metrics (even if priorities were reversed)
```

### Circular Dependency Detection

Circular dependencies are detected at plan build time and raise `ModelOnexError(CIRCULAR_DEPENDENCY)`.

---

## Section 11: Testing Strategy

**Reference Ticket**: OMN-1109 (Testing Suite - Golden & Interaction Tests)

### Golden Manifest Tests

```python
def test_golden_manifest_structure():
    """Verify manifest has all required fields."""
    manifest = generate_manifest(node, envelope, contract)

    assert manifest.manifest_id
    assert manifest.correlation_id == envelope.correlation_id
    assert len(manifest.hook_trace) > 0
    assert manifest.metrics_summary.total_duration_ms >= 0
```

### Activation Reason Tests

```python
def test_activation_reason_tracking():
    """Verify activation reasons are recorded."""
    manifest = generate_manifest(node, envelope, contract_with_retry)

    retry_cap = next(
        c for c in manifest.activation_summary.activated_capabilities
        if c.capability_id == "retry"
    )
    assert retry_cap.activation_reason.predicate_name == "contract_requires_retry"
    assert retry_cap.activation_reason.predicate_result is True
```

### Hook Trace Tests

```python
def test_hook_trace_completeness():
    """Verify all hooks are traced."""
    manifest = generate_manifest(node, envelope, contract)

    for entry in manifest.hook_trace:
        assert entry.hook_id
        assert entry.phase
        assert entry.status in ("success", "failed", "skipped")
        assert entry.duration_ms >= 0
```

### Interaction Tests

```python
def test_retry_idempotency_interaction():
    """Retry + Idempotency hooks interact correctly."""
    # ...

def test_timeout_circuit_breaker_interaction():
    """Timeout + CircuitBreaker hooks interact correctly."""
    # ...

def test_redaction_logging_interaction():
    """Redaction + Logging hooks interact correctly."""
    # ...
```

---

## Related Documents

- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Mixin Architecture](MIXIN_ARCHITECTURE.md)
- [Contract System](CONTRACT_SYSTEM.md)
- [Execution Profile](../guides/TESTING_GUIDE.md)

## Related Tickets

- **OMN-1113**: Manifest Generation & Observability (Section 9)
- **OMN-1114**: Pipeline Runner & Hook Registry (Section 4)
- **OMN-1116**: Replay Infrastructure (Section 7)
- **OMN-1109**: Testing Suite (Section 11)
- **OMN-1162**: This document
- **OMN-1163**: Manifest Persistence (omnibase_infra)
