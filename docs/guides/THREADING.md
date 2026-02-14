> **Navigation**: [Home](../INDEX.md) > Guides > Thread Safety

# Thread Safety in Omnibase Core

## Overview

ONEX nodes are **single-request-scoped**. Each request creates its own node instance,
processes through handlers, and discards the instance. This design eliminates most
threading concerns at the architecture level.

**If you are reaching for locks, thread-local storage, or `ThreadPoolExecutor`, you
almost certainly need a different scoping boundary, not more synchronization.**

This document explains the concurrency model, the built-in debug tooling, and what
to do when you genuinely need parallelism.

---

## 1. Safety Rules

### Nodes Are Single-Request-Scoped

Every node instance (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR) is created for one
request and discarded after. This is enforced by convention and validated at runtime
via `ONEX_DEBUG_THREAD_SAFETY`.

```python
# CORRECT: Each request gets its own node instance.
async def handle_request(container, input_data):
    node = NodeEffect(container)
    node.effect_subcontract = subcontract
    return await node.process(input_data)

# WRONG: Sharing a node instance across requests/threads.
shared_node = NodeEffect(container)  # Created once, reused -- DO NOT DO THIS

async def handle_request(input_data):
    return await shared_node.process(input_data)  # Race conditions
```

### What Is Thread-Safe

| Component | Why |
|-----------|-----|
| `ModelONEXContainer` | Read-only after initialization |
| Frozen Pydantic models | Immutable by construction |
| `ModelValidatorSubcontract` | Frozen Pydantic model |
| `ModelValidationResult` | Frozen Pydantic model |
| Stateless mixin methods | No mutable state to corrupt |

### What Is NOT Thread-Safe

| Component | Mutable State |
|-----------|---------------|
| Node instances (all types) | Caches, circuit breakers, FSM state, workflow state |
| `ModelComputeCache` | LRU eviction, access counts |
| `ModelCircuitBreaker` | Failure counters, state transitions |
| `ModelEffectTransaction` | Operation list, rollback state |
| `ValidatorBase` / `ValidatorPatterns` | Internal file and rule caches |

**Mitigation for all of the above**: Create a new instance per request. Do not share
instances across threads or async tasks that may run concurrently.

### Shallow Immutability Warning

`frozen=True` on Pydantic models provides **shallow** immutability. Nested mutable
objects (dicts, lists) can still be modified in place:

```python
payload = ModelPayloadLogEvent(level="INFO", message="Test", context={"count": 0})

payload.level = "ERROR"           # Raises ValidationError (top-level frozen)
payload.context["count"] = 999    # Succeeds -- nested dict is NOT frozen
```

If multiple async tasks share a frozen model with mutable nested data, treat the
nested data as read-only, or use `model_copy(deep=True)` to create isolated copies.

---

## 2. `ONEX_DEBUG_THREAD_SAFETY`

ONEX provides a built-in runtime check that catches cross-thread node access during
development with zero overhead in production.

### How It Works

The flag is defined in `src/omnibase_core/constants/constants_effect.py`:

```python
DEBUG_THREAD_SAFETY: bool = os.environ.get("ONEX_DEBUG_THREAD_SAFETY", "0") == "1"
```

When enabled:

1. `MixinEffectExecution.__init__` records the creating thread's ID in
   `self._owner_thread_id`.
2. `_check_thread_safety()` is called at the entry of `execute_effect()` and
   `get_circuit_breaker()`. If the current thread differs from the owner, a
   `ModelOnexError` is raised with error code `THREAD_SAFETY_VIOLATION`.

When disabled (the default):

- `_owner_thread_id` is `None`.
- The check is `if self._owner_thread_id is not None:` which short-circuits
  immediately. Zero performance cost.

### Enabling

```bash
# Development / CI
export ONEX_DEBUG_THREAD_SAFETY=1
poetry run pytest tests/

# Disable (default -- zero overhead)
unset ONEX_DEBUG_THREAD_SAFETY
```

GitHub Actions example:

```yaml
- name: Run tests with thread safety validation
  env:
    ONEX_DEBUG_THREAD_SAFETY: "1"
  run: poetry run pytest tests/
```

### Error Output

When a violation is detected:

```text
ModelOnexError: Thread safety violation: node instance accessed from different thread
  error_code: ONEX_CORE_261_THREAD_SAFETY_VIOLATION
  context:
    owner_thread: 140234567890432
    current_thread: 140234567890999
    node_id: 550e8400-e29b-41d4-a716-446655440000
```

### Protected Methods

| Component | Method | Check |
|-----------|--------|-------|
| `MixinEffectExecution` | `execute_effect()` | Thread ID at entry |
| `NodeEffect` | `get_circuit_breaker()` | Thread ID at entry |
| `NodeEffect` | `process()` | Thread ID at entry |

### When to Use

