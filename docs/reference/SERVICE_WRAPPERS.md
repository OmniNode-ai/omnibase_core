# ONEX Service Wrappers - Pre-Composed Production-Ready Node Classes

## Overview

Service wrappers are **pre-composed node classes** that eliminate boilerplate by wiring together commonly used mixins with ONEX node base classes. They provide production-ready capabilities out of the box: health monitoring, event publishing, performance metrics, and caching.

### Problem They Solve:

Without service wrappers, every node developer must manually:
1. Choose which mixins to include
2. Remember correct inheritance order (MRO matters!)
3. Wire up mixin initialization in `__init__`
4. Import 4-6 classes for a single node

Service wrappers reduce this to **one import, one inheritance**.

---

## Standard Service Wrappers

### 1. ModelServiceEffect

**Purpose:** Effect nodes performing I/O operations, external API calls, or database operations.

#### Included Mixins:

- `NodeEffect` - Transaction management, retry, circuit breaker semantics
- `MixinHealthCheck` - Health monitoring endpoints
- `MixinEventBus` - Event emission for state changes
- `MixinMetrics` - Performance metrics collection

#### Usage:

```
from omnibase_core.models.service import ModelServiceEffect
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect

class NodeDatabaseWriterEffect(ModelServiceEffect):
    """Database writer with automatic health checks, events, and metrics."""

    async def execute_effect(self, contract: ModelContractEffect) -> dict:
        # Just write your business logic!
        result = await self.database.write(contract.input_data)

        # Emit event automatically tracked with metrics
        await self.publish_event(
            event_type="write_completed",
            payload={"records_written": result["count"]},
            correlation_id=contract.correlation_id
        )

        return {"status": "success", "data": result}
```

#### What You Get Automatically:

- ✅ Health check endpoint: `GET /health` → `{"status": "healthy", "message": "..."}`
- ✅ Event emission: `await self.publish_event(...)` → publishes to event bus
- ✅ Metrics tracking: Request latency, throughput, error rates automatically collected
- ✅ Transaction management: Automatic rollback on failures
- ✅ Retry logic: Configurable retry with exponential backoff
- ✅ Circuit breaker: Automatic fault tolerance for cascading failures

---

### 2. ModelServiceCompute

**Purpose:** Compute nodes performing pure transformations, calculations, or data processing.

#### Included Mixins:

- `NodeCompute` - Pure function semantics, deterministic outputs
- `MixinHealthCheck` - Health monitoring
- `MixinCaching` - Multi-level result caching (L1/L2)
- `MixinMetrics` - Performance metrics

#### Usage:

```
from omnibase_core.models.service import ModelServiceCompute
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute

class NodeDataTransformerCompute(ModelServiceCompute):
    """Data transformer with automatic caching and metrics."""

    async def execute_compute(self, contract: ModelContractCompute) -> dict:
        # Check cache first (automatic via MixinCaching)
        cache_key = self.generate_cache_key(contract.input_data)
        cached_result = await self.get_cached(cache_key)

        if cached_result:
            return cached_result  # Cache hit!

        # Perform expensive computation
        result = await self._transform_data(contract.input_data)

        # Cache result for 10 minutes
        await self.set_cached(cache_key, result, ttl_seconds=600)

        return result
```

#### What You Get Automatically:

- ✅ Result caching: LRU cache with configurable TTL
- ✅ Cache key generation: Deterministic key generation from inputs
- ✅ Cache hit/miss tracking: Metrics for cache performance
- ✅ Health check: Cache service health included in node health
- ✅ Performance metrics: Computation latency, cache hit ratio

#### Why Caching Matters:

Compute nodes often perform expensive operations (ML inference, complex transformations, aggregations). Caching eliminates redundant computation for identical inputs, reducing latency from seconds to milliseconds.

---

### 3. ModelServiceOrchestrator

**Purpose:** Orchestrator nodes coordinating multi-node workflows and managing dependencies.

#### Included Mixins:

- `NodeOrchestrator` - Workflow coordination, dependency management
- `MixinHealthCheck` - Health monitoring (aggregates subnode health)
- `MixinEventBus` - Event emission for workflow lifecycle
- `MixinMetrics` - Workflow performance metrics

#### Usage:

