# MixinNodeService Integration Test Plan

**Document Version:** 1.0
**Date:** 2025-10-16
**Status:** Planning Phase
**Target:** Unit test coverage for MixinNodeService integration with all 4 service models

---

## 1. Executive Summary

### 1.1 Scope

This test plan covers comprehensive unit testing for `MixinNodeService` integration with all four ONEX service models:

1. **ModelServiceEffect** - I/O operations, external APIs, database operations
2. **ModelServiceCompute** - Pure transformations, deterministic outputs
3. **ModelServiceReducer** - Aggregation, state management, persistence
4. **ModelServiceOrchestrator** - Workflow coordination, dependency management

### 1.2 Key Testing Objectives

- **Service Lifecycle**: Validate `start_service_mode()` and `stop_service_mode()` behavior
- **Event Handling**: Verify TOOL_INVOCATION event processing and TOOL_RESPONSE emission
- **Health Monitoring**: Test `get_service_health()` and health monitoring loop
- **Graceful Shutdown**: Ensure proper cleanup and active invocation completion
- **Error Handling**: Validate error scenarios and response generation
- **Performance Tracking**: Verify metrics collection (invocations, success rates, timing)
- **Mixin Integration**: Test interactions with EventBus, HealthCheck, Metrics, Caching mixins
- **MRO Correctness**: Validate Method Resolution Order for all service models

### 1.3 Testing Approach

- **Isolation**: Each test should be independent and not rely on external services
- **Mocking**: Mock external dependencies (event bus, container, databases)
- **Async Testing**: Use `pytest.mark.asyncio` for async methods
- **Coverage Target**: 95%+ line coverage, 100% branch coverage for critical paths
- **Performance**: All tests should complete in <5s per test class

---

## 2. MixinNodeService Capabilities Analysis

### 2.1 Core Capabilities

| Capability | Methods | Dependencies | Priority |
|------------|---------|--------------|----------|
| **Service Lifecycle** | `start_service_mode()`, `stop_service_mode()` | EventBus, Signal Handlers | Critical |
| **Tool Invocation Handling** | `handle_tool_invocation()` | EventBus, Node.run() | Critical |
| **Health Monitoring** | `get_service_health()`, `_health_monitor_loop()` | Performance Metrics | High |
| **Graceful Shutdown** | `_wait_for_active_invocations()`, `_emit_shutdown_event()` | EventBus | High |
| **Signal Handling** | `_register_signal_handlers()` | OS Signals (SIGTERM, SIGINT) | Medium |
| **Performance Tracking** | Metrics attributes | Time tracking | High |
| **Shutdown Callbacks** | `add_shutdown_callback()` | Callback list | Medium |
| **Event Subscription** | `_subscribe_to_tool_invocations()` | EventBus | Critical |
| **Input State Conversion** | `_convert_event_to_input_state()` | Node contracts | High |
| **Tool Execution** | `_execute_tool()` | Node.run() | Critical |
| **Result Serialization** | `_serialize_result()` | Pydantic models | High |
| **Response Emission** | `_emit_tool_response()` | EventBus | Critical |

### 2.2 State Management

**Service State Attributes:**
- `_service_running: bool` - Service active flag
- `_service_task: asyncio.Task | None` - Main service task
- `_health_task: asyncio.Task | None` - Health monitoring task
- `_active_invocations: set[UUID]` - Active tool invocations
- `_shutdown_requested: bool` - Shutdown signal flag
- `_shutdown_callbacks: list[Callable]` - Cleanup callbacks

**Performance Metrics:**
- `_total_invocations: int` - Total tool calls
- `_successful_invocations: int` - Successful completions
- `_failed_invocations: int` - Failed invocations
- `_start_time: float | None` - Service start timestamp

---

## 3. Service Model Compositions

### 3.1 ModelServiceEffect

**MRO:** `MixinNodeService → NodeEffect → MixinHealthCheck → MixinEventBus → MixinMetrics → NodeCoreBase → ABC`

**Included Mixins:**
- `MixinNodeService` - Persistent service mode
- `MixinHealthCheck` - Health monitoring
- `MixinEventBus` - Event publishing
- `MixinMetrics` - Performance metrics

**Key Characteristics:**
- Transaction management (via NodeEffect)
- Circuit breaker pattern
- Retry logic with backoff
- Event emission for state changes

**Integration Points:**
- EventBus: Tool invocations, tool responses, state change events
- HealthCheck: Service health + transaction health
- Metrics: Invocation timing, success rates, circuit breaker state

### 3.2 ModelServiceCompute

**MRO:** `MixinNodeService → NodeCompute → MixinHealthCheck → MixinCaching → MixinMetrics → NodeCoreBase → ABC`

**Included Mixins:**
- `MixinNodeService` - Persistent service mode
- `MixinHealthCheck` - Health monitoring
- `MixinCaching` - Result caching
- `MixinMetrics` - Performance metrics

**Key Characteristics:**
- Pure function semantics (no side effects)
- Result caching for expensive operations
- Deterministic outputs
- Idempotent operations

**Integration Points:**
- EventBus: Tool invocations, tool responses
- HealthCheck: Service health + cache health
- Caching: Result caching, cache hit/miss tracking
- Metrics: Invocation timing, cache hit rates

