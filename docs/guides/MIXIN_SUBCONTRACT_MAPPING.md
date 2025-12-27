# Mixin-Subcontract Mapping Guide

**Version**: 1.0.0
**Last Updated**: 2025-11-19
**Status**: Comprehensive Architecture Reference

## Overview

This guide explains the relationship between **mixins** (runtime behavior) and **subcontracts** (declarative configuration) in the ONEX architecture. Understanding this distinction is critical for designing nodes correctly.

---

## Quick Reference: Mixin vs. Subcontract

| Aspect | Mixin | Subcontract |
|--------|-------|-------------|
| **Purpose** | Provides runtime behavior | Provides declarative configuration |
| **Layer** | Python class methods | Pydantic model (YAML → Python) |
| **When Used** | Inherited into node classes | Composed into node contracts |
| **Configuration** | Imperative (code) | Declarative (YAML/JSON) |
| **Examples** | `MixinFSMExecution` | `ModelFSMSubcontract` |
| **File Location** | `src/omnibase_core/mixins/` | `src/omnibase_core/models/contracts/subcontracts/` |

---

## Three-Layer Architecture

The ONEX framework uses a three-layer architecture for mixing declarative and imperative programming:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: YAML Contract (Declarative)                       │
│ ─────────────────────────────────────────────────────────── │
│ node_contract.yaml:                                         │
│   fsm_subcontract:                                          │
│     state_machine_name: "OrderProcessing"                   │
│     initial_state: "pending"                                │
│     transitions:                                            │
│       - from_state: "pending"                               │
│         to_state: "confirmed"                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Pydantic Model (Type-Safe Validation)             │
│ ─────────────────────────────────────────────────────────── │
│ ModelFSMSubcontract:                                        │
│   - Validates state machine configuration                  │
│   - Enforces constraints (initial state exists, etc.)      │
│   - Provides type-safe access to config                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Python Mixin (Runtime Behavior)                   │
│ ─────────────────────────────────────────────────────────── │
│ MixinFSMExecution:                                          │
│   - Executes state transitions                              │
│   - Validates transition legality                           │
│   - Emits ModelIntent for side effects                      │
│   - Uses subcontract for configuration                      │
└─────────────────────────────────────────────────────────────┘
```

**Flow**: YAML → Pydantic → Python → Runtime Execution

---

## Declarative Mixins (8 Total)

These mixins have dedicated subcontracts for YAML-based configuration:

### 1. MixinFSMExecution ↔ ModelFSMSubcontract

**Purpose**: Finite state machine execution with pure transitions

**Subcontract**: `ModelFSMSubcontract`

**Applicable Node Types**: REDUCER (primary), ALL (optional)

**Configuration Example**:

```
fsm_subcontract:
  state_machine_name: "OrderLifecycle"
  state_machine_version: {major: 1, minor: 0, patch: 0}
  description: "Order processing state machine"

  states:
    - state_name: "pending"
      is_initial: true
      description: "Order awaiting payment"
    - state_name: "confirmed"
      description: "Payment received"
    - state_name: "shipped"
      description: "Order in transit"
    - state_name: "delivered"
      is_terminal: true
      description: "Order completed"
    - state_name: "cancelled"
      is_terminal: true
      is_error: true
      description: "Order cancelled"

  initial_state: "pending"
  terminal_states: ["delivered", "cancelled"]
  error_states: ["cancelled"]

  transitions:
    - from_state: "pending"
      to_state: "confirmed"
      event_trigger: "PAYMENT_RECEIVED"
    - from_state: "confirmed"
      to_state: "shipped"
      event_trigger: "SHIPMENT_CREATED"
    - from_state: "shipped"
      to_state: "delivered"
      event_trigger: "DELIVERY_CONFIRMED"
    - from_state: "*"  # Wildcard: any state
      to_state: "cancelled"
      event_trigger: "CANCEL_ORDER"

  persistence_enabled: true
  checkpoint_interval_ms: 30000
  recovery_enabled: true
  rollback_enabled: true
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution

class OrderReducer(NodeReducer, MixinFSMExecution):
    """REDUCER node with FSM capabilities."""

    async def execute_reduction(self, contract: ModelContractReducer):
        # Access FSM configuration from subcontract
        fsm_config = contract.fsm_subcontract

        # Execute state transition (pure FSM)
        result = await self.execute_transition(
            current_state="pending",
            event="PAYMENT_RECEIVED",
            fsm_config=fsm_config
        )

        # Returns: (new_state, intents[])
        # new_state = "confirmed"
        # intents = [ModelIntent(DATABASE_WRITE, ...), ...]
        return result
```

---

### 2. MixinCaching ↔ ModelCachingSubcontract

**Purpose**: Cache strategies and performance optimization

**Subcontract**: `ModelCachingSubcontract`

**Applicable Node Types**: ALL

**Configuration Example**:

```
caching_subcontract:
  caching_enabled: true
  cache_strategy: "lru"  # lru, lfu, fifo, ttl
  cache_backend: "memory"  # memory, redis, memcached

  max_entries: 10000
  max_memory_mb: 512
  entry_size_limit_kb: 1024

  key_strategy:
    key_generation_method: "composite_hash"
    include_correlation_id: true
    include_timestamp: false

  invalidation_policy:
    invalidation_strategy: "ttl_based"
    default_ttl_seconds: 3600
    max_ttl_seconds: 86400

  # Multi-level caching (L1/L2)
  multi_level_enabled: true
  l1_cache_size: 1000
  l2_cache_size: 10000
  promotion_threshold: 3

  metrics_enabled: true
  hit_ratio_threshold: 0.8
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_caching import MixinCaching

class FastComputeNode(NodeCompute, MixinCaching):
    """COMPUTE node with caching."""

    async def execute_compute(self, contract: ModelContractCompute):
        cache_config = contract.caching_subcontract

        # Check cache
        cached = await self.get_from_cache(
            key=self.generate_cache_key(contract.input_data),
            config=cache_config
        )

        if cached:
            return cached

        # Compute result
        result = await self.expensive_computation(contract.input_data)

        # Store in cache
        await self.store_in_cache(
            key=self.generate_cache_key(contract.input_data),
            value=result,
            config=cache_config
        )

        return result
```

---

### 3. MixinWorkflowExecution ↔ ModelWorkflowCoordinationSubcontract

**Purpose**: Workflow coordination and multi-step execution

**Subcontract**: `ModelWorkflowCoordinationSubcontract`

**Applicable Node Types**: ORCHESTRATOR (exclusive)

**Configuration Example**:

```
workflow_coordination_subcontract:
  max_concurrent_workflows: 10
  default_workflow_timeout_ms: 600000  # 10 minutes
  node_coordination_timeout_ms: 30000
  checkpoint_interval_ms: 60000

  auto_retry_enabled: true
  max_retries: 3
  retry_delay_ms: 2000
  exponential_backoff: true

  parallel_execution_enabled: true
  workflow_persistence_enabled: true
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_workflow_execution import MixinWorkflowExecution

class WorkflowOrchestrator(NodeOrchestrator, MixinWorkflowExecution):
    """ORCHESTRATOR node with workflow coordination."""

    async def execute_orchestration(self, contract: ModelContractOrchestrator):
        workflow_config = contract.workflow_coordination_subcontract

        # Coordinate multi-step workflow
        workflow_id = await self.start_workflow(
            workflow_name="DataPipeline",
            config=workflow_config
        )

        # Execute steps with coordination
        result = await self.execute_workflow_steps(
            workflow_id=workflow_id,
            steps=[
                {"node": "effect", "operation": "fetch_data"},
                {"node": "compute", "operation": "transform"},
                {"node": "reducer", "operation": "aggregate"}
            ],
            config=workflow_config
        )

        return result
```

---

### 4. MixinHealthCheck ↔ ModelHealthCheckSubcontract

**Purpose**: Health monitoring and status reporting

**Subcontract**: `ModelHealthCheckSubcontract`

**Applicable Node Types**: ALL

**Configuration Example**:

```
health_check_subcontract:
  check_interval_ms: 30000
  failure_threshold: 3
  recovery_threshold: 2
  timeout_ms: 5000

  include_dependency_checks: true
  include_component_checks: true
  enable_health_score_calculation: true
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck

class MonitoredNode(NodeCompute, MixinHealthCheck):
    """Node with health monitoring."""

    async def health_check(self):
        config = self.contract.health_check_subcontract

        # Perform comprehensive health check
        status = await self.check_health(
            include_dependencies=config.include_dependency_checks,
            include_components=config.include_component_checks,
            timeout_ms=config.timeout_ms
        )

        return status  # ModelNodeHealthStatus
```

---

### 5. MixinMetrics ↔ ModelMetricsSubcontract

**Purpose**: Metrics collection and performance tracking

**Subcontract**: `ModelMetricsSubcontract`

**Applicable Node Types**: ALL

**Configuration Example**:

```
metrics_subcontract:
  metrics_enabled: true
  metrics_backend: "prometheus"  # prometheus, statsd, none

  enable_histograms: true
  enable_counters: true
  enable_gauges: true
  enable_summaries: false

  collection_interval_seconds: 60
  export_interval_seconds: 10

  enable_performance_metrics: true
  track_response_times: true
  track_throughput: true
  track_error_rates: true

  max_label_cardinality: 1000
  aggregation_window_seconds: 300
  retention_period_hours: 168  # 7 days
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_metrics import MixinMetrics

class MetricCollectingNode(NodeEffect, MixinMetrics):
    """Node with metrics collection."""

    async def execute_effect(self, contract: ModelContractEffect):
        metrics_config = contract.metrics_subcontract

        # Record execution metrics
        with self.track_execution_time(
            metric_name="effect_execution",
            config=metrics_config
        ):
            result = await self.perform_effect_operation(contract)

        # Record custom metric
        await self.record_metric(
            name="operations_completed",
            value=1,
            metric_type="counter",
            config=metrics_config
        )

        return result
```

---

### 6. MixinDiscoveryResponder ↔ ModelDiscoverySubcontract

**Purpose**: Service discovery and introspection response

**Subcontract**: `ModelDiscoverySubcontract`

**Applicable Node Types**: ALL

**Configuration Example**:

```
discovery_subcontract:
  enabled: true
  auto_start: true

  # Rate limiting
  response_throttle_seconds: 1.0
  response_timeout_seconds: 5.0

  # Capability advertisement
  advertise_capabilities: true
  custom_capabilities:
    - "high_performance"
    - "fault_tolerant"

  # Event bus integration
  discovery_channels:
    - "onex.discovery.broadcast"
    - "onex.discovery.response"
  use_dedicated_consumer_group: true

  # Response content
  include_introspection: true
  include_event_channels: true
  include_version_info: true
  include_health_status: true

  # Performance
  max_response_size_bytes: 102400
  enable_response_compression: false

  # Monitoring
  enable_metrics: true
  enable_detailed_logging: false
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder

class DiscoverableNode(NodeCompute, MixinDiscoveryResponder):
    """Node that responds to discovery broadcasts."""

    async def handle_discovery_request(self, event):
        discovery_config = self.contract.discovery_subcontract

        # Auto-respond to discovery broadcasts
        response = await self.generate_discovery_response(
            request=event,
            config=discovery_config
        )

        # Response includes: introspection, health, capabilities, etc.
        return response
```

---

### 7. MixinIntrospection ↔ ModelIntrospectionSubcontract

**Purpose**: Node metadata exposure and schema export

**Subcontract**: `ModelIntrospectionSubcontract`

**Applicable Node Types**: ALL

**Configuration Example**:

```
introspection_subcontract:
  introspection_enabled: true

  # Metadata inclusion
  include_metadata: true
  include_core_metadata: true
  include_organization_metadata: true

  # Contract and schema
  include_contract: true
  include_input_schema: true
  include_output_schema: true
  include_cli_interface: true

  # Capabilities and dependencies
  include_capabilities: true
  include_dependencies: true
  include_optional_dependencies: true

  # Filtering and depth
  depth_limit: 10
  exclude_field_patterns:
    - "password"
    - "secret"
    - "token"
    - "api_key"

  # Schema export
  export_json_schema: true
  export_openapi_schema: false

  # Caching
  cache_introspection_response: true
  cache_ttl_seconds: 300

  # Security
  redact_sensitive_info: true
  require_authentication: false
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_introspection import MixinIntrospection