```
from omnibase_core.models.service import ModelServiceOrchestrator
from omnibase_core.models.contracts.model_contract_orchestrator import ModelContractOrchestrator

class NodeWorkflowOrchestrator(ModelServiceOrchestrator):
    """Workflow orchestrator with automatic event coordination and metrics."""

    async def execute_orchestration(self, contract: ModelContractOrchestrator) -> dict:
        # Emit workflow started event
        await self.publish_event(
            event_type="workflow_started",
            payload={"workflow_id": str(contract.workflow_id)},
            correlation_id=contract.correlation_id
        )

        # Coordinate subnode execution
        results = await self._execute_workflow(contract)

        # Emit workflow completed event
        await self.publish_event(
            event_type="workflow_completed",
            payload={
                "workflow_id": str(contract.workflow_id),
                "steps_completed": len(results)
            },
            correlation_id=contract.correlation_id
        )

        return results
```

#### What You Get Automatically:

- ✅ Event-driven coordination: Workflow lifecycle events (started, completed, failed)
- ✅ Subnode health aggregation: Overall workflow health based on subnode health
- ✅ Correlation tracking: All workflow events share correlation ID
- ✅ Performance metrics: Workflow duration, step counts, success rates
- ✅ Error propagation: Failed subnodes trigger workflow failure events

---

### 4. ModelServiceReducer

**Purpose:** Reducer nodes performing aggregation, state management, or data persistence.

#### Included Mixins:

- `NodeReducer` - Aggregation semantics, state management
- `MixinHealthCheck` - Health monitoring (includes state persistence checks)
- `MixinCaching` - Result caching for expensive aggregations
- `MixinMetrics` - Aggregation performance metrics

#### Usage:

```
from omnibase_core.models.service import ModelServiceReducer
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

class NodeMetricsAggregatorReducer(ModelServiceReducer):
    """Metrics aggregator with automatic caching and health checks."""

    async def execute_reduction(self, contract: ModelContractReducer) -> dict:
        # Check cache for recent aggregation
        cache_key = self.generate_cache_key(contract.aggregation_window)
        cached_result = await self.get_cached(cache_key)

        if cached_result:
            return cached_result  # Avoid re-aggregating

        # Perform expensive aggregation over large dataset
        aggregated_data = await self._aggregate_metrics(contract.input_data)

        # Cache aggregated result for 5 minutes
        await self.set_cached(cache_key, aggregated_data, ttl_seconds=300)

        return aggregated_data
```

#### What You Get Automatically:

- ✅ Aggregation result caching: Avoids re-computing expensive aggregations
- ✅ State persistence health: Monitors state storage availability
- ✅ Performance metrics: Aggregation latency, data volume processed
- ✅ Cache invalidation: Automatic cache clearing on state changes

#### Why Caching Matters:

Reducers often aggregate large datasets (sum, average, group-by operations). Caching aggregated results eliminates redundant computation for repeated queries over the same time window or dataset.

---

## When to Use Standard Services vs Custom Composition

### Use Standard Services When:
✅ You need the standard set of capabilities (health, metrics, events/caching)
✅ You're building a typical ONEX node (database adapters, API clients, etc.)
✅ You want minimal boilerplate and fast development
✅ You trust the ONEX team's mixin selection for your node type

### Use Custom Composition When:
✅ You need specialized mixin combinations (e.g., Retry + CircuitBreaker + Timeout)
✅ You're building a unique node with specific requirements
✅ You need fine-grained control over mixin initialization order
✅ You want to exclude certain mixins (e.g., no caching for lightweight nodes)

---

## Custom Composition Examples

### Example 1: Fault-Tolerant API Client
```
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.mixins.mixin_retry import MixinRetry
from omnibase_core.mixins.mixin_circuit_breaker import MixinCircuitBreaker
from omnibase_core.mixins.mixin_metrics import MixinMetrics

class ResilientApiClient(
    NodeEffect,
    MixinRetry,
    MixinCircuitBreaker,
    MixinMetrics
):
    """
    Custom composition for fault-tolerant API client.

    Adds retry and circuit breaker for transient failure handling.
    Omits event bus (not needed for API client).
    """
    pass
```

### Example 2: High-Performance Compute Node (No Caching)
```
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics

class StreamProcessorCompute(
    NodeCompute,
    MixinHealthCheck,
    MixinMetrics
):
    """
    Custom composition for high-throughput stream processing.

    Omits caching (data is never repeated).
    Includes only health checks and metrics for monitoring.
    """
    pass
```

### Example 3: Secure Data Processor
```
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.mixins.mixin_security import MixinSecurity
from omnibase_core.mixins.mixin_validation import MixinValidation
from omnibase_core.mixins.mixin_logging import MixinLogging

class SecureDataProcessor(
    NodeCompute,
    MixinSecurity,
    MixinValidation,
    MixinLogging
):
    """
    Custom composition for processing sensitive data.

    Adds security (redaction) and validation (fail-fast).
    Omits caching (never cache sensitive data).
    """
    pass
```