### 3.3 ModelServiceReducer

**MRO:** `MixinNodeService → NodeReducer → MixinHealthCheck → MixinCaching → MixinMetrics → NodeCoreBase → ABC`

**Included Mixins:**
- `MixinNodeService` - Persistent service mode
- `MixinHealthCheck` - Health monitoring
- `MixinCaching` - Result caching (critical for aggregations)
- `MixinMetrics` - Performance metrics

**Key Characteristics:**
- Aggregation operations (sum, average, group-by)
- State management and persistence
- Cache invalidation on state changes
- Result caching for expensive aggregations

**Integration Points:**
- EventBus: Tool invocations, tool responses
- HealthCheck: Service health + state persistence health
- Caching: Aggregation caching, cache invalidation
- Metrics: Invocation timing, aggregation performance

### 3.4 ModelServiceOrchestrator

**MRO:** `MixinNodeService → NodeOrchestrator → MixinHealthCheck → MixinEventBus → MixinMetrics → NodeCoreBase → ABC`

**Included Mixins:**
- `MixinNodeService` - Persistent service mode
- `MixinHealthCheck` - Health monitoring
- `MixinEventBus` - Event publishing (critical for coordination)
- `MixinMetrics` - Performance metrics

**Key Characteristics:**
- Workflow coordination
- Dependency management
- Subnode health aggregation
- Correlation ID tracking across workflow steps

**Integration Points:**
- EventBus: Tool invocations, workflow lifecycle events, subnode coordination
- HealthCheck: Service health + subnode health aggregation
- Metrics: Workflow timing, step completion rates

---

## 4. Test Organization Structure

### 4.1 Directory Structure

```
tests/unit/mixins/
├── test_mixin_node_service.py              # Core MixinNodeService tests
└── test_mixin_node_service_integration/
    ├── __init__.py
    ├── test_service_effect_integration.py
    ├── test_service_compute_integration.py
    ├── test_service_reducer_integration.py
    ├── test_service_orchestrator_integration.py
    ├── test_mixin_interactions.py          # Cross-mixin integration tests
    ├── test_mro_correctness.py             # MRO validation tests
    └── fixtures.py                         # Shared fixtures
```

### 4.2 Test Class Naming Convention

- **Unit Tests**: `Test<ClassName><Capability>`
  - `TestMixinNodeServiceLifecycle`
  - `TestMixinNodeServiceToolInvocation`
  - `TestMixinNodeServiceHealthMonitoring`

- **Integration Tests**: `Test<ServiceModel><Capability>Integration`
  - `TestServiceEffectLifecycleIntegration`
  - `TestServiceComputeCachingIntegration`

- **Edge Cases**: `Test<ClassName>EdgeCases`
  - `TestMixinNodeServiceShutdownEdgeCases`

---

## 5. Core MixinNodeService Tests

### 5.1 Service Lifecycle Tests

**Test File:** `tests/unit/mixins/test_mixin_node_service.py`

#### 5.1.1 Initialization

| Test Case | Description | Assertions |
|-----------|-------------|------------|
| `test_initialization` | Verify mixin initializes all attributes | Check all state attributes exist with correct defaults |
| `test_initialization_with_kwargs` | Test initialization with kwargs propagation | Verify kwargs passed to super().__init__ |

#### 5.1.2 Service Start

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_start_service_mode_basic` | Start service with minimal setup | Service running flag set, task created | Critical |
| `test_start_service_mode_publishes_introspection` | Verify introspection published on start | Mock introspection emission | High |
| `test_start_service_mode_subscribes_to_events` | Verify event subscription | Mock event bus subscribe call | Critical |
| `test_start_service_mode_starts_health_monitoring` | Verify health task created | Health task exists and running | High |
| `test_start_service_mode_registers_signal_handlers` | Verify signal handlers registered | Mock signal.signal calls | Medium |
| `test_start_service_mode_already_running` | Test idempotency when already running | Warning logged, no duplicate tasks | Medium |
| `test_start_service_mode_failure_during_startup` | Test error handling during startup | Service stopped, exception propagated | High |
| `test_start_service_mode_without_event_bus` | Test startup without event bus | RuntimeError raised | High |

#### 5.1.3 Service Stop

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_stop_service_mode_basic` | Stop running service gracefully | Service stopped, flag cleared | Critical |
| `test_stop_service_mode_emits_shutdown_event` | Verify shutdown event emitted | Mock shutdown event emission | High |
| `test_stop_service_mode_cancels_health_task` | Verify health task cancelled | Health task cancelled properly | High |
| `test_stop_service_mode_waits_for_invocations` | Verify waits for active invocations | Wait function called with timeout | Critical |
| `test_stop_service_mode_runs_shutdown_callbacks` | Verify callbacks executed | Mock callbacks called | Medium |
| `test_stop_service_mode_cleanup_event_handlers` | Verify event handlers cleaned up | Cleanup method called | High |
| `test_stop_service_mode_idempotent` | Test stopping already stopped service | No errors, graceful return | Medium |
| `test_stop_service_mode_with_callback_failure` | Test callback exception handling | Error logged, shutdown continues | Medium |

