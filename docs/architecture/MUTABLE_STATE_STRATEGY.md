> **Navigation**: [Home](../index.md) > [Architecture](./overview.md) > Mutable State Strategy

# Mutable State Strategy for ONEX Nodes

> **Status**: MVP Design Decision
> **Version**: 0.4.0
> **Last Updated**: 2025-12-14
> **Related Issues**: OMN-704, OMN-700

## Table of Contents

1. [Overview](#overview)
2. [MVP Design Decision](#mvp-design-decision)
3. [Current Mutable State by Node Type](#current-mutable-state-by-node-type)
4. [Thread Safety Guidelines](#thread-safety-guidelines)
5. [Production Improvement Roadmap](#production-improvement-roadmap)
6. [Migration Path](#migration-path)
7. [References](#references)

---

## Overview

This document explains the intentional use of mutable state in ONEX node implementations during the MVP phase, the trade-offs involved, and the roadmap for production improvements.

**Key Principle**: ONEX nodes use mutable instance state as an explicit MVP design decision. This approach prioritizes rapid development and iterative learning over distributed state management complexity.

**Thread Safety Impact**: Most ONEX node components are **NOT thread-safe by default**. See [Thread Safety Guidelines](#thread-safety-guidelines) and the comprehensive [THREADING.md](../guides/THREADING.md) guide.

---

## MVP Design Decision

### Why Mutable State?

During the MVP phase, ONEX nodes use mutable instance state for:

1. **Rapid Development**: Simpler implementation without distributed state management overhead
2. **Reduced Complexity**: No external state store dependencies (Redis, PostgreSQL for state)
3. **Iterative Learning**: Flexibility to evolve the state model based on real-world usage patterns
4. **Single-Process Optimization**: Efficient in-memory operations for single-instance deployments
5. **Debugging Simplicity**: State is inspectable within the process without external tooling

### Trade-offs Accepted

| Benefit | Trade-off |
|---------|-----------|
| Simpler implementation | Not thread-safe by default |
| No external dependencies for state | State lost on instance restart |
| Faster iteration on state model | Manual synchronization required for concurrency |
| Lower latency (in-memory) | No horizontal scaling with shared state |
| Easy local debugging | No distributed coordination support |

### Design Philosophy

The mutable state approach aligns with ONEX's progressive enhancement philosophy:

1. **Start Simple**: Begin with in-memory mutable state
2. **Validate Patterns**: Learn from real usage which state patterns emerge
3. **Evolve Intentionally**: Add complexity (external stores, distributed coordination) only when proven necessary
4. **Maintain Compatibility**: Future enhancements will be opt-in, preserving existing APIs

---

## Current Mutable State by Node Type

### NodeCompute

**Import**: `from omnibase_core.nodes import NodeCompute`

| Component | Purpose | Thread Safety Impact |
|-----------|---------|---------------------|
| `_cache` | Computation result caching | Cache operations not atomic; LRU eviction races |
| `computation_registry` | Algorithm function registry | Dict mutations not synchronized |
| `computation_metrics` | Performance tracking | Counter updates not atomic |

**Risk Level**: High

**Mitigation Strategies**:
- **Protocol Injection (OMN-700)**: Thread-safe cache implementations can be injected via container
- **Thread-Local Instances**: Use `threading.local()` for per-thread NodeCompute instances
- **Locked Cache Wrapper**: Wrap `ModelComputeCache` with `threading.Lock`

**Example - Thread-Safe Cache Injection**:

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Container configured with thread-safe cache implementation
container = ModelONEXContainer()
container.register_service("ProtocolComputeCache", ThreadSafeComputeCache())

# NodeCompute will use the thread-safe cache
node = NodeCompute(container)
```

### NodeReducer

**Import**: `from omnibase_core.nodes import NodeReducer`

| Component | Purpose | Thread Safety Impact |
|-----------|---------|---------------------|
| `fsm_contract` | Loaded FSM definition | Reference mutation during loading |
| FSM current state | State machine position | State transition races |
| FSM state history | Transition audit trail | List append races |
| FSM context | Accumulated context data | Dict mutation races |

**Risk Level**: High

**Mitigation Strategy**: Thread-local instances recommended. Each thread should have its own NodeReducer instance with isolated FSM state.

**Why FSM State is Mutable**:
- FSM transitions modify `current_state` in-place for performance
- State history accumulates across transitions
- Context data evolves through the workflow lifecycle

**Example - Thread-Local Reducer**:

```python
import threading
from omnibase_core.nodes import NodeReducer

thread_local = threading.local()

def get_reducer(container, fsm_contract):
    """Get or create thread-local NodeReducer instance."""
    if not hasattr(thread_local, 'reducer'):
        node = NodeReducer(container)
        node.fsm_contract = fsm_contract
        thread_local.reducer = node
    return thread_local.reducer
```

### NodeOrchestrator

**Import**: `from omnibase_core.nodes import NodeOrchestrator`

| Component | Purpose | Thread Safety Impact |
|-----------|---------|---------------------|
| `workflow_definition` | Loaded workflow definition | Reference mutation during loading |
| Active executions | Running workflow tracking | Execution state races |
| Step completion status | Progress tracking | Status update races |
| Workflow context | Accumulated context data | Dict mutation races |

**Risk Level**: High

**Mitigation Strategy**: Thread-local instances recommended. Each thread should have its own NodeOrchestrator instance with isolated workflow state.

**Why Workflow State is Mutable**:
- Workflows track execution progress across multiple steps
- Step completion modifies execution state in-place
- Context accumulates outputs from completed steps

**Example - Thread-Local Orchestrator**:

```python
import threading
from omnibase_core.nodes import NodeOrchestrator

thread_local = threading.local()

def get_orchestrator(container, workflow_definition):
    """Get or create thread-local NodeOrchestrator instance."""
    if not hasattr(thread_local, 'orchestrator'):
        node = NodeOrchestrator(container)
        node.workflow_definition = workflow_definition
        thread_local.orchestrator = node
    return thread_local.orchestrator
```

### NodeEffect

**Import**: `from omnibase_core.nodes import NodeEffect`

| Component | Purpose | Thread Safety Impact |
|-----------|---------|---------------------|
| `_circuit_breakers` | Per-operation circuit breakers | Dict and counter races |
| `effect_subcontract` | Loaded effect definition | Reference mutation during loading |

**Risk Level**: Critical

**Mitigation Strategy**: Thread-local instances **strongly recommended**. Circuit breaker state corruption can lead to incorrect failure handling.

**Why Circuit Breaker State is Mutable**:
- Failure counts increment on each failure
- State transitions (closed -> open -> half-open) modify state in-place
- Last failure timestamps update on each failure

**Critical Race Condition**:

```text
# Thread 1 and Thread 2 both check for operation_id simultaneously:

# Thread 1                          # Thread 2
if op_id not in self._circuit_breakers:  # True
                                    if op_id not in self._circuit_breakers:  # True
    breaker = ModelCircuitBreaker.create_resilient()
    self._circuit_breakers[op_id] = breaker  # Creates breaker
                                    breaker = ModelCircuitBreaker.create_resilient()
                                    self._circuit_breakers[op_id] = breaker  # Overwrites!

# Result: Thread 1's circuit breaker state is lost
```

**Example - Thread-Local Effect Node**:

```python
import threading
from omnibase_core.nodes import NodeEffect

thread_local = threading.local()

def get_effect_node(container, subcontract):
    """Get or create thread-local NodeEffect instance."""
    if not hasattr(thread_local, 'effect_node'):
        node = NodeEffect(container)
        node.effect_subcontract = subcontract
        thread_local.effect_node = node
    return thread_local.effect_node
```

---

## Thread Safety Guidelines

For detailed thread safety patterns, mitigation strategies, and production checklists, see the comprehensive [THREADING.md](../guides/THREADING.md) guide.

### Quick Reference

**Thread-Safe Components**:
| Component | Notes |
|-----------|-------|
| `ModelONEXContainer` | Read-only after initialization |
| Pydantic Models | Immutable after creation (frozen=True) |
| Input/Output Models | Frozen via Pydantic |
| Workflow Contract Models | Frozen via Pydantic (v0.4.0+) |
| Stateless Mixin Methods | Safe if inputs are thread-safe |

**NOT Thread-Safe Components**:
| Component | Risk Level | Recommended Mitigation |
|-----------|------------|------------------------|
| `NodeCompute` | High | Thread-local instances or locked cache |
| `NodeEffect` | Critical | Thread-local instances (strongly recommended) |
| `NodeReducer` | High | Thread-local instances |
| `NodeOrchestrator` | High | Thread-local instances |
| `ModelComputeCache` | High | Wrap with `threading.Lock` |
| `ModelCircuitBreaker` | High | Use locks or thread-local instances |
| `ModelEffectTransaction` | Critical | Never share across threads |

### Quick Decision Guide

1. **Creating a multi-threaded service?** Use thread-local node instances
2. **Need shared state?** Add explicit synchronization with `threading.Lock`
3. **Using asyncio only?** Single-threaded event loop avoids most races (but watch for `run_in_executor`)
4. **Production deployment?** Complete the [Production Checklist](../guides/THREADING.md#production-checklist)

### Debug Mode

Enable runtime thread safety validation during development:

```bash
export ONEX_DEBUG_THREAD_SAFETY=1
poetry run pytest tests/
```

When enabled, accessing a node instance from a different thread than its creator raises `ModelOnexError` with `THREAD_SAFETY_VIOLATION` error code.

---

## Production Improvement Roadmap

### Phase 1: Protocol Injection (Completed - OMN-700)

**Status**: Implemented in v0.4.0

**Changes**:
- NodeCompute infrastructure services (cache, timing, parallel executor) now injectable
- Thread-safe implementations can be injected via container
- Pure mode available (no mutable state when services not injected)

**Benefits**:
- Swap in thread-safe implementations without code changes
- Test with mock implementations
- Gradual migration to production-ready components

**Example**:

```python
# Inject thread-safe cache via container
container.register_service("ProtocolComputeCache", ThreadSafeComputeCache())
container.register_service("ProtocolParallelExecutor", ThreadSafeExecutor())

# NodeCompute uses injected services
node = NodeCompute(container)
```

### Phase 2: External State Stores (Planned)

**Target**: v0.5.0+

**Scope**:
- FSM state persistence to external store (Redis, PostgreSQL)
- Workflow execution state externalization
- Circuit breaker state sharing across instances
- Configurable state backends via protocol injection

**Benefits**:
- State survives instance restarts
- Horizontal scaling with shared state
- Distributed coordination support
- State inspection via external tooling

**Proposed Interface**:

```python
from abc import abstractmethod
from typing import Protocol

class ProtocolStateStore(Protocol):
    """Protocol for external state storage."""

    @abstractmethod
    async def get(self, key: str) -> dict | None:
        """Retrieve state by key."""
        ...

    @abstractmethod
    async def set(self, key: str, state: dict, ttl_seconds: int | None = None) -> None:
        """Store state with optional TTL."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete state by key."""
        ...
```

### Phase 3: Lease-Based Coordination (Planned)

**Target**: v0.6.0+

**Scope**:
- Lease-based single-writer semantics for orchestrators
- Distributed locks for reducer state transitions
- Workflow step claiming with automatic release
- Conflict resolution for concurrent workflows

**Benefits**:
- True distributed orchestration
- Automatic failover on instance failure
- At-most-once execution guarantees
- No split-brain scenarios

**Conceptual Model**:

```python
class ProtocolLeaseManager(Protocol):
    """Protocol for distributed lease management."""

    @abstractmethod
    async def acquire(self, resource_id: str, holder_id: str, ttl_seconds: int) -> bool:
        """Attempt to acquire lease. Returns True if successful."""
        ...

    @abstractmethod
    async def renew(self, resource_id: str, holder_id: str, ttl_seconds: int) -> bool:
        """Renew existing lease. Returns True if successful."""
        ...

    @abstractmethod
    async def release(self, resource_id: str, holder_id: str) -> bool:
        """Release lease. Returns True if released."""
        ...
```

### Phase 4: Event-Sourced State (Future)

**Target**: v1.0.0+

**Scope**:
- Full event sourcing for state changes
- State reconstruction from event log
- Time-travel debugging support
- Event replay for testing and recovery

**Benefits**:
- Complete audit trail of all state changes
- State reconstruction at any point in time
- Debugging complex distributed scenarios
- Replay events for testing and recovery

**Conceptual Model**:

```python
class ModelStateEvent(BaseModel):
    """Event representing a state change."""
    event_id: UUID
    aggregate_id: str
    event_type: str
    payload: dict
    timestamp: datetime
    sequence_number: int

class ProtocolEventStore(Protocol):
    """Protocol for event sourcing storage."""

    @abstractmethod
    async def append(self, aggregate_id: str, events: list[ModelStateEvent]) -> None:
        """Append events to the event stream."""
        ...

    @abstractmethod
    async def read(self, aggregate_id: str, from_sequence: int = 0) -> list[ModelStateEvent]:
        """Read events from sequence number."""
        ...
```

---

## Migration Path

When production improvements are implemented, the migration path follows these principles:

### 1. No Breaking Changes

Current APIs remain stable. Existing code continues to work without modification.

```python
# v0.4.0 code continues to work in v0.5.0+
from omnibase_core.nodes import NodeCompute

node = NodeCompute(container)
result = await node.process(input_data)
```

### 2. Opt-In Features

New capabilities are available via configuration, not required.

```python
# v0.5.0+ - opt-in to external state store
from omnibase_core.state import RedisStateStore

container.register_service("ProtocolStateStore", RedisStateStore(redis_url))

# NodeReducer automatically uses external state when available
reducer = NodeReducer(container)
```

### 3. Gradual Migration

Existing code works, new code can use enhanced features. Mix and match as needed.

```python
# Some nodes use external state, others use in-memory
compute_node = NodeCompute(container)  # In-memory cache (default)
reducer_node = NodeReducer(container)  # External state (if configured)
```

### 4. Documentation Updates

Migration guides will be provided for each phase:

| Phase | Migration Guide (Planned) |
|-------|---------------------------|
| Phase 2 | `docs/guides/MIGRATING_TO_EXTERNAL_STATE.md` |
| Phase 3 | `docs/guides/MIGRATING_TO_LEASE_COORDINATION.md` |
| Phase 4 | `docs/guides/MIGRATING_TO_EVENT_SOURCING.md` |

---

## References

### Thread Safety

- [THREADING.md](../guides/THREADING.md) - Comprehensive thread safety guide with patterns and production checklist

### Node Architecture

- [ONEX_FOUR_NODE_ARCHITECTURE.md](ONEX_FOUR_NODE_ARCHITECTURE.md) - Node architecture overview
- [NODE_CLASS_HIERARCHY.md](NODE_CLASS_HIERARCHY.md) - Node class hierarchy and inheritance

### Contract Specifications

- [CONTRACT_DRIVEN_NODEEFFECT_V1_0.md](CONTRACT_DRIVEN_NODEEFFECT_V1_0.md) - Effect node specification
- [CONTRACT_DRIVEN_NODEREDUCER_V1_0.md](CONTRACT_DRIVEN_NODEREDUCER_V1_0.md) - Reducer node specification
- [CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md](CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md) - Orchestrator node specification
- [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md) - Compute node specification

### Related Issues

- **OMN-704**: Document mutable state strategy for ONEX nodes
- **OMN-700**: Protocol injection for NodeCompute infrastructure services

---

**Document Version**: 1.0.0
**Created**: 2025-12-14
**Author**: ONEX Architecture Team