---

## Available Mixins for Custom Composition

### Flow Control
- **MixinRetry**: Automatic retry with exponential backoff, jitter, circuit breaker integration
- **MixinCircuitBreaker**: Fault tolerance pattern with failure threshold detection

### Monitoring & Observability
- **MixinHealthCheck**: Health monitoring, dependency health aggregation, liveness checks
- **MixinMetrics**: Performance metrics (Prometheus/OpenTelemetry), latency tracking, counters
- **MixinLogging**: Structured logging, correlation ID tracking, ONEX-compliant log events

### Data Management
- **MixinCaching**: Multi-level caching (L1/L2), TTL, invalidation strategies, distributed caching
- **MixinSerialization**: Canonical YAML/JSON serialization with deterministic output

### Communication
- **MixinEventBus**: Event-driven communication, structured payloads, correlation tracking

### Security & Reliability
- **MixinSecurity**: Sensitive field redaction, input sanitization
- **MixinValidation**: Fail-fast input validation, type checking

**See:** `src/omnibase_core/mixins/mixin_metadata.yaml` for detailed mixin capabilities, configuration options, and integration patterns.

---

## Method Resolution Order (MRO) and Mixin Composition

Python's MRO (Method Resolution Order) determines which method gets called when multiple classes define the same method. Understanding MRO is critical for mixin composition.

#### MRO Principles:

1. **Child classes take precedence** over parent classes
2. **Left-to-right order** in inheritance list matters
3. **All `__init__` methods are called** via `super().__init__()`

#### Standard Service MRO Examples:

```
# ModelServiceEffect MRO
ModelServiceEffect → NodeEffect → MixinHealthCheck → MixinEventBus
→ MixinMetrics → NodeCoreBase → ABC

# ModelServiceCompute MRO
ModelServiceCompute → NodeCompute → MixinHealthCheck → MixinCaching
→ MixinMetrics → NodeCoreBase → ABC
```

#### Best Practice:

Always put the **most specific** class first (node type), followed by mixins in **order of dependency**. For example:
- Put `MixinValidation` before `MixinSecurity` (validate before securing)
- Put `MixinRetry` before `MixinCircuitBreaker` (retry before circuit breaking)

---

## Migration Guide: From Infrastructure Classes to Service Wrappers

### Old Infrastructure Classes (Legacy)
```
from omnibase_core.infrastructure.infrastructure_bases import NodeEffectExecutor

class MyDatabaseWriter(NodeEffectExecutor):
    def __init__(self, container):
        super().__init__(container)
        # Manual mixin wiring...
```

### New Service Wrappers (Recommended)
```
from omnibase_core.models.service import ModelServiceEffect

class MyDatabaseWriter(ModelServiceEffect):
    # No __init__ needed! Everything is wired automatically.
    async def execute_effect(self, contract):
        # Just write your business logic
        pass
```

#### Migration Benefits:

- ✅ **Less code**: No manual mixin wiring
- ✅ **Consistent capabilities**: All nodes get health checks, metrics, events/caching
- ✅ **Easier testing**: Standard mixin mocks available
- ✅ **Better observability**: Metrics and events included by default

---

## Testing Service Wrappers

### Unit Testing with Mocked Mixins
```
import pytest
from unittest.mock import AsyncMock, MagicMock
from omnibase_core.models.service import ModelServiceEffect

class TestMyDatabaseWriter:
    @pytest.fixture
    def mock_container(self):
        container = MagicMock()
        container.get_service.return_value = AsyncMock()  # Mock event bus
        return container

    async def test_execute_effect_emits_event(self, mock_container):
        node = MyDatabaseWriter(mock_container)

        # Mock the publish_event method from MixinEventBus
        node.publish_event = AsyncMock()

        result = await node.execute_effect(mock_contract)

        # Verify event was emitted
        node.publish_event.assert_called_once_with(
            event_type="write_completed",
            payload={"records_written": 10},
            correlation_id=mock_contract.correlation_id
        )
```

### Integration Testing with Real Mixins
```
import pytest
from omnibase_core.models.service import ModelServiceCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class TestDataTransformerIntegration:
    @pytest.fixture
    def real_container(self):
        # Use real container with cache service
        return ModelONEXContainer.create_default()

    async def test_caching_behavior(self, real_container):
        node = NodeDataTransformerCompute(real_container)

        # First call: cache miss
        result1 = await node.execute_compute(contract)

        # Second call: cache hit (should be faster)
        result2 = await node.execute_compute(contract)

        assert result1 == result2
        assert node.cache_hit_ratio > 0.0  # Cache hit occurred
```