#### 5.1.4 Service Event Loop

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_service_event_loop_runs_while_active` | Test loop continues while service running | Loop iterations occur | High |
| `test_service_event_loop_stops_on_shutdown` | Test loop exits on shutdown request | Loop terminates gracefully | Critical |
| `test_service_event_loop_handles_cancellation` | Test CancelledError handling | Log message emitted | Medium |
| `test_service_event_loop_propagates_exceptions` | Test exception propagation | Exception raised to caller | High |

### 5.2 Tool Invocation Handling Tests

#### 5.2.1 Basic Invocation Handling

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_handle_tool_invocation_basic` | Handle valid tool invocation | Response event emitted, success tracked | Critical |
| `test_handle_tool_invocation_tracks_active` | Verify invocation tracked during execution | Correlation ID in active set | High |
| `test_handle_tool_invocation_removes_from_active` | Verify removal from active after completion | Correlation ID removed from set | High |
| `test_handle_tool_invocation_increments_total` | Verify total invocations incremented | Counter incremented by 1 | High |
| `test_handle_tool_invocation_increments_successful` | Verify successful invocations tracked | Success counter incremented | High |
| `test_handle_tool_invocation_increments_failed` | Verify failed invocations tracked | Failure counter incremented | High |

#### 5.2.2 Target Validation

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_handle_tool_invocation_validates_target_by_id` | Test target validation by node ID | Invocation processed | High |
| `test_handle_tool_invocation_validates_target_by_name` | Test target validation by node name | Invocation processed | High |
| `test_handle_tool_invocation_validates_target_by_service_name` | Test target validation by service name | Invocation processed | High |
| `test_handle_tool_invocation_ignores_wrong_target` | Test ignoring wrong target | Warning logged, no processing | High |

#### 5.2.3 Input State Conversion

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_convert_event_to_input_state_with_class` | Convert event with input state class | Input state created with correct data | High |
| `test_convert_event_to_input_state_without_class` | Convert event without input state class | SimpleNamespace created with action + params | High |
| `test_convert_event_to_input_state_infers_class` | Test input state class inference | Correct class inferred from node attributes | Medium |
| `test_convert_event_to_input_state_with_complex_params` | Test complex parameter conversion | Nested objects handled correctly | Medium |

#### 5.2.4 Tool Execution

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_execute_tool_async_run_method` | Execute tool with async run() | Result returned from async method | Critical |
| `test_execute_tool_sync_run_method` | Execute tool with sync run() | Executor used, result returned | High |
| `test_execute_tool_no_run_method` | Test error when no run() method | RuntimeError raised | High |
| `test_execute_tool_with_execution_time` | Verify execution time tracking | execution_time_ms calculated correctly | Medium |

#### 5.2.5 Result Serialization

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_serialize_result_pydantic_model` | Serialize Pydantic model result | model_dump() called | High |
| `test_serialize_result_dict_object` | Serialize dict object | Dict returned as-is | High |
| `test_serialize_result_custom_object` | Serialize custom object with __dict__ | __dict__ returned | Medium |
| `test_serialize_result_primitive` | Serialize primitive type | Wrapped in {"result": value} | Medium |
| `test_serialize_result_none` | Serialize None result | {"result": None} | Low |

#### 5.2.6 Response Emission

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_emit_tool_response_success` | Emit success response | Event published via event bus | Critical |
| `test_emit_tool_response_error` | Emit error response | Error event published | Critical |
| `test_emit_tool_response_without_event_bus` | Test emission without event bus | Error logged | Medium |
| `test_emit_tool_response_with_bus_failure` | Test event bus publish failure | Error logged, exception handled | Medium |

#### 5.2.7 Error Handling

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_handle_tool_invocation_execution_error` | Test error during execution | Error response emitted, failure tracked | Critical |
| `test_handle_tool_invocation_conversion_error` | Test error during state conversion | Error response emitted | High |
| `test_handle_tool_invocation_serialization_error` | Test error during serialization | Error response emitted | High |
| `test_handle_tool_invocation_critical_error` | Test critical error handling | Service remains running | High |

### 5.3 Health Monitoring Tests

#### 5.3.1 Health Status Retrieval

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_get_service_health_basic` | Get health status | Dict with all required fields | Critical |
| `test_get_service_health_status_healthy` | Test healthy status | status == "healthy" | High |
| `test_get_service_health_status_unhealthy` | Test unhealthy status when shutdown requested | status == "unhealthy" | High |
| `test_get_service_health_uptime_calculation` | Test uptime calculation | uptime_seconds calculated correctly | Medium |
| `test_get_service_health_active_invocations` | Test active invocations count | Count matches _active_invocations | High |
| `test_get_service_health_success_rate` | Test success rate calculation | (successful / total) calculated correctly | High |
| `test_get_service_health_success_rate_zero_invocations` | Test success rate with zero invocations | 1.0 returned (100%) | Medium |
| `test_get_service_health_before_start` | Test health before service started | uptime_seconds == 0 | Low |

#### 5.3.2 Health Monitoring Loop

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_health_monitor_loop_runs_while_active` | Test loop runs during service lifetime | Health checks performed | High |
| `test_health_monitor_loop_logs_periodically` | Test periodic health logging | Log emitted every 100 invocations | Medium |
| `test_health_monitor_loop_sleep_interval` | Test sleep interval between checks | 30 second sleep called | Low |
| `test_health_monitor_loop_handles_cancellation` | Test cancellation handling | CancelledError caught, logged | Medium |
| `test_health_monitor_loop_handles_exceptions` | Test exception handling | Exception logged, not propagated | High |
| `test_health_monitor_loop_stops_on_shutdown` | Test loop exits on shutdown | Loop terminates | High |

