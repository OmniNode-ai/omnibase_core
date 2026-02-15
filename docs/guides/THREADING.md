> **Navigation**: [Home](../INDEX.md) > Guides > Thread Safety

# Thread Safety in Omnibase Core

## Overview

This document explains the concurrency model and thread safety guarantees for ONEX nodes. Understanding these guarantees is critical for production multi-threaded environments.

**Key Takeaway**: Most ONEX node components are **NOT thread-safe by default**. Careful synchronization is required for concurrent usage.

## Thread Safety Warnings Summary

This section consolidates all critical thread safety warnings for quick reference.

### Critical Warnings

| Component | Risk Level | Issue | Mitigation |
|-----------|------------|-------|------------|
| `NodeCompute` | High | Cache operations not atomic | Use thread-local instances or locked cache |
| `NodeEffect` | Critical | Circuit breaker state corruption | Use thread-local instances (recommended) |
| `NodeReducer` | High | FSM state is mutable | Use thread-local instances |
| `NodeOrchestrator` | High | Workflow state is mutable | Use thread-local instances |
| `ModelComputeCache` | High | LRU eviction races | Wrap with `threading.Lock` |
| `ModelCircuitBreaker` | High | Counter/state races | Use locks or thread-local instances |
| `ModelEffectTransaction` | Critical | Rollback assumes single-thread | Never share across threads |
| `ValidatorBase` | High | File cache not synchronized | Use thread-local instances |
| `ValidatorPatterns` | High | Rule cache not synchronized | Use thread-local instances |

### Safe Components