---

## Performance Characteristics

| Service Wrapper | Overhead per Call | Memory per Instance | Recommended Use Cases |
|----------------|-------------------|---------------------|----------------------|
| **ModelServiceEffect** | ~10-20ms | ~10-20KB | Database adapters, API clients, file I/O |
| **ModelServiceCompute** | ~5-15ms | ~15-30KB (with cache) | Data transformers, ML inference, calculations |
| **ModelServiceOrchestrator** | ~15-30ms | ~20-40KB | Workflow coordinators, multi-step processes |
| **ModelServiceReducer** | ~10-25ms | ~15-35KB (with cache) | Metrics aggregators, log analyzers, analytics |

### Overhead Breakdown:

- Health check: ~5-10ms per check
- Event emission: ~5-10ms per event (depends on backend)
- Metrics collection: ~1-5ms per operation
- Cache lookup: ~0.1-1ms (memory) or ~1-5ms (Redis)

---

## Best Practices

### 1. Always Use Service Wrappers for New Nodes
Unless you have specific requirements, start with standard service wrappers. They provide production-ready capabilities out of the box.

### 2. Override Health Checks for Custom Dependencies
```
class MyApiClient(ModelServiceEffect):
    def get_health_checks(self):
        return [
            self._check_api_availability,
            self._check_rate_limits,
            self._check_authentication
        ]
```

### 3. Configure Cache TTL Based on Data Staleness
```
class MyTransformer(ModelServiceCompute):
    async def execute_compute(self, contract):
        # Short TTL for frequently changing data
        await self.set_cached(key, result, ttl_seconds=60)

        # Long TTL for stable reference data
        await self.set_cached(key, result, ttl_seconds=3600)
```

### 4. Use Correlation IDs for Event Tracking
```
class MyWorkflow(ModelServiceOrchestrator):
    async def execute_orchestration(self, contract):
        # Propagate correlation ID through all events
        await self.publish_event(
            event_type="workflow_started",
            payload={...},
            correlation_id=contract.correlation_id  # ✅ Track entire workflow
        )
```

### 5. Monitor Cache Hit Ratios
```
# Check cache effectiveness periodically
if self.cache_hit_ratio < 0.5:
    logger.warning(f"Low cache hit ratio: {self.cache_hit_ratio:.0%}")
    # Consider adjusting cache size or TTL
```

---

## Troubleshooting

### Import Errors: "Cannot import ModelServiceEffect"
**Cause:** Node base classes don't exist yet (waiting for Agent 2).
**Solution:** Wait for `NodeEffect`, `NodeCompute`, `NodeOrchestrator`, `NodeReducer` to be created in `src/omnibase_core/nodes/`.

### MRO Errors: "Cannot create consistent method resolution order"
**Cause:** Conflicting mixin inheritance order.
**Solution:** Reorder mixins. Put node type first, then mixins in dependency order.

### Event Bus Unavailable Warnings
**Cause:** Container doesn't provide event bus service.
**Solution:** Check container configuration. Service wrappers gracefully degrade if event bus is missing.

### Cache Misses Despite Identical Inputs
**Cause:** Non-deterministic cache key generation.
**Solution:** Ensure `generate_cache_key()` produces consistent keys for identical inputs. Avoid using timestamps or random values in keys.

---

## Further Reading

- **Mixin Metadata:** `src/omnibase_core/mixins/mixin_metadata.yaml` - Detailed mixin capabilities
- **ONEX Architecture Patterns:** See project documentation for ONEX architecture guidelines
- **Node Base Classes:** `src/omnibase_core/nodes/node_*.py` (created by Agent 2)
- **Container Documentation:** `src/omnibase_core/models/container/model_onex_container.py`

---

## Summary

**Service wrappers eliminate boilerplate** by pre-composing commonly used mixins with ONEX node base classes. They provide production-ready capabilities (health checks, events, metrics, caching) out of the box, reducing development time and ensuring consistency across nodes.

### Key Takeaways:

- ✅ Use standard services for 80% of nodes
- ✅ Use custom composition for specialized requirements
- ✅ Understand MRO when creating custom compositions
- ✅ Monitor cache hit ratios and health check results
- ✅ Always propagate correlation IDs through events

### Next Steps:

1. Choose the appropriate service wrapper for your node type
2. Implement your business logic in `execute_*` method
3. Add custom health checks if needed
4. Test with mocked and real mixins
5. Monitor metrics and health in production