### 5.4 Graceful Shutdown Tests

#### 5.4.1 Active Invocation Waiting

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_wait_for_active_invocations_none` | Wait with no active invocations | Returns immediately | Medium |
| `test_wait_for_active_invocations_completes_in_time` | Wait for invocations that complete | Returns when all complete | Critical |
| `test_wait_for_active_invocations_timeout` | Test timeout with active invocations | Warning logged, returns after timeout | High |
| `test_wait_for_active_invocations_partial_completion` | Test partial completion before timeout | Returns after timeout with remaining | Medium |
| `test_wait_for_active_invocations_custom_timeout` | Test custom timeout value | Respects provided timeout | Low |

#### 5.4.2 Shutdown Event Emission

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_emit_shutdown_event_success` | Emit shutdown event successfully | Event published with correct data | High |
| `test_emit_shutdown_event_without_event_bus` | Test emission without event bus | Graceful handling, no crash | Medium |
| `test_emit_shutdown_event_failure` | Test event bus publish failure | Error logged, exception caught | Medium |

#### 5.4.3 Shutdown Callbacks

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_add_shutdown_callback` | Add callback to list | Callback stored | Medium |
| `test_add_multiple_shutdown_callbacks` | Add multiple callbacks | All callbacks stored | Medium |
| `test_shutdown_callbacks_executed` | Test callbacks executed on shutdown | All callbacks called | High |
| `test_shutdown_callbacks_execution_order` | Test execution order | Callbacks called in registration order | Low |
| `test_shutdown_callback_exception_handling` | Test exception in callback | Error logged, other callbacks still run | High |

#### 5.4.4 Signal Handling

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_register_signal_handlers_success` | Register SIGTERM and SIGINT handlers | signal.signal called twice | Medium |
| `test_register_signal_handlers_failure` | Test handler registration failure | Warning logged | Low |
| `test_signal_handler_sets_shutdown_flag` | Test signal handler behavior | _shutdown_requested set to True | High |
| `test_signal_handler_logs_signal` | Test signal handler logging | Log message with signal number | Low |

### 5.5 Performance Tracking Tests

| Test Case | Description | Assertions | Priority |
|-----------|-------------|------------|----------|
| `test_performance_tracking_initialization` | Test initial counter values | All counters at 0 | Low |
| `test_performance_tracking_total_invocations` | Test total invocations counter | Increments on each invocation | High |
| `test_performance_tracking_successful_invocations` | Test success counter | Increments on successful completion | High |
| `test_performance_tracking_failed_invocations` | Test failure counter | Increments on failed invocation | High |
| `test_performance_tracking_start_time` | Test start time recording | Timestamp set on service start | Medium |
| `test_performance_tracking_success_rate_calculation` | Test success rate calculation | Correct percentage calculated | High |

---

## 6. Service Model Integration Tests

### 6.1 ModelServiceEffect Integration

**Test File:** `tests/unit/mixins/test_mixin_node_service_integration/test_service_effect_integration.py`

#### 6.1.1 Service Lifecycle with Effect Semantics

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_effect_service_start_with_transaction_manager` | Start service with transaction manager | NodeEffect + MixinNodeService | Critical |
| `test_effect_service_handles_tool_invocation_with_transaction` | Tool invocation within transaction | NodeEffect.run() + transaction context | Critical |
| `test_effect_service_health_includes_transaction_status` | Health check includes transaction health | MixinHealthCheck + NodeEffect | High |
| `test_effect_service_emits_events_during_execution` | Events emitted during effect execution | MixinEventBus + MixinNodeService | High |
| `test_effect_service_tracks_metrics_for_effects` | Metrics tracked for effect operations | MixinMetrics + MixinNodeService | High |

#### 6.1.2 EventBus Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_effect_service_publishes_tool_responses_via_event_bus` | Tool responses published | MixinEventBus + MixinNodeService | Critical |
| `test_effect_service_subscribes_to_tool_invocations_via_event_bus` | Subscribes to invocations | MixinEventBus + MixinNodeService | Critical |
| `test_effect_service_publishes_state_change_events` | State change events published | MixinEventBus + NodeEffect | High |

#### 6.1.3 HealthCheck Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_effect_service_health_aggregates_service_and_node_health` | Aggregate health from both mixins | MixinHealthCheck + MixinNodeService | High |
| `test_effect_service_health_includes_active_invocations` | Health includes service metrics | MixinHealthCheck + MixinNodeService | Medium |

#### 6.1.4 Metrics Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_effect_service_metrics_include_invocation_timing` | Metrics include tool timing | MixinMetrics + MixinNodeService | High |
| `test_effect_service_metrics_include_success_rates` | Metrics include success rates | MixinMetrics + MixinNodeService | High |

### 6.2 ModelServiceCompute Integration

