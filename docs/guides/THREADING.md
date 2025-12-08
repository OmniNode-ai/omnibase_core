# Thread Safety in Omnibase Core

## Overview

This document explains the concurrency model and thread safety guarantees for ONEX nodes. Understanding these guarantees is critical for production multi-threaded environments.

**Key Takeaway**: Most ONEX node components are **NOT thread-safe by default**. Careful synchronization is required for concurrent usage.

## NodeCompute Thread Safety

### Parallel Processing

`NodeCompute` uses `ThreadPoolExecutor` for parallel batch processing:

- **Thread-Safe**: Input/output models (immutable after creation via Pydantic)
- **NOT Thread-Safe**: Internal cache state (requires synchronization)
- **Recommendation**: Use separate NodeCompute instances per thread OR implement cache locking

### Computation Cache

**Current implementation: NOT thread-safe by default**

The `ModelComputeCache` LRU cache operations are not atomic:
- Concurrent `get()` calls can race with `put()` operations
- LRU eviction logic can corrupt cache state under concurrent access
- Access count updates are not atomic

**Mitigation: Add threading.Lock for production use**

Example of thread-safe cache wrapper:

```
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

**Option 1: Per-Thread NodeCompute Instances (Recommended)**

```
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

**Option 2: Shared NodeCompute with Locked Cache**

```
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

**Circuit Breaker State**:
- Circuit breakers are stored in `_circuit_breakers` instance dictionary
- Keyed by `operation_id` (UUID) for per-operation failure tracking
- State includes failure counters, timestamps, and state transitions
- No synchronization primitives (by design for performance)

**State Race Conditions**:
- `failure_count` increments are not atomic
- `last_failure_time` updates can race
- Multiple threads may incorrectly trip/reset breaker state
- Dictionary updates (`_circuit_breakers[op_id] = breaker`) are not atomic

**Impact Under Concurrent Load**:
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

**❌ WRONG - Sharing NodeEffect Across Threads**

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

**✅ CORRECT - Separate Instance Per Thread**

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

**Option 1: Single-Threaded Effects (Recommended)**

Design effects to run sequentially using semaphores or queues:

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

**Option 2: Per-Thread NodeEffect Instances (Recommended)**

Use thread-local storage to ensure each thread has its own NodeEffect:

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

**Option 3: Per-Thread Circuit Breakers (Advanced)**

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
            self._thread_local.breakers[service_name] = ModelCircuitBreaker()

        return self._thread_local.breakers[service_name]
```

**Option 4: Atomic Counters with Locks (Advanced)**

Add synchronization to circuit breaker operations:

```python
from threading import Lock
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState

class ThreadSafeCircuitBreaker:
    """Thread-safe wrapper for ModelCircuitBreaker.

    Production-ready circuit breaker with atomic failure tracking.
    """

    def __init__(self):
        self._breaker = ModelCircuitBreaker()
        self._lock = Lock()

    def can_execute(self) -> bool:
        """Thread-safe execution check."""
        with self._lock:
            return self._breaker.can_execute()

    def record_failure(self) -> None:
        """Thread-safe failure recording."""
        with self._lock:
            self._breaker.record_failure()

    def record_success(self) -> None:
        """Thread-safe success recording."""
        with self._lock:
            self._breaker.record_success()

    @property
    def state(self) -> EnumCircuitBreakerState:
        """Thread-safe state retrieval."""
        with self._lock:
            return self._breaker.state
```

### Architecture Reference

For complete details on NodeEffect architecture and circuit breaker implementation:
- [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](../architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md) - Full specification
- [NodeEffect](../../src/omnibase_core/nodes/node_effect.py) - Implementation
- [MixinEffectExecution](../../src/omnibase_core/mixins/mixin_effect_execution.py) - Execution mixin

## Transaction Thread Safety

`ModelEffectTransaction` is **NOT thread-safe**:

- Rollback operations assume single-threaded execution
- Operation list modifications are not synchronized
- State transitions are not atomic

**Critical Rule**: Multiple threads should NEVER share transaction objects.

### Transaction Isolation Pattern

```
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

```
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

## General Thread Safety Guidelines

### Immutable by Default

All Pydantic models are thread-safe after creation:

```
from omnibase_core.models.model_compute_input import ModelComputeInput

# Thread-safe - models are immutable after construction
input_data = ModelComputeInput(
    computation_type="sum_numbers",
    data=[1, 2, 3, 4, 5]
)

# Safe to share across threads - no mutable state
```

### Mutable State Requires Synchronization

Any mutable state (caches, counters, registries) needs explicit synchronization:

```
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

```
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

### Node Instance Sharing

**DO NOT share node instances across threads without careful analysis:**

```
# ❌ UNSAFE - shared NodeCompute with cache races
compute_node = NodeCompute(container)

async def worker1():
    await compute_node.process(input1)  # Cache race!

async def worker2():
    await compute_node.process(input2)  # Cache race!

# ✅ SAFE - separate instances per thread
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

## Performance Considerations

### Lock Granularity

Balance between safety and performance:

```
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

```
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

```
import asyncio

# AsyncIO tasks share event loop - no thread races
async def safe_async_processing():
    # No locks needed for single-threaded async
    result1 = await async_operation1()
    result2 = await async_operation2()
    return result1 + result2
```

**However**: If using `run_in_executor()` or `ThreadPoolExecutor`, thread safety concerns return:

```
# This introduces thread safety concerns!
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(thread_pool, blocking_operation)
```

## Testing Thread Safety

See `tests/unit/test_thread_safety.py` for examples of:

- Deliberate race condition tests
- Cache corruption scenarios
- Circuit breaker race tests
- Expected failures without synchronization
- Correct locking pattern validation

## Additional Resources

- [Python threading documentation](https://docs.python.org/3/library/threading.html)
- [asyncio thread safety](https://docs.python.org/3/library/asyncio-dev.html#concurrency-and-multithreading)
- [Pydantic model immutability](https://docs.pydantic.dev/latest/concepts/models/#frozen-models)

## Summary

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| Pydantic Models | ✅ Yes (immutable) | None needed |
| ModelONEXContainer | ✅ Yes (read-only) | None needed after init |
| ModelComputeOutput | ✅ Yes (frozen=True) | None needed |
| ModelReducerOutput | ✅ Yes (frozen=True) | None needed |
| ModelEffectInput/Output | ✅ Yes (frozen=True) | None needed |
| EffectIOConfig models | ✅ Yes (frozen=True) | None needed |
| ModelComputeCache | ❌ No | Use locks or thread-local instances |
| ModelCircuitBreaker | ❌ No | Use locks or thread-local instances |
| ModelEffectTransaction | ❌ No | Never share across threads |
| NodeCompute instances | ❌ No | Thread-local instances or locked cache |
| NodeEffect instances | ❌ No | Thread-local instances (recommended) |
| MixinEffectExecution._circuit_breakers | ❌ No | Process-local, single-thread only |

**Default Assumption**: Unless explicitly documented as thread-safe, assume components require synchronization for concurrent use.

**Key References**:
- NodeEffect: [node_effect.py](../../src/omnibase_core/nodes/node_effect.py)
- MixinEffectExecution: [mixin_effect_execution.py](../../src/omnibase_core/mixins/mixin_effect_execution.py)
- NodeEffect Architecture: [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](../architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md)