class IntrospectableNode(NodeReducer, MixinIntrospection):
    """Node with introspection capabilities."""

    async def get_introspection_data(self):
        intro_config = self.contract.introspection_subcontract

        # Generate introspection response
        data = await self.introspect(
            include_metadata=intro_config.include_metadata,
            include_contract=intro_config.include_contract,
            depth_limit=intro_config.depth_limit,
            redact_sensitive=intro_config.redact_sensitive_info
        )

        return data  # Full node metadata, schemas, capabilities
```

---

### 8. MixinEventHandler ↔ ModelEventHandlingSubcontract

**Purpose**: Event subscription and handling

**Subcontract**: `ModelEventHandlingSubcontract`

**Applicable Node Types**: ALL

**Configuration Example**:

```
event_handling_subcontract:
  enabled: true

  # Event subscription
  subscribed_events:
    - "NODE_INTROSPECTION_REQUEST"
    - "NODE_DISCOVERY_REQUEST"
    - "DATA_UPDATED"
    - "WORKFLOW_COMPLETED"
  auto_subscribe_on_init: true

  # Event filtering
  enable_node_id_filtering: true
  enable_node_name_filtering: true
  respond_to_all_when_no_filter: true

  # Introspection handling
  handle_introspection_requests: true
  handle_discovery_requests: true
  filter_introspection_data: true

  # Event bus support
  async_event_bus_support: true
  sync_event_bus_fallback: true
  cleanup_on_shutdown: true

  # Retry and resilience
  max_retries: 3
  retry_delay_seconds: 1.0
  retry_exponential_backoff: true

  # Dead letter queue
  dead_letter_channel: "dlq.events.failed"
  dead_letter_max_events: 1000
  dead_letter_overflow_strategy: "drop_oldest"

  # Error handling
  fail_fast_on_handler_errors: false
  log_handler_errors: true
  emit_error_events: true

  # Performance
  track_handler_performance: true
  handler_timeout_seconds: 30.0
```

**Runtime Behavior**:

```
from omnibase_core.mixins.mixin_event_handler import MixinEventHandler

class EventDrivenNode(NodeEffect, MixinEventHandler):
    """Node with event handling."""

    async def initialize(self):
        event_config = self.contract.event_handling_subcontract

        # Auto-subscribe to configured events
        await self.subscribe_to_events(
            events=event_config.subscribed_events,
            async_support=event_config.async_event_bus_support
        )

    async def handle_event(self, event):
        event_config = self.contract.event_handling_subcontract

        # Process event with retry and DLQ
        try:
            result = await self.process_event(
                event=event,
                config=event_config
            )
        except Exception as e:
            if event_config.max_retries > 0:
                await self.retry_with_backoff(event, config=event_config)
            else:
                await self.send_to_dlq(event, config=event_config)