**Test File:** `tests/unit/mixins/test_mixin_node_service_integration/test_service_compute_integration.py`

#### 6.2.1 Service Lifecycle with Compute Semantics

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_compute_service_start_with_cache` | Start service with caching enabled | NodeCompute + MixinCaching | Critical |
| `test_compute_service_handles_tool_invocation_with_caching` | Tool invocation with result caching | NodeCompute.run() + MixinCaching | Critical |
| `test_compute_service_health_includes_cache_status` | Health check includes cache health | MixinHealthCheck + MixinCaching | High |
| `test_compute_service_tracks_metrics_for_compute` | Metrics tracked for compute operations | MixinMetrics + MixinNodeService | High |

#### 6.2.2 Caching Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_compute_service_caches_tool_results` | Tool results cached automatically | MixinCaching + MixinNodeService | Critical |
| `test_compute_service_cache_hit_returns_cached_result` | Cache hit returns cached data | MixinCaching + MixinNodeService | Critical |
| `test_compute_service_cache_miss_executes_tool` | Cache miss executes tool | MixinCaching + MixinNodeService | High |
| `test_compute_service_cache_key_generation` | Cache keys generated correctly | MixinCaching + MixinNodeService | High |
| `test_compute_service_cache_ttl_respected` | Cache TTL honored | MixinCaching + MixinNodeService | Medium |

#### 6.2.3 HealthCheck Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_compute_service_health_includes_cache_health` | Health includes cache status | MixinHealthCheck + MixinCaching | High |
| `test_compute_service_health_includes_cache_hit_rate` | Health includes cache metrics | MixinHealthCheck + MixinCaching | Medium |

#### 6.2.4 Metrics Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_compute_service_metrics_include_cache_hit_rate` | Metrics include cache hit rate | MixinMetrics + MixinCaching | High |
| `test_compute_service_metrics_include_compute_timing` | Metrics include computation time | MixinMetrics + MixinNodeService | High |

### 6.3 ModelServiceReducer Integration

**Test File:** `tests/unit/mixins/test_mixin_node_service_integration/test_service_reducer_integration.py`

#### 6.3.1 Service Lifecycle with Reducer Semantics

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_reducer_service_start_with_aggregation_state` | Start service with aggregation state | NodeReducer + MixinNodeService | Critical |
| `test_reducer_service_handles_tool_invocation_with_aggregation` | Tool invocation performs aggregation | NodeReducer.run() + MixinNodeService | Critical |
| `test_reducer_service_health_includes_state_persistence` | Health check includes state health | MixinHealthCheck + NodeReducer | High |
| `test_reducer_service_tracks_metrics_for_aggregation` | Metrics tracked for aggregations | MixinMetrics + MixinNodeService | High |

#### 6.3.2 Caching Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_reducer_service_caches_aggregation_results` | Aggregation results cached | MixinCaching + NodeReducer | Critical |
| `test_reducer_service_cache_invalidation_on_state_change` | Cache invalidated when state changes | MixinCaching + NodeReducer | Critical |
| `test_reducer_service_cache_key_includes_aggregation_window` | Cache key includes time window | MixinCaching + NodeReducer | High |

#### 6.3.3 HealthCheck Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_reducer_service_health_includes_aggregation_state` | Health includes aggregation state | MixinHealthCheck + NodeReducer | High |
| `test_reducer_service_health_includes_cache_status` | Health includes cache status | MixinHealthCheck + MixinCaching | High |

#### 6.3.4 Metrics Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_reducer_service_metrics_include_aggregation_timing` | Metrics include aggregation time | MixinMetrics + NodeReducer | High |
| `test_reducer_service_metrics_include_state_persistence` | Metrics include persistence operations | MixinMetrics + NodeReducer | Medium |

### 6.4 ModelServiceOrchestrator Integration

**Test File:** `tests/unit/mixins/test_mixin_node_service_integration/test_service_orchestrator_integration.py`

#### 6.4.1 Service Lifecycle with Orchestrator Semantics

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_orchestrator_service_start_with_subnodes` | Start service with subnode management | NodeOrchestrator + MixinNodeService | Critical |
| `test_orchestrator_service_handles_tool_invocation_with_workflow` | Tool invocation executes workflow | NodeOrchestrator.run() + MixinNodeService | Critical |
| `test_orchestrator_service_health_includes_subnode_health` | Health check aggregates subnode health | MixinHealthCheck + NodeOrchestrator | High |
| `test_orchestrator_service_tracks_metrics_for_workflows` | Metrics tracked for workflows | MixinMetrics + MixinNodeService | High |

#### 6.4.2 EventBus Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_orchestrator_service_publishes_workflow_lifecycle_events` | Workflow events published | MixinEventBus + NodeOrchestrator | Critical |
| `test_orchestrator_service_coordinates_subnodes_via_events` | Subnode coordination via events | MixinEventBus + NodeOrchestrator | Critical |
| `test_orchestrator_service_tracks_correlation_ids` | Correlation IDs tracked across workflow | MixinEventBus + NodeOrchestrator | High |