- **Enable during**: development, CI, staging, performance testing (to catch races).
- **Disable in**: production (default), benchmarking.

---

## 3. Concurrency Model

Most ONEX workloads use asyncio, which is single-threaded. The architecture provides
three mechanisms for parallelism that do not require manual threading.

### Async Tasks for I/O-Bound Concurrency (Within a Node)

Use `asyncio.create_task` or `asyncio.gather` to run multiple I/O operations
concurrently within a single node's handler:

```python
async def execute_handler(self, input_data):
    # Fan out I/O operations concurrently within this handler.
    results = await asyncio.gather(
        self._fetch_user(input_data.user_id),
        self._fetch_permissions(input_data.user_id),
        self._fetch_preferences(input_data.user_id),
    )
    return self._merge_results(results)
```

No locks required -- all tasks run on the same event loop thread.

### Event Bus Fan-Out for Cross-Node Parallelism

When multiple independent nodes need to process in parallel, emit events and let
the event bus distribute work:

```python
# Orchestrator emits events; the bus delivers to independent node instances.
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

async def execute_orchestration(self, input_data):
    events = [
        ModelEventEnvelope(event_type="validate_schema", payload=input_data.schema),
        ModelEventEnvelope(event_type="validate_permissions", payload=input_data.auth),
        ModelEventEnvelope(event_type="validate_quota", payload=input_data.usage),
    ]
    return ModelHandlerOutput.for_orchestrator(
        input_envelope_id=input_envelope_id,  # from handler args
        correlation_id=correlation_id,         # from handler args
        events=events,
    )
```

Each event is handled by its own node instance -- no shared state, no locks.

### Separate Process Workers for CPU-Bound Parallelism

For CPU-bound work that would block the event loop, use orchestrator intents to
dispatch to worker processes:

```python
# Orchestrator emits an intent to run CPU-bound work in a separate process.
async def execute_orchestration(self, input_data):
    intents = [
        ModelIntent(
            action="spawn_worker",
            payload={"task": "compress_dataset", "data_ref": input_data.data_ref},
        ),
    ]
    return ModelHandlerOutput.for_orchestrator(
        input_envelope_id=input_envelope_id,  # from handler args
        correlation_id=correlation_id,         # from handler args
        intents=intents,
    )
```

The worker process creates its own node instances. No state is shared across the
process boundary.

### Per-Request Node Instances Replace Shared Instances with Locks

The old pattern of creating one node instance and wrapping it with locks is
never correct in ONEX:

```python
# WRONG: Shared instance + lock
shared_node = NodeCompute(container)
lock = threading.Lock()

async def handle(data):
    with lock:
        return await shared_node.process(data)  # Serializes all requests

# CORRECT: Per-request instance
async def handle(data):
    node = NodeCompute(container)  # Fresh instance, no lock needed
    return await node.process(data)
```

---

## 4. Replacement Checklist

If you think you need a threading primitive, use this checklist to find the
correct architectural pattern instead.

| You Think You Need | You Actually Need |
|--------------------|-------------------|
| `threading.Lock` / `RLock` | A different scoping boundary. Create per-request instances instead of sharing one instance with a lock. |
| `ThreadPoolExecutor` | Event bus fan-out (cross-node) or `asyncio.gather` (within-node). For CPU-bound work, use orchestrator intents to spawn worker processes. |
| `threading.local()` | Per-request instance creation. The request handler creates a fresh node; no thread-local storage needed. |
| `threading.Timer` | The `EFFECT_TIMEOUT_BEHAVIOR` subcontract. See [EFFECT_TIMEOUT_BEHAVIOR.md](../architecture/EFFECT_TIMEOUT_BEHAVIOR.md). |
| `threading.Semaphore` | Rate limiting via the effect subcontract's circuit breaker configuration or an external rate limiter service. |
| Shared mutable cache | Per-request computation (COMPUTE nodes are cheap) or an external cache service accessed via an EFFECT node. |

---

## 5. Timeouts and Cancellation

Timeouts in ONEX are contract-driven, not manual-threading-driven.

### Effect Operation Timeout

The `operation_timeout_ms` field in the effect subcontract controls overall timeout
including retries. The timeout is checked **before** each retry attempt, not during
operation execution. See [EFFECT_TIMEOUT_BEHAVIOR.md](../architecture/EFFECT_TIMEOUT_BEHAVIOR.md)
for the full specification.

```yaml
effect_subcontract:
  operations:
    - operation_name: "fetch_data"
      operation_timeout_ms: 60000      # 60s for full operation including retries
      io_config:
        handler_type: http
        timeout_ms: 10000              # 10s per individual HTTP call
      max_retries: 3
```

**Key behaviors**:

- Timeout is checked at the start of each retry attempt, not mid-operation.
- In-flight operations run to completion (no mid-execution interruption).
- Handler-level `timeout_ms` controls individual call duration.
- `operation_timeout_ms` guards the entire retry loop.