```

---

## Imperative Mixins (33 Total)

These mixins provide runtime behavior **without** dedicated subcontracts:

### Why No Subcontract?

Imperative mixins typically:
1. **Provide utility methods** - No configuration needed
2. **Have minimal state** - Behavior is fixed
3. **Are context-dependent** - Configuration varies by usage
4. **Are too granular** - Subcontract would be overkill

### Complete List of Imperative Mixins

| Mixin | Purpose | Node Types | Example Usage |
|-------|---------|------------|---------------|
| `MixinRetry` | Automatic retry with exponential backoff | ALL | Retry failed operations |
| `MixinTimeout` | Timeout enforcement for operations | ALL | Prevent hanging operations |
| `MixinCircuitBreaker` | Circuit breaker pattern | EFFECT | Protect external services |
| `MixinRateLimiter` | Rate limiting and throttling | EFFECT | Limit API call rates |
| `MixinBulkhead` | Bulkhead isolation pattern | ALL | Resource isolation |
| `MixinEventBus` | Event bus publication | ALL | Publish events |
| `MixinEventListener` | Event subscription | ALL | Subscribe to events |
| `MixinEventDrivenNode` | Event-driven coordination | ORCHESTRATOR | Event-based workflows |
| `MixinRequestResponseIntrospection` | Request/response logging | ALL | Debug and audit |
| `MixinNodeLifecycle` | Lifecycle hooks | ALL | Startup/shutdown logic |
| `MixinNodeExecutor` | Node execution wrapper | ALL | Execution boilerplate |
| `MixinHybridExecution` | Sync/async execution | ALL | Mixed execution modes |
| `MixinSerializable` | Serialization helpers | ALL | JSON/YAML serialization |
| `MixinCanonicalSerialization` | Canonical form serialization | ALL | Deterministic serialization |
| `MixinLazyValue` | Lazy evaluation | ALL | Deferred computation |
| `MixinNodeIntrospectionData` | Introspection data structures | ALL | Data models |
| `ModelLogData` | Structured logging data | ALL | Log formatting |
| `ModelCompletionData` | Completion tracking data | ALL | Status tracking |
| `MixinCLIHandler` | CLI command handling | ALL | Command-line interface |
| `MixinValidation` | Input validation | ALL | Data validation |
| `MixinSecurity` | Security utilities | ALL | Auth/authz helpers |
| `MixinLogging` | Logging utilities | ALL | Structured logging |
| `MixinTelemetry` | Telemetry collection | ALL | Distributed tracing |
| `MixinObservability` | Observability hooks | ALL | Monitoring integration |
| `MixinResourceManager` | Resource pooling | EFFECT | Connection pools |
| `MixinTransactionManager` | Transaction coordination | REDUCER | ACID guarantees |
| `MixinStateManager` | State persistence | REDUCER | State storage |
| `MixinDependencyResolver` | Dependency injection | ORCHESTRATOR | Service resolution |
| `MixinWorkflowStep` | Workflow step definition | ORCHESTRATOR | Step execution |
| `MixinParallelExecution` | Parallel processing | COMPUTE | Data parallelism |
| `MixinDataTransformation` | Data mapping | COMPUTE | ETL operations |
| `MixinAlgorithmRegistry` | Algorithm selection | COMPUTE | Dynamic algorithms |
| `MixinPerformanceOptimization` | Performance tuning | ALL | Optimization hints |

---

## Decision Framework: When to Create a Subcontract

Use this decision tree when considering whether a new mixin needs a subcontract:

```
┌─────────────────────────────────────┐
│ Does the mixin require runtime     │
│ configuration from YAML contracts?  │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │ YES            │ NO → Use imperative mixin only
       ▼                │      (e.g., MixinSerializable)
┌──────────────────────┐
│ Is the configuration │
│ complex or structured?│
└──────┬───────────────┘
       │
   ┌───┴────┐
   │ YES    │ NO → Use simple config fields
   ▼        │      (e.g., retry_enabled: bool)
┌────────────────────────┐
│ Does the configuration │
│ have validation rules? │
└──────┬─────────────────┘
       │
   ┌───┴────┐
   │ YES    │ NO → Consider if complexity warrants subcontract
   ▼        │
┌────────────────────────────┐
│ Will multiple nodes share  │
│ this configuration pattern?│
└──────┬─────────────────────┘
       │
   ┌───┴────┐
   │ YES    │ NO → Maybe just use inline config
   ▼        │
┌──────────────────────┐
│ CREATE SUBCONTRACT   │
└──────────────────────┘
```

### Examples

**CREATE Subcontract**:
- ✅ FSM configuration (complex states, transitions, validation)
- ✅ Caching strategies (multiple backends, eviction policies)
- ✅ Workflow coordination (timeouts, retries, checkpoints)

**DON'T CREATE Subcontract**:
- ❌ Simple retry flag (`retry_enabled: bool`)
- ❌ Single timeout value (`timeout_ms: int`)
- ❌ Utility methods with no configuration (serialization helpers)

---

## Usage Examples by Node Type

### EFFECT Node Example

```
# EFFECT node contract
effect_contract:
  node_type: "EFFECT"

  # Declarative subcontracts
  caching_subcontract:
    caching_enabled: true
    cache_strategy: "lru"
    max_entries: 1000

  health_check_subcontract:
    check_interval_ms: 30000
    failure_threshold: 3

  metrics_subcontract:
    metrics_enabled: true
    metrics_backend: "prometheus"

  discovery_subcontract:
    enabled: true
    advertise_capabilities: true