#### 6.4.3 HealthCheck Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_orchestrator_service_health_aggregates_subnode_health` | Health aggregates from subnodes | MixinHealthCheck + NodeOrchestrator | High |
| `test_orchestrator_service_health_includes_workflow_status` | Health includes workflow status | MixinHealthCheck + NodeOrchestrator | Medium |

#### 6.4.4 Metrics Integration

| Test Case | Description | Integration Points | Priority |
|-----------|-------------|-------------------|----------|
| `test_orchestrator_service_metrics_include_workflow_timing` | Metrics include workflow time | MixinMetrics + NodeOrchestrator | High |
| `test_orchestrator_service_metrics_include_step_completion_rates` | Metrics include step completion | MixinMetrics + NodeOrchestrator | High |

---

## 7. Cross-Mixin Interaction Tests

**Test File:** `tests/unit/mixins/test_mixin_node_service_integration/test_mixin_interactions.py`

### 7.1 EventBus + NodeService Interactions

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_event_bus_subscription_during_service_start` | Verify subscription during start | Critical |
| `test_event_bus_publishes_tool_responses` | Verify response emission | Critical |
| `test_event_bus_publishes_shutdown_events` | Verify shutdown emission | High |
| `test_event_bus_unavailable_during_start` | Test start without event bus | High |
| `test_event_bus_unavailable_during_emission` | Test emission without event bus | Medium |

### 7.2 HealthCheck + NodeService Interactions

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_health_check_includes_service_health` | Health includes service metrics | High |
| `test_health_check_called_during_health_monitor_loop` | Health check called periodically | High |
| `test_health_check_with_active_invocations` | Health reflects active invocations | Medium |
| `test_health_check_with_shutdown_requested` | Health reflects shutdown state | Medium |

### 7.3 Metrics + NodeService Interactions

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_metrics_track_invocation_count` | Metrics include invocation count | High |
| `test_metrics_track_success_rate` | Metrics include success rate | High |
| `test_metrics_track_execution_time` | Metrics include timing data | High |
| `test_metrics_track_active_invocations` | Metrics include active count | Medium |

### 7.4 Caching + NodeService Interactions

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_caching_tool_results` | Tool results cached | Critical |
| `test_caching_cache_hit_tracking` | Cache hits tracked | High |
| `test_caching_cache_miss_tracking` | Cache misses tracked | High |
| `test_caching_health_includes_cache_status` | Health includes cache status | Medium |

---

## 8. MRO Correctness Tests

**Test File:** `tests/unit/mixins/test_mixin_node_service_integration/test_mro_correctness.py`

### 8.1 MRO Validation

| Test Case | Description | Verification | Priority |
|-----------|-------------|--------------|----------|
| `test_service_effect_mro` | Validate ModelServiceEffect MRO | MRO matches expected order | High |
| `test_service_compute_mro` | Validate ModelServiceCompute MRO | MRO matches expected order | High |
| `test_service_reducer_mro` | Validate ModelServiceReducer MRO | MRO matches expected order | High |
| `test_service_orchestrator_mro` | Validate ModelServiceOrchestrator MRO | MRO matches expected order | High |

### 8.2 Method Resolution Tests

| Test Case | Description | Verification | Priority |
|-----------|-------------|--------------|----------|
| `test_service_effect_init_calls_all_mixins` | Verify all mixin __init__ called | All mixins initialized | High |
| `test_service_compute_init_calls_all_mixins` | Verify all mixin __init__ called | All mixins initialized | High |
| `test_service_reducer_init_calls_all_mixins` | Verify all mixin __init__ called | All mixins initialized | High |
| `test_service_orchestrator_init_calls_all_mixins` | Verify all mixin __init__ called | All mixins initialized | High |

### 8.3 Method Override Tests

| Test Case | Description | Verification | Priority |
|-----------|-------------|--------------|----------|
| `test_no_diamond_problem_conflicts` | Verify no MRO diamond issues | No conflicting methods | High |
| `test_mixin_methods_accessible` | Verify all mixin methods accessible | Methods callable | Medium |
| `test_super_calls_propagate_correctly` | Verify super() propagation | All __init__ called | High |

---

## 9. Edge Cases and Error Scenarios

### 9.1 Concurrency Edge Cases

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_concurrent_tool_invocations` | Handle multiple simultaneous invocations | Critical |
| `test_shutdown_during_active_invocations` | Shutdown with pending invocations | Critical |
| `test_start_called_multiple_times_concurrently` | Concurrent start calls | Medium |
| `test_stop_called_during_start` | Stop called before start completes | Medium |

### 9.2 Resource Cleanup Edge Cases

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_cleanup_on_exception_during_start` | Resources cleaned up on start failure | High |
| `test_cleanup_on_exception_during_stop` | Resources cleaned up on stop failure | High |
| `test_cleanup_with_orphaned_tasks` | Orphaned tasks handled | Medium |
| `test_cleanup_with_stuck_invocations` | Stuck invocations timed out | High |