| Component | Notes |
|-----------|-------|
| `ModelONEXContainer` | Read-only after initialization |
| Pydantic Models | Immutable after creation |
| Input/Output Models | Frozen via Pydantic |
| Workflow Contract Models | Frozen via Pydantic (v0.4.0+) - see [Workflow Contract Models](#workflow-contract-models-v040) |
| Stateless Mixin Methods | Safe if inputs are thread-safe |
| `ModelValidatorSubcontract` | Frozen Pydantic model - safe to share |
| `ModelValidationResult` | Frozen Pydantic model |

### Quick Decision Guide

1. **Creating a multi-threaded service?** Use thread-local node instances (Option 1 patterns below)
2. **Need shared state?** Add explicit synchronization with `threading.Lock`
3. **Using asyncio only?** Single-threaded event loop avoids most races (but watch for `run_in_executor`)
4. **Production deployment?** Complete the [Production Checklist](#production-checklist) at the end of this document

## NodeCompute Thread Safety

### Parallel Processing

`NodeCompute` uses `ThreadPoolExecutor` for parallel batch processing:

- **Thread-Safe**: Input/output models (immutable after creation via Pydantic)
- **NOT Thread-Safe**: Internal cache state (requires synchronization)
- **Recommendation**: Use separate NodeCompute instances per thread OR implement cache locking

### Computation Cache

#### Current Implementation: NOT Thread-Safe by Default

The `ModelComputeCache` LRU cache operations are not atomic:
- Concurrent `get()` calls can race with `put()` operations
- LRU eviction logic can corrupt cache state under concurrent access
- Access count updates are not atomic

#### Mitigation: Add threading.Lock for Production Use

Example of thread-safe cache wrapper:

```python
from collections.abc import Callable
from threading import Lock
from typing import Any

from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache

class ThreadSafeComputeCache:
    """Thread-safe wrapper for ModelComputeCache.

    Use this wrapper in production environments where NodeCompute
    instances are shared across threads.
    """

    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
        self._cache = ModelComputeCache(max_size, default_ttl_minutes)
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        """Thread-safe cache retrieval."""
        with self._lock:
            return self._cache.get(key)

    def put(self, key: str, value: Any, ttl_minutes: int | None = None) -> None:
        """Thread-safe cache storage."""
        with self._lock:
            self._cache.put(key, value, ttl_minutes)

    def clear(self) -> None:
        """Thread-safe cache clearing."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, int | float]:
        """Thread-safe cache statistics."""
        with self._lock:
            return self._cache.get_stats()

    def compute_if_absent(
        self,
        key: str,
        compute_fn: Callable[[str], Any],
        ttl_minutes: int | None = None,
    ) -> Any:
        """
        Atomically compute and cache value if absent.

        This method prevents race conditions by holding the lock
        during both the cache check and computation.

        Args:
            key: Cache key
            compute_fn: Function to compute value if absent (receives key as arg)
            ttl_minutes: Optional TTL override

        Returns:
            Cached or newly computed value
        """
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

            result = compute_fn(key)
            self._cache.put(key, result, ttl_minutes)
            return result
```

### Cache Synchronization Strategies

#### Option 1: Per-Thread NodeCompute Instances (Recommended)

```python
import threading
from omnibase_core.nodes.node_compute import NodeCompute

# Thread-local storage for NodeCompute instances
thread_local = threading.local()

def get_compute_node(container):
    """Get or create thread-local NodeCompute instance."""
    if not hasattr(thread_local, 'compute_node'):
        thread_local.compute_node = NodeCompute(container)
    return thread_local.compute_node

# Usage in multithreaded context
async def process_computation(data):
    compute_node = get_compute_node(my_container)
    return await compute_node.process(data)
```

#### Option 2: Shared NodeCompute with Locked Cache

```python
from omnibase_core.nodes.node_compute import NodeCompute

# Create NodeCompute instance
compute_node = NodeCompute(container)

# Replace cache with thread-safe version
compute_node.computation_cache = ThreadSafeComputeCache(
    max_size=1000,
    default_ttl_minutes=30
)

# Now safe to share across threads
```

**Important Atomicity Note**: While the `ThreadSafeComputeCache` wrapper makes individual `get()` and `put()` operations thread-safe, the common cache pattern of "check cache → compute if missing → cache result" requires special handling. For atomic compute-and-cache operations, use the `compute_if_absent()` method (shown above), which holds the lock during the entire check-compute-cache sequence. Alternatively, use Option 1 (per-thread instances) to avoid coordination overhead entirely.

## NodeEffect and MixinEffectExecution Thread Safety

⚠️ **CRITICAL**: NodeEffect instances contain circuit breaker state that is **NOT thread-safe**.

### Thread Safety Matrix

| Component | Thread-Safe? | Action Required |
|-----------|-------------|-----------------|
| `NodeEffect` | ❌ No | Use separate instances per thread |
| `MixinEffectExecution._circuit_breakers` | ❌ No | Process-local, single-thread only |
| `MixinEffectExecution` methods | ⚠️ Stateless | Safe if called with thread-safe inputs |
| `ModelEffectSubcontract` | ✅ Yes | Immutable after creation |
| `ModelEffectInput` / `ModelEffectOutput` | ✅ Yes | Frozen Pydantic models |
| `EffectIOConfig` models | ✅ Yes | Frozen Pydantic models |
| `ModelCircuitBreaker` | ❌ No | Use locks or thread-local instances |
| `ModelEffectTransaction` | ❌ No | Never share across threads |

### Why NodeEffect is NOT Thread-Safe

#### Circuit Breaker State

- Circuit breakers are stored in `_circuit_breakers` instance dictionary
- Keyed by `operation_id` (UUID) for per-operation failure tracking
- State includes failure counters, timestamps, and state transitions
- No synchronization primitives (by design for performance)

#### State Race Conditions

- `failure_count` increments are not atomic
- `last_failure_time` updates can race
- Multiple threads may incorrectly trip/reset breaker state
- Dictionary updates (`_circuit_breakers[op_id] = breaker`) are not atomic

#### Dictionary Update Thread Safety (CRITICAL)

The `_circuit_breakers` dictionary itself is subject to race conditions:

```text
# Race condition in _check_circuit_breaker() and _record_circuit_breaker_result()
# Thread 1 and Thread 2 both check for operation_id simultaneously:

# Thread 1                          # Thread 2
if op_id not in self._circuit_breakers:  # True
                                    if op_id not in self._circuit_breakers:  # True
    breaker = ModelCircuitBreaker.create_resilient()
    self._circuit_breakers[op_id] = breaker  # Creates breaker
                                    breaker = ModelCircuitBreaker.create_resilient()
                                    self._circuit_breakers[op_id] = breaker  # Overwrites!

# Result: Thread 1's circuit breaker state is lost
# Both threads now use Thread 2's breaker, losing failure tracking from Thread 1
```

This is why **thread-local NodeEffect instances are strongly recommended** - each thread
maintains its own `_circuit_breakers` dictionary with no possibility of race conditions.

#### Impact Under Concurrent Load

- Circuit breakers may fail to trip when they should (missed failures)
- Circuit breakers may trip prematurely (double-counted failures)
- Circuit breakers may reset incorrectly (race on success counter)
- State corruption can lead to incorrect open/closed/half-open transitions

### Mixin Method Safety

The `MixinEffectExecution` mixin methods are **stateless** and operate on passed arguments:
- `execute_effect()` - Safe if inputs are thread-safe
- `_resolve_io_context()` - Pure function, thread-safe
- `_parse_io_config()` - Pure function, thread-safe
- `_extract_field()` - Pure function, thread-safe

**However**, these methods access `self._circuit_breakers`, making the **overall operation NOT thread-safe**.

### Usage Patterns

#### Incorrect: Sharing NodeEffect Across Threads

```python
# UNSAFE - Circuit breaker state will be corrupted
node = NodeEffect(container)
node.effect_subcontract = subcontract

async def worker_1():
    await node.process(input_1)  # Race on _circuit_breakers!

async def worker_2():
    await node.process(input_2)  # Race on _circuit_breakers!

# Both threads share the same _circuit_breakers dict
# Concurrent access will corrupt circuit breaker state
```

#### Correct: Separate Instance Per Thread

```python
import threading
from omnibase_core.nodes import NodeEffect

# Thread-local storage for NodeEffect instances
thread_local = threading.local()

def get_effect_node(container, subcontract):
    """Get or create thread-local NodeEffect instance."""
    if not hasattr(thread_local, 'effect_node'):
        node = NodeEffect(container)
        node.effect_subcontract = subcontract
        thread_local.effect_node = node
    return thread_local.effect_node

# Each thread gets its own instance with isolated circuit breaker state
async def worker_1():
    node = get_effect_node(my_container, my_subcontract)
    await node.process(input_1)  # No race - separate instance

async def worker_2():
    node = get_effect_node(my_container, my_subcontract)
    await node.process(input_2)  # No race - separate instance
```

### Mitigation Options

**Choosing Between Options**:
- **Option 1 (Sequential Execution)**: Best for asyncio-based applications where you want a single shared node instance with serialized access. Simpler setup but creates a bottleneck under high concurrency.
- **Option 2 (Thread-Local Instances)**: Best for multi-threaded applications (e.g., using `ThreadPoolExecutor`). Each thread gets independent state with no coordination overhead, enabling true parallelism.

For most production use cases, **Option 2 is preferred** as it provides better throughput under concurrent load.

#### Option 1: Sequential Execution (Asyncio)

Design effects to run sequentially using an asyncio lock. Best for single-threaded async contexts where serialization is acceptable:

```python
import asyncio
from omnibase_core.nodes import NodeEffect

class SingleThreadedEffectNode(NodeEffect):
    """NodeEffect that enforces sequential execution."""

    def __init__(self, container):
        super().__init__(container)
        self._execution_lock = asyncio.Lock()

    async def process(self, input_data):
        """Process effects sequentially."""
        async with self._execution_lock:
            return await super().process(input_data)
```

#### Option 2: Per-Thread NodeEffect Instances (Recommended for Multi-Threading)

Use thread-local storage to ensure each thread has its own NodeEffect. Best for `ThreadPoolExecutor` or multi-threaded scenarios:

```python
import threading
from omnibase_core.nodes import NodeEffect

# Thread-local storage
thread_local = threading.local()

def get_thread_local_effect(container, subcontract):
    """Get or create thread-local NodeEffect instance."""
    if not hasattr(thread_local, 'effect_node'):
        node = NodeEffect(container)
        node.effect_subcontract = subcontract
        thread_local.effect_node = node
    return thread_local.effect_node

# Usage
async def process_effect(input_data):
    node = get_thread_local_effect(my_container, my_subcontract)
    return await node.process(input_data)
```

#### Option 3: Per-Thread Circuit Breakers (Advanced)

Use thread-local circuit breakers for isolated failure tracking:

```python
import threading
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

class ThreadLocalCircuitBreakerManager:
    """Manages thread-local circuit breakers."""

    def __init__(self):
        self._thread_local = threading.local()

    def get_breaker(self, service_name: str) -> ModelCircuitBreaker:
        """Get or create thread-local circuit breaker."""
        if not hasattr(self._thread_local, 'breakers'):
            self._thread_local.breakers = {}

        if service_name not in self._thread_local.breakers:
            self._thread_local.breakers[service_name] = ModelCircuitBreaker.create_resilient()

        return self._thread_local.breakers[service_name]
```

#### Option 4: Atomic Counters with Locks (Advanced)

Add synchronization to circuit breaker operations:

```python
from threading import Lock
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker

class ThreadSafeCircuitBreaker:
    """Thread-safe wrapper for ModelCircuitBreaker.

    Production-ready circuit breaker with atomic failure tracking.
    """

    def __init__(self):
        self._breaker = ModelCircuitBreaker()
        self._lock = Lock()

    def should_allow_request(self) -> bool:
        """Thread-safe request check."""
        with self._lock:
            return self._breaker.should_allow_request()

    def record_failure(self) -> None:
        """Thread-safe failure recording."""
        with self._lock:
            self._breaker.record_failure()

    def record_success(self) -> None:
        """Thread-safe success recording."""
        with self._lock:
            self._breaker.record_success()

    def reset_state(self) -> None:
        """Thread-safe state reset."""
        with self._lock:
            self._breaker.reset_state()

    def get_current_state(self) -> str:
        """Thread-safe state retrieval with potential state transitions.

        Returns:
            Current state: "closed", "open", "half_open", or "disabled"
        """
        with self._lock:
            return self._breaker.get_current_state()

    def get_failure_rate(self) -> float:
        """Thread-safe failure rate calculation."""
        with self._lock:
            return self._breaker.get_failure_rate()

    @property
    def state(self) -> str:
        """Thread-safe raw state retrieval (no state transitions).

        Returns:
            Current state: "closed", "open", or "half_open"
        """
        with self._lock:
            return self._breaker.state
```

### Architecture Reference

For complete details on NodeEffect architecture and circuit breaker implementation:
- [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](../architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md) - Full specification
- [EFFECT_TIMEOUT_BEHAVIOR.md](../architecture/EFFECT_TIMEOUT_BEHAVIOR.md) - Timeout check points and behavior
- [NodeEffect](../../src/omnibase_core/nodes/node_effect.py) - Implementation
- [MixinEffectExecution](../../src/omnibase_core/mixins/mixin_effect_execution.py) - Execution mixin

## Transaction Thread Safety

`ModelEffectTransaction` is **NOT thread-safe**:

- Rollback operations assume single-threaded execution
- Operation list modifications are not synchronized
- State transitions are not atomic

**Critical Rule**: Multiple threads should NEVER share transaction objects.

### Transaction Isolation Pattern

```python
from uuid import uuid4
from omnibase_core.models.infrastructure.model_effect_transaction import ModelEffectTransaction

async def execute_isolated_effect(effect_node, operation_data):
    """Execute effect with transaction isolation.

    Creates one transaction per operation - never shared across threads.
    """
    # Each operation gets its own transaction
    operation_id = uuid4()

    async with effect_node.transaction_context(operation_id) as transaction:
        # Transaction is isolated to this execution context
        result = await effect_node._execute_effect(operation_data, transaction)
        return result
```

### Transaction Cleanup in Concurrent Environments

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def safe_transaction_cleanup(effect_node):
    """Ensure transactions are cleaned up even in concurrent failures."""
    active_transactions = []

    try:
        yield active_transactions
    finally:
        # Clean up all active transactions
        cleanup_tasks = [
            transaction.rollback()
            for transaction in active_transactions
            if not transaction.committed
        ]

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
```

## Validator Thread Safety

### Overview

The `ValidatorBase` class and its subclasses (`ValidatorPatterns`, `ValidatorUnionUsage`, etc.) are **NOT thread-safe** by default. Each validator instance maintains internal mutable state that is not synchronized.

### Why Validators Are NOT Thread-Safe

#### Internal Mutable State

All validators inheriting from `ValidatorBase` contain:

- `_file_line_cache`: Dictionary caching file contents for suppression checking
- `_contract`: Lazily loaded contract (single initialization is GIL-protected, but not formally thread-safe)

Additionally, `ValidatorPatterns` has:

- `_rule_config_cache`: Lazily built dictionary mapping rule IDs to configurations

These caches are cleared after each `validate()` call, but concurrent access during validation can cause:

- Cache corruption (dictionary modifications during iteration)
- Stale reads (one thread reads while another clears)
- Race conditions in cache population

#### Safe vs Unsafe Components

| Component | Thread-Safe? | Notes |
|-----------|-------------|-------|
| `ValidatorBase` instance | ❌ No | _file_line_cache is mutable |
| `ValidatorPatterns` instance | ❌ No | _rule_config_cache is mutable |
| `ValidatorUnionUsage` instance | ❌ No | Inherits _file_line_cache |
| `ModelValidatorSubcontract` | ✅ Yes | Frozen Pydantic model |
| `ModelValidationResult` | ✅ Yes | Frozen Pydantic model |
| `ModelValidationIssue` | ✅ Yes | Frozen Pydantic model |

### parallel_execution Contract Field

The `parallel_execution: true` field in validator YAML contracts indicates **PROCESS-safe** parallel execution, NOT **thread-safe** execution:

```yaml
# From any_type.validation.yaml
parallel_execution: true
```

**What this means**:
- External tools (pytest-xdist, CI runners) MAY split files across worker **processes**
- Each worker process creates its own validator instance
- Files are processed independently with no shared state between processes

**What this does NOT mean**:
- It does NOT enable internal multi-threading within the validator
- It does NOT make validator instances thread-safe
- It does NOT allow sharing a single instance across threads within a process

### Correct Usage Patterns

#### Pattern 1: Separate Instances Per Thread (Recommended)

```python
import threading
from omnibase_core.validation.validator_patterns import ValidatorPatterns

# Thread-local storage for validator instances
thread_local = threading.local()

def get_validator():
    """Get or create thread-local validator instance."""
    if not hasattr(thread_local, 'validator'):
        thread_local.validator = ValidatorPatterns()
    return thread_local.validator

# Usage in multi-threaded context
def worker_thread(files_to_validate):
    validator = get_validator()  # Each thread gets its own instance
    for file_path in files_to_validate:
        result = validator.validate_file(file_path)
        # Process result...
```

#### Pattern 2: Fresh Instance Per Validation

```python
from pathlib import Path
from omnibase_core.validation.validator_patterns import ValidatorPatterns

def validate_file_safely(file_path: Path):
    """Create fresh validator for each validation."""
    validator = ValidatorPatterns()  # New instance per call
    return validator.validate_file(file_path)
```

#### Pattern 3: Shared Contract, Separate Validators

```python
from pathlib import Path
from omnibase_core.validation.validator_patterns import ValidatorPatterns
from omnibase_core.models.contracts.subcontracts import ModelValidatorSubcontract

# Load contract once (immutable, safe to share)
shared_contract = ModelValidatorSubcontract.model_validate({
    "version": {"major": 1, "minor": 0, "patch": 0},
    "validator_id": "patterns",
    # ... rest of contract
})

def create_validator():
    """Create validator with shared contract."""
    return ValidatorPatterns(contract=shared_contract)

# Each thread/worker creates its own instance with the shared contract
```

### Incorrect Usage (Anti-Patterns)

```python
# ❌ WRONG: Sharing validator across threads
validator = ValidatorPatterns()

def worker_1():
    result = validator.validate(Path("src/module1/"))  # Race!

def worker_2():
    result = validator.validate(Path("src/module2/"))  # Race!

# Both threads share _file_line_cache - will corrupt
```

### pytest-xdist Compatibility

When using pytest-xdist (parallel test execution), validators work correctly because:

1. Each xdist worker is a **separate process** (not thread)
2. Each worker imports and creates its own validator instances
3. No state is shared between workers

The `parallel_execution: true` contract flag signals that this parallel process execution is supported.

```python
# This works correctly with pytest-xdist
class TestValidatorPatterns:
    def test_validate_file(self):
        validator = ValidatorPatterns()  # Fresh instance per test
        result = validator.validate_file(Path("src/test_file.py"))
        assert result.is_valid
```

## General Thread Safety Guidelines

### Immutable by Default

All Pydantic models are thread-safe after creation:

```python
from omnibase_core.models.model_compute_input import ModelComputeInput

# Thread-safe - models are immutable after construction
input_data = ModelComputeInput(
    computation_type="sum_numbers",
    data=[1, 2, 3, 4, 5]
)

# Safe to share across threads - no mutable state
```

### ⚠️ Shallow Immutability Warning

**CRITICAL**: `frozen=True` provides **shallow immutability only**. Nested mutable objects (dicts, lists) can still be modified in place:

```python
from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent

payload = ModelPayloadLogEvent(
    level="INFO",
    message="Test",
    context={"count": 0}
)

# ✅ This raises ValidationError (top-level field is frozen):
payload.level = "ERROR"  # ValidationError!

# ⚠️ This SUCCEEDS - nested dict is NOT frozen:
payload.context["count"] = 999  # Modifies in place!
payload.context["new_key"] = "injected"  # Also works!
```

**Thread Safety Implication**: If multiple threads share a frozen model with mutable nested data, they can race on modifying that nested data.

**Mitigation Options**:

1. **Treat nested data as read-only** (recommended for most cases)
2. **Use `model_copy(deep=True)`** to create thread-safe independent copies:
   ```python
   # Each thread gets its own deep copy
   thread_local_payload = payload.model_copy(deep=True)
   thread_local_payload.context["count"] = 999  # Safe - isolated copy
   ```
3. **Use immutable nested types** where possible (e.g., `tuple` instead of `list`)

### Mutable State Requires Synchronization

Any mutable state (caches, counters, registries) needs explicit synchronization:

```python
from threading import Lock

class ThreadSafeMetrics:
    """Example of synchronized mutable state."""

    def __init__(self):
        self._metrics = {}
        self._lock = Lock()

    def increment(self, key: str, value: float = 1.0) -> None:
        """Thread-safe metric increment."""
        with self._lock:
            self._metrics[key] = self._metrics.get(key, 0.0) + value

    def get_metrics(self) -> dict[str, float]:
        """Thread-safe metric retrieval."""
        with self._lock:
            return self._metrics.copy()
```

### Container Sharing

`ModelONEXContainer` can be safely shared across threads:

- **Read-only after initialization**: Container services are registered once
- **Protocol resolution is thread-safe**: `get_service()` performs dictionary lookup only
- **Service instances**: Individual services may not be thread-safe - check service documentation

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Create container once
container = ModelONEXContainer()
# ... register services ...

# Safe to share across threads for service resolution
def worker_thread(container):
    logger = container.get_service("ProtocolLogger")
    event_bus = container.get_service("ProtocolEventBus")
    # Use services (check individual service thread safety)
```

### Service Registry Initialization

The `initialize_service_registry()` method is thread-safe and can be called from multiple
threads simultaneously. The method uses an internal lock to ensure:

- Exactly one thread will successfully initialize the registry
- Other threads will receive `ModelOnexError` with `INVALID_STATE` error code
- The registry instance is safely published to all threads

**Example: Safe concurrent initialization**

```python
import threading
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.errors import ModelOnexError

container = ModelONEXContainer(enable_service_registry=False)

def worker():
    try:
        registry = container.initialize_service_registry()
        # Use registry...
    except ModelOnexError:
        # Another thread already initialized
        registry = container.service_registry
        # Use registry...

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

**Note**: Once initialized, `container.service_registry` property access is always thread-safe.

### Node Instance Sharing

**DO NOT** share node instances across threads without careful analysis:

```python
# UNSAFE - shared NodeCompute with cache races
compute_node = NodeCompute(container)

async def worker1():
    await compute_node.process(input1)  # Cache race!

async def worker2():
    await compute_node.process(input2)  # Cache race!

# SAFE - separate instances per thread
def get_thread_local_compute():
    if not hasattr(thread_local, 'node'):
        thread_local.node = NodeCompute(container)
    return thread_local.node

async def worker1():
    node = get_thread_local_compute()
    await node.process(input1)  # No race

async def worker2():
    node = get_thread_local_compute()
    await node.process(input2)  # No race
```

## Production Checklist

Before deploying ONEX nodes in multi-threaded production environments:

- [ ] **Cache Access Synchronized**: Wrap `ModelComputeCache` with `threading.Lock` or use thread-local caches
- [ ] **Circuit Breakers Thread-Safe**: Use thread-local breakers or synchronized wrappers
- [ ] **Transactions Per-Operation**: Create one transaction per operation, never share across threads
- [ ] **Metrics Collection Synchronized**: Ensure metric updates are atomic (use locks or atomic types)
- [ ] **Event Bus Publishing**: Verify event bus implementation is thread-safe
- [ ] **Node Instance Isolation**: Use thread-local instances or explicit synchronization
- [ ] **Container Services Validated**: Verify all container services are thread-safe
- [ ] **Load Testing Performed**: Test under realistic concurrent load to expose races
- [ ] **Error Handling Verified**: Ensure error handling doesn't introduce race conditions
- [ ] **Resource Cleanup Tested**: Verify cleanup works correctly under concurrent shutdown
- [ ] **Timeout Thread Monitoring Configured**: Monitor thread accumulation from timeout operations (see below)

## Compute Pipeline Timeout Thread Behavior

This section documents how `execute_compute_pipeline` enforces timeouts using background threads, and the deployment implications of this design.

### How Compute Timeout Enforcement Works

When `pipeline_timeout_ms` is configured in a `ModelComputeSubcontract`, the `execute_compute_pipeline` function wraps execution in a `ThreadPoolExecutor`:

```python
# From src/omnibase_core/utils/util_compute_executor.py
executor = ThreadPoolExecutor(max_workers=1)
try:
    future = executor.submit(_execute_pipeline_steps, contract, input_data, context, start_time)
    return future.result(timeout=timeout_seconds)
except FuturesTimeoutError:
    # Return timeout failure result
    return ModelComputePipelineResult(success=False, error_type="timeout_exceeded", ...)
finally:
    executor.shutdown(wait=False)  # Non-blocking shutdown
```

**Key Characteristics**:

| Aspect | Behavior |
|--------|----------|
| **Thread Type** | Daemon thread (Python ThreadPoolExecutor default) |
| **Thread Lifecycle** | Created per timeout-enabled pipeline execution |
| **Pooling** | None - new executor per call, not pooled |
| **Cleanup on Timeout** | `shutdown(wait=False)` - non-blocking |
| **Background Continuation** | Thread may continue running after timeout |

### Daemon Thread Behavior

Python's `ThreadPoolExecutor` creates daemon threads by default. This has important implications:

**Auto-Cleanup on Process Exit**:
- Daemon threads are terminated when the main process exits
- No explicit cleanup required - Python handles this automatically
- If the process exits normally, any running timeout threads terminate immediately

**Background Thread Continuation**:
- When a timeout occurs, the background thread continues executing
- `executor.shutdown(wait=False)` returns immediately without waiting
- The thread eventually completes and is garbage collected
- The result is discarded (since we've already returned a timeout error)

```text
Timeline: Timeout at 100ms, operation takes 500ms

0ms:     Submit task to executor
         Background thread starts executing pipeline
100ms:   FuturesTimeoutError raised
         Return timeout result to caller
         executor.shutdown(wait=False) called
         Background thread continues running (daemon)
500ms:   Background thread completes
         Result discarded (no one waiting)
         Thread resources freed by GC
```

### Thread Lifecycle Details

**Per-Timeout Creation** (Not Pooled):
- Each call to `execute_compute_pipeline` with `pipeline_timeout_ms` set creates a new `ThreadPoolExecutor`
- The executor is created inline and shut down after use
- This design prioritizes simplicity over thread reuse

**Why Not Pooled?**:
1. **Isolation**: Each execution is independent - no shared state concerns
2. **Simplicity**: No pool management, sizing, or lifecycle coordination
3. **Timeout Safety**: Pool threads could block if timeouts occur frequently
4. **Resource Reclaim**: Daemon threads are auto-cleaned on process exit

**Thread Count**:
- One thread per active timeout-enabled pipeline execution
- Under heavy load, this could mean many concurrent daemon threads
- Most deployments use asyncio which limits concurrent blocking operations

### Memory and Resource Implications

**During Normal Operation**:
- Minimal overhead: one thread per timeout-enabled pipeline
- Thread is released after pipeline completes or times out
- GC cleans up completed threads

**During Timeout Scenarios**:
- The background thread continues consuming CPU/memory until completion
- Result data is computed but discarded
- For CPU-bound operations, the work continues to completion
- For I/O-bound operations (rare in compute pipelines), connections may remain open

**High-Concurrency Considerations**:
- If many pipelines timeout simultaneously, daemon threads accumulate
- All will complete eventually (or terminate on process exit)
- Monitor thread count in production: `threading.active_count()`

```python
import threading

# Monitor thread count for diagnostics
active_threads = threading.active_count()
if active_threads > expected_baseline + 10:
    logger.warning(f"Elevated thread count: {active_threads} (possible timeout accumulation)")
```

### What Happens When Timeouts Trigger vs Complete Normally

**Normal Completion (Within Timeout)**:
```text
1. Pipeline submitted to executor
2. Background thread executes all steps
3. future.result(timeout=X) returns with result
4. executor.shutdown(wait=False) - thread already done
5. Result returned to caller
```

**Timeout Triggered**:
```text
1. Pipeline submitted to executor
2. Background thread starts executing
3. future.result(timeout=X) raises FuturesTimeoutError
4. executor.shutdown(wait=False) - returns immediately
5. Timeout result returned to caller
6. Background thread continues (daemon)
7. Eventually completes and is garbage collected
```

**Process Exit During Timeout**:
```text
1. Pipeline submitted to executor
2. Timeout triggers, timeout result returned
3. Background thread still running
4. Process receives SIGTERM/exits
5. Daemon threads terminated immediately by Python
6. No cleanup needed - Python handles this
```

### Best Practices for Timeout Configuration

**Setting Appropriate Timeout Values**:

```python
# Good: Timeout accounts for expected operation duration + margin
contract = ModelComputeSubcontract(
    operation_name="data_transform",
    pipeline=[...],
    pipeline_timeout_ms=5000,  # 5s for typical 2-3s operations
)

# Risky: Timeout too close to expected duration
contract = ModelComputeSubcontract(
    operation_name="data_transform",
    pipeline=[...],
    pipeline_timeout_ms=2500,  # May timeout on normal variance
)
```

**Consider the Cleanup Implications**:

```python
# For short-running operations, tight timeouts are safe
# The background thread completes quickly even if timeout fires
contract = ModelComputeSubcontract(
    operation_name="quick_validation",
    pipeline=[...],
    pipeline_timeout_ms=100,  # 100ms - thread finishes fast
)

# For long-running operations, consider if background completion is acceptable
# The thread will continue for the full duration after timeout
contract = ModelComputeSubcontract(
    operation_name="expensive_transform",
    pipeline=[...],
    pipeline_timeout_ms=1000,  # 1s timeout, but operation may take 10s
)
# Warning: If operation takes 10s, daemon thread runs for 10s after timeout
```

**Avoid Timeout in Resource-Constrained Environments**:

```python
# In memory-constrained environments, consider if timeout threads can accumulate
if environment.memory_constrained:
    # Option 1: Disable timeout (use external timeout mechanisms)
    contract = ModelComputeSubcontract(
        operation_name="resource_aware",
        pipeline=[...],
        pipeline_timeout_ms=None,  # No internal timeout
    )

    # Option 2: Use longer timeouts to reduce accumulation
    contract = ModelComputeSubcontract(
        operation_name="resource_aware",
        pipeline=[...],
        pipeline_timeout_ms=30000,  # 30s - fewer concurrent timeouts
    )
```

### Deployment Checklist for Timeout-Enabled Pipelines

- [ ] **Understand background continuation**: Accept that timeout does not cancel the underlying work
- [ ] **Set appropriate timeout values**: Account for normal variance in operation duration
- [ ] **Monitor thread count**: Track `threading.active_count()` for unexpected accumulation
- [ ] **Test under load**: Verify behavior when multiple pipelines timeout simultaneously
- [ ] **Consider memory budget**: Account for memory consumed by background threads
- [ ] **Plan for graceful shutdown**: Process exit cleanly terminates daemon threads
- [ ] **Log timeout events**: Enable observability for timeout patterns

### Comparison: Compute vs Effect Timeout Mechanisms

| Aspect | Compute Pipeline (`execute_compute_pipeline`) | Effect Execution (`execute_effect`) |
|--------|-----------------------------------------------|-------------------------------------|
| **Mechanism** | `ThreadPoolExecutor` with `future.result(timeout=X)` | `threading.Timer` with cancellation callback |
| **Thread Type** | Worker thread in executor (daemon) | Timer thread (daemon) |
| **On Timeout** | Returns immediately, thread continues | Callback fires, may cancel operation |
| **Cleanup** | `shutdown(wait=False)` | Timer auto-cleanup |
| **Use Case** | CPU-bound transformations | I/O-bound external operations |

### Architecture Reference

For related timeout documentation:
- [EFFECT_TIMEOUT_BEHAVIOR.md](../architecture/EFFECT_TIMEOUT_BEHAVIOR.md) - Effect-level timeout checkpoints
- [util_compute_executor.py](../../src/omnibase_core/utils/util_compute_executor.py) - Compute timeout implementation
- [constants_effect.py](../../src/omnibase_core/constants/constants_effect.py) - Timeout constants

---

## Production Monitoring for Timeout Threads

### Overview

The timeout mechanism in ONEX effect execution creates **daemon threads** for each timeout operation. While daemon threads are automatically terminated when the main program exits, they can accumulate during long-running production services, potentially causing resource exhaustion.

### Timeout Thread Creation Behavior

When `MixinEffectExecution.execute_effect()` is called with a timeout:

1. A new daemon thread is created via `threading.Timer`
2. The thread sleeps for the timeout duration
3. If the timeout expires before the operation completes, the thread executes the cancellation callback
4. If the operation completes first, the thread is cancelled but may not be immediately garbage collected

**Key Insight**: Each effect execution with a timeout creates at least one daemon thread. Under high load, this can result in hundreds or thousands of threads accumulating before cleanup.

### Thread Lifecycle

```text
Effect Request       Thread Created      Operation Completes      Thread Cleanup
     │                    │                      │                      │
     ▼                    ▼                      ▼                      ▼
 ┌──────┐            ┌──────┐              ┌──────────┐          ┌──────────┐
 │Start │───────────▶│Timer │─────────────▶│ Cancel   │─────────▶│   GC     │
 │Effect│            │Thread│              │  Timer   │          │(eventual)│
 └──────┘            └──────┘              └──────────┘          └──────────┘
                         │
                         │ (if timeout expires)
                         ▼
                   ┌──────────┐
                   │ Execute  │
                   │ Callback │
                   └──────────┘
```

### Metrics to Monitor

#### Primary Metrics

| Metric | Description | Collection Method |
|--------|-------------|-------------------|
| `onex_active_threads_total` | Total active threads in the process | `threading.active_count()` |
| `onex_timeout_threads_active` | Threads specifically for timeouts | Custom counter (see below) |
| `onex_thread_creation_rate` | Threads created per second | Delta of active_count over time |
| `onex_effect_timeout_executions_total` | Total effect executions with timeout | Counter in execute_effect |

#### Secondary Metrics

| Metric | Description | Collection Method |
|--------|-------------|-------------------|
| `onex_thread_names` | Thread name distribution | `threading.enumerate()` analysis |
| `onex_daemon_threads_total` | Count of daemon threads | Filter `enumerate()` by daemon flag |
| `onex_max_threads_seen` | High-water mark for thread count | Track maximum of active_count |

### Warning Thresholds

Configure alerts based on your system's capacity:

| Threshold Level | Thread Count | Action |
|-----------------|--------------|--------|
| **Normal** | < 100 | Nominal operation |
| **Warning** | 100-500 | Log warning, monitor trend |
| **Critical** | 500-1000 | Alert on-call, investigate |
| **Emergency** | > 1000 | Immediate intervention required |

**Threshold Calibration**: These are starting points. Adjust based on:
- Available system memory (each thread consumes ~8MB stack by default on Linux)
- CPU core count (context switching overhead increases with thread count)
- Effect execution patterns (burst vs steady traffic)
- Timeout duration distribution (longer timeouts = more concurrent threads)

### Thread Accumulation Detection

#### Symptom Indicators

1. **Gradual memory increase** without corresponding workload increase
2. **Increased context switching** visible in system metrics
3. **Delayed thread cleanup** after traffic subsides
4. **GC pressure** from thread object accumulation

#### Monitoring Implementation

```python
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

@dataclass
class ThreadMetrics:
    """Thread monitoring metrics snapshot."""
    timestamp: float
    active_count: int
    daemon_count: int
    timeout_thread_count: int
    thread_names: dict[str, int]

class ThreadMonitor:
    """Production thread accumulation monitor.

    Tracks thread creation patterns and detects accumulation issues.
    Thread-safe for use in multi-threaded environments.

    Example:
        monitor = ThreadMonitor(
            warning_threshold=100,
            critical_threshold=500,
            on_warning=lambda m: logger.warning(f"Thread warning: {m.active_count}"),
            on_critical=lambda m: alert_oncall(m),
        )

        # Start background monitoring
        monitor.start(interval_seconds=10)

        # ... application runs ...

        # Stop monitoring
        monitor.stop()
    """

    def __init__(
        self,
        warning_threshold: int = 100,
        critical_threshold: int = 500,
        history_size: int = 60,
        on_warning: Callable[[ThreadMetrics], None] | None = None,
        on_critical: Callable[[ThreadMetrics], None] | None = None,
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.history: deque[ThreadMetrics] = deque(maxlen=history_size)
        self.on_warning = on_warning
        self.on_critical = on_critical
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def collect_metrics(self) -> ThreadMetrics:
        """Collect current thread metrics snapshot."""
        threads = threading.enumerate()
        thread_names: dict[str, int] = {}

        daemon_count = 0
        timeout_count = 0

        for t in threads:
            if t.daemon:
                daemon_count += 1

            # Identify timeout threads by name pattern
            name = t.name or "unnamed"
            if name.startswith("Timer-") or "timeout" in name.lower():
                timeout_count += 1

            # Group by name prefix for analysis
            prefix = name.split("-")[0] if "-" in name else name
            thread_names[prefix] = thread_names.get(prefix, 0) + 1

        return ThreadMetrics(
            timestamp=time.time(),
            active_count=threading.active_count(),
            daemon_count=daemon_count,
            timeout_thread_count=timeout_count,
            thread_names=thread_names,
        )

    def check_thresholds(self, metrics: ThreadMetrics) -> None:
        """Check metrics against thresholds and trigger callbacks."""
        if metrics.active_count >= self.critical_threshold:
            if self.on_critical:
                self.on_critical(metrics)
        elif metrics.active_count >= self.warning_threshold:
            if self.on_warning:
                self.on_warning(metrics)

    def _monitor_loop(self, interval_seconds: float) -> None:
        """Background monitoring loop."""
        while not self._stop_event.wait(interval_seconds):
            metrics = self.collect_metrics()
            with self._lock:
                self.history.append(metrics)
            self.check_thresholds(metrics)

    def start(self, interval_seconds: float = 10.0) -> None:
        """Start background monitoring thread."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            return

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            name="ThreadMonitor",
            daemon=True,
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop background monitoring."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)

    def get_history(self) -> list[ThreadMetrics]:
        """Get thread metrics history (thread-safe)."""
        with self._lock:
            return list(self.history)

    def get_thread_growth_rate(self) -> float | None:
        """Calculate thread growth rate per minute.

        Returns:
            Threads per minute growth rate, or None if insufficient data.
        """
        with self._lock:
            if len(self.history) < 2:
                return None

            oldest = self.history[0]
            newest = self.history[-1]

            time_delta_minutes = (newest.timestamp - oldest.timestamp) / 60.0
            if time_delta_minutes < 0.1:  # Less than 6 seconds
                return None

            count_delta = newest.active_count - oldest.active_count
            return count_delta / time_delta_minutes
```

### Prometheus Integration

Export thread metrics for Prometheus scraping:

```python
from prometheus_client import Gauge, Counter, Histogram

# Define metrics
ACTIVE_THREADS = Gauge(
    "onex_active_threads_total",
    "Total number of active threads in the process",
)

DAEMON_THREADS = Gauge(
    "onex_daemon_threads_total",
    "Total number of daemon threads in the process",
)

TIMEOUT_THREADS = Gauge(
    "onex_timeout_threads_active",
    "Number of active timeout-related threads",
)

THREAD_CREATION_RATE = Gauge(
    "onex_thread_creation_rate_per_minute",
    "Rate of thread creation per minute",
)

MAX_THREADS_SEEN = Gauge(
    "onex_max_threads_seen",
    "High-water mark for thread count since process start",
)

EFFECT_TIMEOUT_TOTAL = Counter(
    "onex_effect_timeout_executions_total",
    "Total number of effect executions with timeout configured",
    ["effect_type", "timeout_triggered"],
)


class PrometheusThreadExporter:
    """Export thread metrics to Prometheus.

    Example:
        exporter = PrometheusThreadExporter()
        exporter.start()

        # Metrics are now available at /metrics endpoint
    """

    def __init__(self):
        self._max_threads = 0
        self._last_count = 0
        self._last_time = time.time()
        self._lock = threading.Lock()

    def update_metrics(self) -> None:
        """Update all Prometheus metrics."""
        metrics = self._collect()

        ACTIVE_THREADS.set(metrics.active_count)
        DAEMON_THREADS.set(metrics.daemon_count)
        TIMEOUT_THREADS.set(metrics.timeout_thread_count)

        with self._lock:
            if metrics.active_count > self._max_threads:
                self._max_threads = metrics.active_count
            MAX_THREADS_SEEN.set(self._max_threads)

            # Calculate rate
            now = time.time()
            time_delta = now - self._last_time
            if time_delta >= 1.0:  # At least 1 second
                rate = (metrics.active_count - self._last_count) / (time_delta / 60.0)
                THREAD_CREATION_RATE.set(rate)
                self._last_count = metrics.active_count
                self._last_time = now

    def _collect(self) -> ThreadMetrics:
        """Collect thread metrics (reuse ThreadMonitor logic)."""
        threads = threading.enumerate()
        daemon_count = sum(1 for t in threads if t.daemon)
        timeout_count = sum(
            1 for t in threads
            if t.name and (t.name.startswith("Timer-") or "timeout" in t.name.lower())
        )
        return ThreadMetrics(
            timestamp=time.time(),
            active_count=threading.active_count(),
            daemon_count=daemon_count,
            timeout_thread_count=timeout_count,
            thread_names={},
        )

    def start(self, interval_seconds: float = 10.0) -> None:
        """Start periodic metric updates."""
        def update_loop():
            while True:
                self.update_metrics()
                time.sleep(interval_seconds)

        thread = threading.Thread(
            target=update_loop,
            name="PrometheusThreadExporter",
            daemon=True,
        )
        thread.start()
```

### Logging and Observability Recommendations

#### Structured Logging for Thread Events

```python
import logging
import threading
from datetime import datetime, timezone

# Configure structured logging
logger = logging.getLogger("onex.threading")

def log_thread_metrics(metrics: ThreadMetrics, level: str = "info") -> None:
    """Log thread metrics in structured format."""
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "thread_metrics",
        "active_count": metrics.active_count,
        "daemon_count": metrics.daemon_count,
        "timeout_thread_count": metrics.timeout_thread_count,
        "top_thread_types": dict(
            sorted(
                metrics.thread_names.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        ),
    }

    if level == "warning":
        logger.warning("Thread accumulation detected", extra=log_data)
    elif level == "critical":
        logger.critical("Critical thread accumulation", extra=log_data)
    else:
        logger.info("Thread metrics snapshot", extra=log_data)
```

#### Integration with OpenTelemetry

```python
from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk.metrics import MeterProvider

# Initialize meter
meter = otel_metrics.get_meter("onex.threading")

# Create instruments
active_threads_gauge = meter.create_observable_gauge(
    name="onex.threads.active",
    description="Number of active threads",
    callbacks=[lambda: [(threading.active_count(), {})]],
)

timeout_threads_gauge = meter.create_observable_gauge(
    name="onex.threads.timeout",
    description="Number of timeout-related threads",
    callbacks=[lambda: [(_count_timeout_threads(), {})]],
)

def _count_timeout_threads() -> int:
    """Count timeout-related threads."""
    return sum(
        1 for t in threading.enumerate()
        if t.name and (t.name.startswith("Timer-") or "timeout" in t.name.lower())
    )
```

### Mitigation Strategies

When thread accumulation is detected:

1. **Reduce timeout duration**: Shorter timeouts mean threads complete faster
2. **Implement timeout pooling**: Reuse timer threads instead of creating new ones
3. **Rate limit effect executions**: Control the rate of new effect operations
4. **Increase GC frequency**: More aggressive garbage collection for thread objects
5. **Circuit breaker activation**: Trip circuit breakers to reduce load

#### Example: Timeout Thread Pool

```python
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Callable

class TimeoutPool:
    """Pooled timeout management to prevent thread accumulation.

    Instead of creating a new thread per timeout, this uses a thread pool
    to manage multiple timeouts efficiently.

    Example:
        pool = TimeoutPool(max_workers=10)

        # Schedule a timeout
        cancel_event = pool.schedule_timeout(
            timeout_seconds=30.0,
            callback=lambda: cancel_operation(),
        )

        # If operation completes early, cancel the timeout
        cancel_event.set()
    """

    def __init__(self, max_workers: int = 10):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="TimeoutPool",
        )

    def schedule_timeout(
        self,
        timeout_seconds: float,
        callback: Callable[[], None],
    ) -> Event:
        """Schedule a timeout callback.

        Args:
            timeout_seconds: Timeout duration in seconds.
            callback: Function to call when timeout expires.

        Returns:
            Event that can be set to cancel the timeout.
        """
        cancel_event = Event()

        def timeout_task():
            if not cancel_event.wait(timeout_seconds):
                # Timeout expired without cancellation
                callback()

        self._executor.submit(timeout_task)
        return cancel_event

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the timeout pool."""
        self._executor.shutdown(wait=wait)
```

### Production Checklist Addition

Add these items to your production deployment checklist:

- [ ] **Thread monitoring configured**: `ThreadMonitor` or equivalent running
- [ ] **Prometheus metrics exported**: Thread metrics available for scraping
- [ ] **Alert thresholds set**: Warning at 100, Critical at 500 (adjust as needed)
- [ ] **Runbook documented**: Steps to take when thread accumulation is detected
- [ ] **Timeout durations reviewed**: Ensure timeouts are appropriate for operations
- [ ] **Load testing completed**: Verified thread behavior under peak load

## Performance Considerations

### Lock Granularity

Balance between safety and performance:

```python
# Coarse-grained locking (safer, slower)
class CoarseLockCache:
    def __init__(self):
        self._lock = Lock()
        self._cache = {}

    def operation(self):
        with self._lock:  # Locks entire cache
            # All cache operations here
            pass

# Fine-grained locking (faster, more complex)
class FineGrainedCache:
    def __init__(self):
        self._locks = {}  # Per-key locks
        self._cache = {}

    def get_key_lock(self, key):
        # Lock only specific key
        pass
```

### Lock-Free Alternatives

For high-performance scenarios, consider lock-free data structures:

```python
from queue import Queue

# Lock-free queue for work distribution
work_queue = Queue()

# Producer
work_queue.put(computation_task)

# Consumer
task = work_queue.get()
```

### Async vs Thread Safety

AsyncIO single-threaded execution model avoids many race conditions:

```python
import asyncio

# AsyncIO tasks share event loop - no thread races
async def safe_async_processing():
    # No locks needed for single-threaded async
    result1 = await async_operation1()
    result2 = await async_operation2()
    return result1 + result2
```

**However**: If using `run_in_executor()` or `ThreadPoolExecutor`, thread safety concerns return:

```python
# This introduces thread safety concerns!
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(thread_pool, blocking_operation)
```

## Built-in Debug Mode Thread Safety Validation

ONEX provides built-in runtime thread safety validation for effect execution that can be enabled during development. This helps catch threading violations early with zero overhead in production.

### Enabling Debug Mode

Set the `ONEX_DEBUG_THREAD_SAFETY` environment variable to enable runtime checks:

```bash
# Enable thread safety validation
export ONEX_DEBUG_THREAD_SAFETY=1

# Run your application/tests
uv run pytest tests/

# Disable (default - zero overhead)
unset ONEX_DEBUG_THREAD_SAFETY
```

### How It Works

When `ONEX_DEBUG_THREAD_SAFETY=1` is set:

1. **Instance Creation**: When a `NodeEffect` or `MixinEffectExecution` instance is created, it records the creating thread's ID
2. **Method Entry**: Key public methods (`execute_effect()`, `get_circuit_breaker()`) validate they're called from the same thread
3. **Violation Detection**: If called from a different thread, a `ModelOnexError` is raised with `THREAD_SAFETY_VIOLATION` error code

When disabled (default):
- The `_owner_thread_id` attribute is `None`
- The check is a simple `if self._owner_thread_id is not None:` which short-circuits immediately
- **Zero performance overhead** in production

### Example Error

When a thread safety violation is detected:

```python
import threading
from omnibase_core.nodes import NodeEffect

# Enable debug mode
import os
os.environ["ONEX_DEBUG_THREAD_SAFETY"] = "1"

# Create node on main thread
node = NodeEffect(container)
node.effect_subcontract = subcontract

# Access from different thread - will raise!
def worker():
    import asyncio
    asyncio.run(node.process(input_data))  # Raises ModelOnexError!

thread = threading.Thread(target=worker)
thread.start()
thread.join()
```

Error output:

```text
ModelOnexError: Thread safety violation: node instance accessed from different thread
  error_code: ONEX_CORE_261_THREAD_SAFETY_VIOLATION
  context:
    owner_thread: 140234567890432
    current_thread: 140234567890999
    node_id: 550e8400-e29b-41d4-a716-446655440000
```

### Protected Methods

The following methods are protected by thread safety checks when debug mode is enabled:

| Component | Method | Protection |
|-----------|--------|------------|
| `MixinEffectExecution` | `execute_effect()` | Validates thread at entry |
| `NodeEffect` | `get_circuit_breaker()` | Validates thread at entry |

### When to Use

**Enable during**:
- Development and debugging
- CI/CD test runs (add to test environment)
- Staging environment validation
- Performance testing (to catch races before production)

**Disable in**:
- Production (default - zero overhead)
- Benchmarking (to measure true performance)

### Configuration

The debug flag is configured in `omnibase_core.constants.constants_effect`:

```python
from omnibase_core.constants.constants_effect import DEBUG_THREAD_SAFETY

# Check if debug mode is enabled
if DEBUG_THREAD_SAFETY:
    print("Thread safety validation is active")
```

### Integration with CI

Add to your CI configuration to catch threading issues early:

```yaml
# GitHub Actions example
- name: Run tests with thread safety validation
  env:
    ONEX_DEBUG_THREAD_SAFETY: "1"
  run: uv run pytest tests/
```

## Runtime Thread Safety Checks (Custom)

In addition to the built-in debug mode, you can add custom runtime checks to detect threading violations:

### Thread Affinity Enforcement

**Performance Warning**: The `__getattribute__` override in `ThreadAffinityMixin` adds overhead to every attribute access on the class. This is intended for **development and debugging only**. Do not use in production without careful profiling, as it can significantly impact performance for attribute-heavy operations.

**Recursion Safety**: The implementation below uses `object.__getattribute__` directly within the override to avoid infinite recursion when accessing internal attributes like `_owner_thread`.

```python
import threading
from typing import Any

class ThreadAffinityMixin:
    """Mixin to enforce single-thread usage of a class.

    Use this mixin to detect accidental multi-threaded access to
    components that are not thread-safe (e.g., NodeCompute, NodeEffect).

    WARNING: This mixin adds overhead to EVERY attribute access.
    Use only for debugging and development, not in production.
    """

    _owner_thread: int | None = None

    def _check_thread_affinity(self) -> None:
        """Verify we're on the same thread that created this instance.

        Raises:
            RuntimeError: If called from a different thread than the creator.
        """
        current_thread = threading.current_thread().ident
        # Use object.__getattribute__ to avoid recursion
        owner = object.__getattribute__(self, '_owner_thread')
        if owner is None:
            object.__setattr__(self, '_owner_thread', current_thread)
        elif owner != current_thread:
            raise RuntimeError(
                f"Thread safety violation: {self.__class__.__name__} "
                f"created on thread {owner} but accessed "
                f"from thread {current_thread}. Use thread-local instances."
            )

    def __getattribute__(self, name: str) -> Any:
        """Check thread affinity on all attribute access.

        WARNING: Potential recursion risk if not implemented carefully.
        This implementation uses object.__getattribute__ directly to
        access internal state without triggering this override.
        """
        # Skip check for internal attributes to avoid recursion and reduce overhead
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        # Use object.__getattribute__ to call the check method safely
        check_method = object.__getattribute__(self, '_check_thread_affinity')
        check_method()
        return object.__getattribute__(self, name)
```

### Debug Mode Thread Safety Wrapper

```python
import os
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar('T')

def debug_thread_check(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to add thread safety checks in debug mode.

    Only active when ONEX_DEBUG_THREADING=1 environment variable is set.
    Use this to instrument methods that should not be called concurrently.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> T:
        if os.environ.get('ONEX_DEBUG_THREADING') == '1':
            import threading
            thread_id = threading.current_thread().ident
            owner_attr = f'_thread_owner_{func.__name__}'

            current_owner = getattr(self, owner_attr, None)
            if current_owner is not None and current_owner != thread_id:
                raise RuntimeError(
                    f"Concurrent access detected in {func.__name__}: "
                    f"thread {thread_id} vs owner {current_owner}"
                )

            setattr(self, owner_attr, thread_id)
            try:
                return func(self, *args, **kwargs)
            finally:
                setattr(self, owner_attr, None)
        else:
            return func(self, *args, **kwargs)

    return wrapper
```

### Usage in Node Classes

```python
from omnibase_core.nodes import NodeEffect

class DebugNodeEffect(NodeEffect):
    """NodeEffect with runtime thread safety checks (development only)."""

    @debug_thread_check
    async def process(self, input_data):
        """Process with thread safety validation."""
        return await super().process(input_data)

    @debug_thread_check
    def get_circuit_breaker(self, operation_id):
        """Get circuit breaker with thread safety validation."""
        return super().get_circuit_breaker(operation_id)
```

## Testing Thread Safety

See `tests/unit/test_thread_safety.py` for examples of:

- Deliberate race condition tests
- Cache corruption scenarios
- Circuit breaker race tests
- Expected failures without synchronization
- Correct locking pattern validation

### Example Test Pattern

```python
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from omnibase_core.nodes import NodeCompute


class TestNodeComputeThreadSafety:
    """Tests demonstrating thread safety issues and mitigations."""

    def test_shared_node_race_condition(self, container):
        """Demonstrates race condition with shared NodeCompute."""
        node = NodeCompute(container)
        errors = []

        def worker():
            try:
                # Simulate concurrent processing
                asyncio.run(node.process(input_data))
            except Exception as e:
                errors.append(e)

        # Launch concurrent workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(100)]
            for f in futures:
                f.result()

        # May see race condition errors or cache corruption
        # This test demonstrates the problem - not a passing test

    def test_thread_local_node_safe(self, container):
        """Demonstrates safe pattern with thread-local nodes."""
        thread_local = threading.local()

        def get_node():
            if not hasattr(thread_local, 'node'):
                thread_local.node = NodeCompute(container)
            return thread_local.node

        errors = []

        def worker():
            try:
                node = get_node()  # Each thread gets its own
                asyncio.run(node.process(input_data))
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(100)]
            for f in futures:
                f.result()

        assert len(errors) == 0, f"Unexpected errors: {errors}"
```

## Additional Resources

- [Python threading documentation](https://docs.python.org/3/library/threading.html)
- [asyncio thread safety](https://docs.python.org/3/library/asyncio-dev.html#concurrency-and-multithreading)
- [Pydantic model immutability](https://docs.pydantic.dev/latest/concepts/models/#frozen-models)

## Thread Safety Quick Reference

### Models (Input/Output)

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| Pydantic Models | Yes (immutable) | None needed |
| ModelComputeInput/Output | Yes (frozen=True) | None needed |
| ModelReducerInput/Output | Yes (frozen=True) | None needed |
| ModelEffectInput/Output | Yes (frozen=True) | None needed |
| ModelOrchestratorInput | Partial* | See note below |
| ModelOrchestratorOutput | Yes (frozen=True) | None needed |
| EffectIOConfig models | Yes (frozen=True) | None needed |

**\*ModelOrchestratorInput Thread Safety Note**:

`ModelOrchestratorInput` is top-level frozen (`frozen=True`), but contains a mutable `metadata` field of type `ModelOrchestratorInputMetadata` (`frozen=False`). This means:

- Top-level fields (workflow_id, steps, execution_mode, etc.) cannot be reassigned
- The `metadata` object CAN be mutated in place (e.g., `input.metadata.source = "new"`)

**Mitigation**:
1. **Treat as read-only** after creation (recommended)
2. **Use model_copy()** to create modified copies: `input.model_copy(update={"metadata": new_metadata})`
3. **Use explicit locks** if mutation across threads is required

### Workflow Contract Models (v0.4.0+)

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| ModelWorkflowDefinition | Yes (frozen=True) | None needed |
| ModelWorkflowDefinitionMetadata | Yes (frozen=True) | None needed |
| ModelWorkflowStep | Yes (frozen=True) | None needed |
| ModelCoordinationRules | Yes (frozen=True) | None needed |
| ModelExecutionGraph | Yes (frozen=True) | None needed |
| ModelWorkflowNode | Yes (frozen=True) | None needed |

**Note**: As of v0.4.0, all workflow contract models are frozen (`frozen=True`) and forbid extra fields (`extra="forbid"`). This makes them inherently thread-safe for reads and safe to share across threads without synchronization. Use `model_copy(update={...})` to create modified copies. See the [CHANGELOG.md](../../CHANGELOG.md) migration guide for details.

### Infrastructure

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| ModelONEXContainer | Yes (read-only) | None needed after init |
| ModelComputeCache | No | Use locks or thread-local instances |
| ModelCircuitBreaker | No | Use locks or thread-local instances |
| ModelEffectTransaction | No | Never share across threads |

### Node Instances

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| NodeCompute | No | Thread-local instances or locked cache |
| NodeEffect | No | Thread-local instances (recommended) |
| NodeReducer | No | Thread-local instances (FSM state is mutable) |
| NodeOrchestrator | No | Thread-local instances (workflow state is mutable) |

### Mixins

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| MixinEffectExecution | No | _circuit_breakers dict is not synchronized |
| MixinNodeLifecycle | Yes | Stateless methods |
| MixinDiscoveryResponder | Yes | Stateless methods |

### Validators

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| ValidatorBase | No | _file_line_cache is mutable |
| ValidatorPatterns | No | _rule_config_cache is mutable |
| ValidatorUnionUsage | No | Inherits _file_line_cache |
| ModelValidatorSubcontract | Yes (frozen=True) | None needed - can share |
| ModelValidationResult | Yes (frozen=True) | None needed |
| ModelValidationIssue | Yes (frozen=True) | None needed |

**Note**: The `parallel_execution: true` contract field indicates **process-safe** parallel execution (e.g., pytest-xdist), NOT thread-safe execution within a process. See [Validator Thread Safety](#validator-thread-safety) for details.

## Design Rationale

ONEX nodes are intentionally NOT thread-safe by default for several reasons:

1. **Performance**: Synchronization adds overhead to every operation
2. **Simplicity**: Thread-local patterns are simpler to reason about
3. **Explicit Control**: Developers must consciously choose their concurrency model
4. **AsyncIO Compatibility**: Most ONEX workloads use asyncio which is single-threaded

**Default Assumption**: Unless explicitly documented as thread-safe, assume components require synchronization for concurrent use.

## Key References

- NodeEffect: [node_effect.py](../../src/omnibase_core/nodes/node_effect.py)
- NodeCompute: [node_compute.py](../../src/omnibase_core/nodes/node_compute.py)
- NodeReducer: [node_reducer.py](../../src/omnibase_core/nodes/node_reducer.py)
- NodeOrchestrator: [node_orchestrator.py](../../src/omnibase_core/nodes/node_orchestrator.py)
- MixinEffectExecution: [mixin_effect_execution.py](../../src/omnibase_core/mixins/mixin_effect_execution.py)
- NodeEffect Architecture: [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](../architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md)
- ValidatorBase: [validator_base.py](../../src/omnibase_core/validation/validator_base.py)
- ValidatorPatterns: [validator_patterns.py](../../src/omnibase_core/validation/validator_patterns.py)
- ValidatorUnionUsage: [validator_types.py](../../src/omnibase_core/validation/validator_types.py)