### Compute Pipeline Timeout

The `pipeline_timeout_ms` field in `ModelComputeSubcontract` wraps execution in a
`ThreadPoolExecutor` with `future.result(timeout=...)`. If the timeout fires, the
background thread (a daemon thread) continues running but its result is discarded.
Daemon threads are terminated automatically on process exit.

### Cancellation Signals

Cancellation signals (`SystemExit`, `KeyboardInterrupt`, `asyncio.CancelledError`)
always propagate through the decorator contract. They are never caught or wrapped.

---

## 6. Container and Service Registry Thread Safety

`ModelONEXContainer` is safe to share across threads after initialization:

- Service registration happens once during startup.
- `get_service()` performs a read-only dictionary lookup.
- `initialize_service_registry()` uses an internal lock for one-time initialization.

**However**, individual services resolved from the container may not be thread-safe.
Check each service's documentation. When in doubt, resolve the service per request.

---

## 7. Validator Thread Safety Note

Validators (`ValidatorBase`, `ValidatorPatterns`, etc.) are NOT thread-safe due to
internal mutable caches (`_file_line_cache`, `_rule_config_cache`).

The `parallel_execution: true` field in validator YAML contracts indicates
**process-safe** parallel execution (e.g., pytest-xdist workers), NOT thread-safe
execution within a process. Each xdist worker is a separate process with its own
validator instances.

For validation work, create a fresh validator instance per validation call or per
thread. Frozen contract models (`ModelValidatorSubcontract`, `ModelValidationResult`,
`ModelValidationIssue`) are safe to share.

---

## 8. Production Checklist

Before deploying ONEX nodes in production:

### Architecture Verification

- [ ] **Per-request node instances**: No node instances are shared across requests
      or threads. Each request creates and discards its own.
- [ ] **No manual locks on nodes**: No `threading.Lock` wrapping node access.
      If locks exist, the scoping boundary is wrong.
- [ ] **Event bus for fan-out**: Cross-node parallelism uses event bus dispatch,
      not shared memory or thread pools.

### Runtime Validation

- [ ] **`ONEX_DEBUG_THREAD_SAFETY=1` in CI**: Thread safety checks enabled in
      the test suite to catch violations early.
- [ ] **No `run_in_executor` with shared nodes**: If `asyncio.run_in_executor`
      is used, the executor callback creates its own node instances.

### Timeout Configuration

- [ ] **Handler timeout <= operation timeout**: Individual call timeouts fire before
      the overall operation timeout. See [EFFECT_TIMEOUT_BEHAVIOR.md](../architecture/EFFECT_TIMEOUT_BEHAVIOR.md).
- [ ] **Timeout values account for backoff**: With exponential backoff and retries,
      total time grows quickly. Set `operation_timeout_ms` accordingly.

### Monitoring

- [ ] **Thread count baseline**: Monitor `threading.active_count()` for unexpected
      growth from compute pipeline timeouts (daemon threads may accumulate under
      heavy timeout load).
- [ ] **Circuit breaker state**: Monitor circuit breaker transitions for reliability
      issues in EFFECT nodes.
- [ ] **Timeout events logged**: Effect timeout occurrences are observable for
      tuning timeout values.

### Resource Cleanup

- [ ] **Graceful shutdown**: Process exit cleanly terminates daemon threads from
      compute pipeline timeouts (Python handles this automatically for daemon threads).
- [ ] **Transaction isolation**: Each effect operation creates its own transaction.
      No transaction objects are shared across concurrent operations.

---

## References

| Topic | Document |
|-------|----------|
| Effect timeout specification | [EFFECT_TIMEOUT_BEHAVIOR.md](../architecture/EFFECT_TIMEOUT_BEHAVIOR.md) |
| NodeEffect architecture | [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](../architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md) |
| Four-node architecture | [ONEX_FOUR_NODE_ARCHITECTURE.md](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |
| Debug thread safety constant | [constants_effect.py](../../src/omnibase_core/constants/constants_effect.py) |
| Effect execution mixin | [mixin_effect_execution.py](../../src/omnibase_core/mixins/mixin_effect_execution.py) |

---

## Design Rationale

ONEX nodes are intentionally NOT thread-safe by default because:

1. **Single-request scoping eliminates the problem**: When each request gets its own
   node instance, there is nothing to synchronize.
2. **AsyncIO is single-threaded**: The event loop model avoids races without locks.
3. **Event bus handles fan-out**: Cross-node parallelism is message-based, not
   shared-memory-based.
4. **Locks add complexity and overhead**: Synchronization primitives are a symptom of
   incorrect scoping, not a solution.

**Default assumption**: Unless explicitly documented as thread-safe, assume components
require their own instance per request.