```

```
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.mixins.mixin_caching import MixinCaching
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder

class MyEffectNode(
    NodeEffect,
    MixinCaching,
    MixinHealthCheck,
    MixinMetrics,
    MixinDiscoveryResponder
):
    """EFFECT node with caching, health checks, metrics, and discovery."""

    async def execute_effect(self, contract: ModelContractEffect):
        # All subcontract configurations available via contract
        cache_config = contract.caching_subcontract
        health_config = contract.health_check_subcontract
        metrics_config = contract.metrics_subcontract

        # Runtime behavior provided by mixins
        cached = await self.get_from_cache(key, cache_config)
        await self.record_metric("effect_calls", 1, metrics_config)

        return result
```

### COMPUTE Node Example

```
compute_contract:
  node_type: "COMPUTE"

  caching_subcontract:
    multi_level_enabled: true
    l1_cache_size: 100
    l2_cache_size: 1000

  metrics_subcontract:
    track_response_times: true
    enable_histograms: true

  introspection_subcontract:
    include_input_schema: true
    include_output_schema: true
```

```
class MyComputeNode(
    NodeCompute,
    MixinCaching,
    MixinMetrics,
    MixinIntrospection
):
    """COMPUTE node with multi-level caching and introspection."""
    pass
```

### REDUCER Node Example

```
reducer_contract:
  node_type: "REDUCER"

  fsm_subcontract:
    state_machine_name: "OrderFSM"
    initial_state: "pending"
    transitions:
      - from_state: "pending"
        to_state: "confirmed"
        event_trigger: "PAYMENT_RECEIVED"

  event_handling_subcontract:
    subscribed_events:
      - "PAYMENT_RECEIVED"
      - "ORDER_CANCELLED"
    max_retries: 3
```

```
class MyReducerNode(
    NodeReducer,
    MixinFSMExecution,
    MixinEventHandler
):
    """REDUCER node with FSM and event handling."""
    pass
```

### ORCHESTRATOR Node Example

```
orchestrator_contract:
  node_type: "ORCHESTRATOR"

  workflow_coordination_subcontract:
    max_concurrent_workflows: 5
    default_workflow_timeout_ms: 300000
    auto_retry_enabled: true

  event_handling_subcontract:
    subscribed_events:
      - "WORKFLOW_STEP_COMPLETED"
      - "WORKFLOW_FAILED"
```

```
class MyOrchestratorNode(
    NodeOrchestrator,
    MixinWorkflowExecution,
    MixinEventHandler
):
    """ORCHESTRATOR node with workflow coordination."""
    pass
```

---

## Common Patterns

### Pattern 1: Declarative + Imperative Hybrid

```
# Declarative: FSM configuration
fsm_subcontract:
  state_machine_name: "DataProcessing"
  initial_state: "raw"
  transitions:
    - from_state: "raw"
      to_state: "processed"
```

```
# Imperative: Retry logic (no subcontract needed)
from omnibase_core.mixins.mixin_retry import MixinRetry

class HybridNode(NodeReducer, MixinFSMExecution, MixinRetry):
    async def execute_reduction(self, contract):
        # Declarative FSM from subcontract
        fsm_config = contract.fsm_subcontract

        # Imperative retry (no config needed)
        @self.with_retry(max_retries=3, backoff="exponential")
        async def transition_with_retry():
            return await self.execute_transition(
                current_state="raw",
                event="PROCESS_DATA",
                fsm_config=fsm_config
            )

        return await transition_with_retry()
```

### Pattern 2: Progressive Enhancement

Start simple (imperative) → Add complexity (declarative):

**Phase 1 - Imperative**:
```
class SimpleNode(NodeCompute):
    async def execute_compute(self, contract):
        # Hardcoded caching
        cache = {}
        if key in cache:
            return cache[key]

        result = await self.compute()
        cache[key] = result
        return result