### 9.3 State Corruption Edge Cases

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_active_invocations_set_consistency` | Active invocations set remains consistent | High |
| `test_counters_dont_overflow` | Performance counters handled correctly | Low |
| `test_state_after_repeated_start_stop_cycles` | State correct after cycles | Medium |

### 9.4 Event Bus Failure Edge Cases

| Test Case | Description | Priority |
|-----------|-------------|----------|
| `test_event_bus_disconnected_during_operation` | Handle event bus disconnection | High |
| `test_event_bus_publish_failure_during_invocation` | Handle publish failure | High |
| `test_event_bus_subscribe_failure` | Handle subscription failure | High |

---

## 10. Test Fixtures

**Test File:** `tests/unit/mixins/test_mixin_node_service_integration/fixtures.py`

### 10.1 Core Fixtures

```python
@pytest.fixture
def mock_container():
    """Mock ModelONEXContainer for dependency injection."""

@pytest.fixture
def mock_event_bus():
    """Mock event bus for publish/subscribe."""

@pytest.fixture
def mock_node_effect():
    """Mock NodeEffect with run() method."""

@pytest.fixture
def mock_node_compute():
    """Mock NodeCompute with run() method."""

@pytest.fixture
def mock_node_reducer():
    """Mock NodeReducer with run() method."""

@pytest.fixture
def mock_node_orchestrator():
    """Mock NodeOrchestrator with run() method."""
```

### 10.2 Event Fixtures

```python
@pytest.fixture
def tool_invocation_event():
    """Create ModelToolInvocationEvent for testing."""

@pytest.fixture
def tool_response_event_success():
    """Create success ModelToolResponseEvent."""

@pytest.fixture
def tool_response_event_error():
    """Create error ModelToolResponseEvent."""

@pytest.fixture
def node_shutdown_event():
    """Create ModelNodeShutdownEvent."""
```

### 10.3 Service Fixtures

```python
@pytest.fixture
def service_effect():
    """Create ModelServiceEffect instance for testing."""

@pytest.fixture
def service_compute():
    """Create ModelServiceCompute instance for testing."""

@pytest.fixture
def service_reducer():
    """Create ModelServiceReducer instance for testing."""

@pytest.fixture
def service_orchestrator():
    """Create ModelServiceOrchestrator instance for testing."""
```

### 10.4 State Fixtures

```python
@pytest.fixture
def mock_input_state():
    """Create mock input state for tool execution."""

@pytest.fixture
def mock_execution_result():
    """Create mock execution result."""

@pytest.fixture
def mock_health_status():
    """Create mock health status."""
```

### 10.5 Utility Fixtures

```python
@pytest.fixture
def correlation_id():
    """Generate UUID for correlation tracking."""

@pytest.fixture
def node_id():
    """Generate UUID for node ID."""

@pytest.fixture
def async_sleep_mock(monkeypatch):
    """Mock asyncio.sleep to speed up tests."""

@pytest.fixture
def time_mock(monkeypatch):
    """Mock time.time() for deterministic timing."""
```

---

## 11. Performance and Load Testing

### 11.1 Performance Test Cases

| Test Case | Description | Target | Priority |
|-----------|-------------|--------|----------|
| `test_invocation_throughput` | Test invocations per second | >100 invocations/sec | Medium |
| `test_concurrent_invocation_handling` | Test concurrent invocations | 10+ concurrent | Medium |
| `test_service_startup_time` | Test service startup latency | <100ms | Low |
| `test_service_shutdown_time` | Test graceful shutdown time | <5s | Medium |
| `test_memory_usage_during_operation` | Test memory footprint | No leaks | High |

### 11.2 Stress Test Cases

| Test Case | Description | Target | Priority |
|-----------|-------------|--------|----------|
| `test_sustained_high_load` | Test sustained high invocation rate | 1000+ invocations | Low |
| `test_many_active_invocations` | Test many concurrent invocations | 100+ concurrent | Low |
| `test_repeated_start_stop_cycles` | Test service lifecycle stability | 100+ cycles | Medium |

---

## 12. Test Execution Strategy

### 12.1 Test Phases

**Phase 1: Core Unit Tests** (Priority: Critical + High)
- Service lifecycle tests
- Tool invocation handling tests
- Health monitoring tests
- Graceful shutdown tests

**Phase 2: Integration Tests** (Priority: Critical + High)
- ModelServiceEffect integration
- ModelServiceCompute integration
- ModelServiceReducer integration
- ModelServiceOrchestrator integration

**Phase 3: Edge Cases** (Priority: High + Medium)
- Concurrency edge cases
- Resource cleanup edge cases
- Event bus failure cases

**Phase 4: MRO and Performance** (Priority: Medium + Low)
- MRO correctness tests
- Performance tests
- Stress tests

### 12.2 CI/CD Integration

**Pre-commit Hooks:**
- Run Phase 1 tests (critical only)
- Expected time: <30s

**PR Validation:**
- Run Phase 1 + Phase 2 tests
- Expected time: <2 minutes

**Main Branch:**
- Run all tests (Phase 1-4)
- Expected time: <5 minutes

**Nightly:**
- Run all tests including stress tests
- Generate coverage reports
- Performance regression analysis

### 12.3 Coverage Requirements

| Test Category | Line Coverage Target | Branch Coverage Target |
|--------------|---------------------|------------------------|
| MixinNodeService core | 95%+ | 100% |
| Service models integration | 90%+ | 95% |
| Edge cases | 85%+ | 90% |
| Performance tests | N/A | N/A |

---

## 13. Test Implementation Guidelines

### 13.1 Testing Principles

1. **Isolation**: Each test must be independent
2. **Fast Execution**: Target <100ms per test
3. **Clear Assertions**: One logical assertion per test
4. **Descriptive Names**: Test names describe behavior
5. **Mock External Dependencies**: No real databases, networks, or files
6. **Async Testing**: Use `pytest.mark.asyncio` for async tests
7. **Fixture Reuse**: Maximize fixture reuse for consistency

### 13.2 Mocking Guidelines

**Always Mock:**
- Event bus (`MixinEventBus`)
- Container dependencies (`ModelONEXContainer`)
- External services (databases, APIs, caches)
- Time and sleep functions for deterministic tests
- Signal handlers

**Never Mock:**
- MixinNodeService internal methods (test the real thing)
- Service model MRO (test actual inheritance)
- Pydantic model validation

### 13.3 Assertion Guidelines

**Good Assertions:**
```python
assert service._service_running is True
assert len(service._active_invocations) == 1
assert health["status"] == "healthy"
assert mock_event_bus.publish.call_count == 1
```

**Avoid:**
```python
assert service  # Too vague
assert True  # Meaningless
```

### 13.4 Test Documentation

Each test should include:
- Docstring describing the test scenario
- Comments for complex setup
- Clear assertion messages

Example:
```python
def test_handle_tool_invocation_basic(mock_event_bus, tool_invocation_event):
    """
    Test basic tool invocation handling.

    Scenario:
    - Service is running
    - Tool invocation event received
    - Tool executes successfully
    - Response event emitted

    Expected:
    - Invocation tracked in active set
    - Tool executed via run()
    - Success response emitted
    - Metrics updated
    """
    # Test implementation