```

**Phase 2 - Declarative** (when complexity grows):
```
caching_subcontract:
  cache_strategy: "lru"
  max_entries: 10000
  multi_level_enabled: true
```

```
from omnibase_core.mixins.mixin_caching import MixinCaching

class AdvancedNode(NodeCompute, MixinCaching):
    async def execute_compute(self, contract):
        # Declarative caching from subcontract
        cache_config = contract.caching_subcontract

        cached = await self.get_from_cache(key, cache_config)
        if cached:
            return cached

        result = await self.compute()
        await self.store_in_cache(key, result, cache_config)
        return result
```

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Creating Subcontracts for Simple Flags

**DON'T DO THIS**:

```
# Overkill for a single boolean
retry_subcontract:
  enabled: true
```

**DO THIS INSTEAD**:

```
# Simple config field
retry_enabled: true
max_retries: 3
```

### ❌ Anti-Pattern 2: Hardcoding Config in Mixins

**DON'T DO THIS**:

```
class MixinCaching:
    def __init__(self):
        self.max_entries = 1000  # HARDCODED!
```

**DO THIS INSTEAD**:

```
class MixinCaching:
    async def get_from_cache(self, key, config: ModelCachingSubcontract):
        max_entries = config.max_entries  # From subcontract
```

### ❌ Anti-Pattern 3: Mixing Concerns in Subcontracts

**DON'T DO THIS**:

```
# Kitchen sink subcontract
mega_subcontract:
  caching_enabled: true
  metrics_enabled: true
  fsm_enabled: true
  workflow_enabled: true
```

**DO THIS INSTEAD**:

```
# Separate concerns
caching_subcontract: {...}
metrics_subcontract: {...}
fsm_subcontract: {...}
workflow_coordination_subcontract: {...}
```

---

## Migration Guide

### Migrating Imperative to Declarative

**Before** (Imperative):

```
class MyNode(NodeCompute):
    def __init__(self, container):
        super().__init__(container)
        self.cache = LRUCache(max_size=1000)
        self.cache_ttl = 3600
```

**After** (Declarative):

```
# node_contract.yaml
caching_subcontract:
  cache_strategy: "lru"
  max_entries: 1000
  invalidation_policy:
    default_ttl_seconds: 3600
```

```
from omnibase_core.mixins.mixin_caching import MixinCaching

class MyNode(NodeCompute, MixinCaching):
    # Configuration now comes from subcontract
    pass
```

---

## Summary

| Total Count | Declarative (Subcontracts) | Imperative (No Subcontract) |
|-------------|----------------------------|------------------------------|
| **41 Mixins** | **8 Mixins** | **33 Mixins** |

**Declarative Mixins** (8):
1. MixinFSMExecution → ModelFSMSubcontract
2. MixinCaching → ModelCachingSubcontract
3. MixinWorkflowExecution → ModelWorkflowCoordinationSubcontract
4. MixinHealthCheck → ModelHealthCheckSubcontract
5. MixinMetrics → ModelMetricsSubcontract
6. MixinDiscoveryResponder → ModelDiscoverySubcontract
7. MixinIntrospection → ModelIntrospectionSubcontract
8. MixinEventHandler → ModelEventHandlingSubcontract

**Key Takeaways**:
- **Subcontracts** = Declarative YAML configuration (8 mixins)
- **Mixins** = Runtime behavior (all 41 mixins)
- Use subcontracts for **complex, reusable, validated** configuration
- Use imperative mixins for **simple utilities** and **context-dependent** behavior
- The three-layer architecture (YAML → Pydantic → Python) ensures type safety and validation

---

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Node Building Guide](./node-building/README.md)
- [Migration Guide: Declarative Nodes](./MIGRATING_TO_DECLARATIVE_NODES.md)
- [Mixin Metadata](../../src/omnibase_core/mixins/mixin_metadata.yaml)
- [Subcontract Reference](../../src/omnibase_core/models/contracts/subcontracts/__init__.py)

---

**Last Updated**: 2025-11-19
**Version**: 1.0.0
**Correlation ID**: `fbe7a832-7fc8-4d12-9e92-5a8d0b8e6c4a`