```

---

## 14. Success Criteria

### 14.1 Test Completion Criteria

- [ ] All 150+ test cases implemented
- [ ] All tests passing consistently
- [ ] 95%+ line coverage for MixinNodeService
- [ ] 90%+ line coverage for service models
- [ ] 100% branch coverage for critical paths
- [ ] Zero flaky tests (100% pass rate over 10 runs)
- [ ] All priority "Critical" and "High" tests completed

### 14.2 Quality Gates

- [ ] All tests execute in <5 minutes total
- [ ] No test timeouts
- [ ] No resource leaks detected
- [ ] All mocks properly cleaned up
- [ ] Documentation complete for all fixtures
- [ ] MRO correctness validated for all models

### 14.3 Documentation Deliverables

- [ ] Test plan document (this document)
- [ ] Test fixture documentation
- [ ] Test execution guide
- [ ] Coverage report with analysis
- [ ] Known limitations and edge cases document

---

## 15. Open Questions and Considerations

### 15.1 Technical Questions

1. **Transaction Management**: How should transactions be mocked for ModelServiceEffect tests?
2. **Cache Backend**: Should we mock the cache backend or use an in-memory implementation?
3. **Signal Handling**: How to test signal handlers in a CI environment?
4. **Event Bus**: Should we test with a real in-memory event bus or mock it?

### 15.2 Test Coverage Gaps

1. **Integration Testing**: Full end-to-end integration tests with real services
2. **Load Testing**: Production-scale load tests
3. **Security Testing**: Input validation, injection attacks
4. **Compliance Testing**: ONEX standards compliance validation

### 15.3 Future Enhancements

1. **Property-Based Testing**: Use `hypothesis` for property-based tests
2. **Mutation Testing**: Use `mutmut` to verify test effectiveness
3. **Benchmark Testing**: Performance regression detection
4. **Chaos Engineering**: Fault injection and resilience testing

---

## 16. Appendix

### 16.1 Related Documentation

- `src/omnibase_core/mixins/mixin_node_service.py`
- `src/omnibase_core/models/nodes/services/`
- `tests/unit/mixins/test_mixin_health_check.py` (reference)

### 16.2 Glossary

- **MRO**: Method Resolution Order - Python's order for resolving method calls in multiple inheritance
- **MCP**: Model Context Protocol - Tool invocation protocol
- **TOOL_INVOCATION**: Event type for tool execution requests
- **TOOL_RESPONSE**: Event type for tool execution results
- **Correlation ID**: UUID tracking request/response pairs
- **Service Mode**: Persistent long-running node operation mode

### 16.3 Test Estimation

| Test Category | Test Count | Estimated Time |
|--------------|-----------|----------------|
| Core MixinNodeService | 60 tests | 3 days |
| ModelServiceEffect | 20 tests | 1 day |
| ModelServiceCompute | 20 tests | 1 day |
| ModelServiceReducer | 20 tests | 1 day |
| ModelServiceOrchestrator | 20 tests | 1 day |
| Cross-mixin interactions | 20 tests | 1 day |
| MRO correctness | 10 tests | 0.5 day |
| Edge cases | 20 tests | 1 day |
| **Total** | **170 tests** | **9.5 days** |

---

## 17. Approval and Sign-off

**Test Plan Author:** Claude Code
**Date:** 2025-10-16
**Status:** Planning Phase - Awaiting Review

**Next Steps:**
1. Review test plan with team
2. Prioritize test cases
3. Create test implementation tickets
4. Begin Phase 1 implementation
5. Iterate based on findings

---

*End of Test Plan*
