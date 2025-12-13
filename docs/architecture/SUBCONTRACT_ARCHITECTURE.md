# ONEX Subcontract Package Architecture

## Overview

The ONEX Subcontract Package provides specialized contract models for complex operations within the Four-Node Architecture. Subcontracts enable sophisticated processing patterns including finite state machines, data aggregation, routing, workflow coordination, introspection, discovery, event handling, lifecycle management, observability, and tool execution while maintaining ONEX compliance and correlation tracking.

### Complete Subcontract Inventory

The package includes **25 specialized subcontracts** organized by functional domain:

**Core Processing Subcontracts:**
1. **ModelAggregationSubcontract** - Data consolidation and statistical operations
2. **ModelFSMSubcontract** - Finite state machine workflow processing
3. **ModelRoutingSubcontract** - Request routing and load balancing
4. **ModelCachingSubcontract** - Intelligent caching strategies

**Event-Driven Subcontracts:**
5. **ModelEventTypeSubcontract** - Event processing and routing
6. **ModelEventBusSubcontract** - Event bus configuration and management
7. **ModelEventHandlingSubcontract** ⭐ - Event subscription, filtering, and handler lifecycle

**Infrastructure Subcontracts:**
8. **ModelStateManagementSubcontract** - State persistence and recovery
9. **ModelConfigurationSubcontract** - Dynamic configuration management
10. **ModelCircuitBreakerSubcontract** - Circuit breaker patterns
11. **ModelHealthCheckSubcontract** - Health monitoring configuration
12. **ModelRetrySubcontract** - Retry logic and resilience

**Security and Validation:**
13. **ModelSecuritySubcontract** - Security policies and authentication
14. **ModelValidationSubcontract** - Input/output validation rules
15. **ModelSerializationSubcontract** - Serialization format control

**Observability and Discovery:**
16. **ModelLoggingSubcontract** - Structured logging configuration
17. **ModelMetricsSubcontract** - Performance metrics collection
18. **ModelIntrospectionSubcontract** ⭐ - Node metadata exposure and schema export
19. **ModelDiscoverySubcontract** ⭐ - Service discovery and capability advertisement
20. **ModelObservabilitySubcontract** ⭐ - Unified observability (logging, metrics, tracing)

**Workflow and Orchestration:**
21. **ModelWorkflowCoordinationSubcontract** - Multi-step workflow coordination
22. **ModelLifecycleSubcontract** ⭐ - Node startup/shutdown and lifecycle hooks
23. **ModelToolExecutionSubcontract** ⭐ - Tool execution and resource management

**Specialized Patterns:**
24. **ModelLoadBalancingSubcontract** - Advanced load balancing strategies
25. **ModelRequestTransformationSubcontract** - Request/response transformation

⭐ = **New in v1.0.0** - Recently added with comprehensive validation and ONEX compliance

## Architectural Principles

### Subcontract Design Philosophy

1. **Specialized Functionality**: Each subcontract addresses specific operational patterns
2. **ONEX Integration**: Seamless integration with Four-Node Architecture
3. **Correlation Tracking**: Complete request traceability across subcontract operations
4. **Performance Optimization**: Optimized for high-throughput and low-latency scenarios
5. **Fault Tolerance**: Built-in error handling and recovery mechanisms

### Package Structure

```
src/omnibase_core/models/contracts/subcontracts/
├── __init__.py                                 # Package exports and registry
├── model_aggregation_subcontract.py          # Data aggregation operations
├── model_fsm_subcontract.py                  # Finite state machine processing
├── model_routing_subcontract.py              # Request routing and load balancing
├── model_caching_subcontract.py              # Caching strategies and management
├── model_configuration_subcontract.py        # Dynamic configuration management
├── model_event_type_subcontract.py           # Event processing and routing
├── model_state_management_subcontract.py     # State persistence and recovery
├── model_circuit_breaker.py                  # Circuit breaker patterns
├── model_load_balancing.py                   # Load balancing configurations
├── model_request_transformation.py           # Request/response transformation
├── model_data_grouping.py                    # Data grouping strategies
├── model_aggregation_function.py             # Aggregation operation definitions
├── model_aggregation_performance.py          # Performance optimization settings
├── model_fsm_state_definition.py             # FSM state specifications
├── model_fsm_state_transition.py             # FSM transition definitions
├── model_fsm_transition_condition.py         # FSM condition evaluations
├── model_fsm_transition_action.py            # FSM action executions
├── model_fsm_operation.py                    # FSM operation definitions
├── model_route_definition.py                 # Route specification models
└── model_routing_metrics.py                  # Routing performance metrics
```

## Core Subcontract Types

### 1. Aggregation Subcontract

**Primary Purpose**: Data consolidation and statistical operations

**File**: `model_aggregation_subcontract.py`

**Key Features**:
- Multiple aggregation functions (sum, average, count, custom)
- Data grouping and partitioning strategies
- Performance optimization with parallel processing
- Circuit breaker integration for fault tolerance
- Streaming and batch processing support

**Usage Pattern**:

```
from omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract import ModelAggregationSubcontract
from omnibase_core.models.contracts.subcontracts.model_aggregation_function import ModelAggregationFunction
from omnibase_core.models.contracts.subcontracts.model_data_grouping import ModelDataGrouping
from omnibase_core.models.contracts.subcontracts.model_aggregation_performance import ModelAggregationPerformance
from uuid import uuid4

# Financial metrics aggregation
financial_aggregation = ModelAggregationSubcontract(
    aggregation_functions=[
        ModelAggregationFunction(
            function_type="sum",
            field_name="revenue",
            output_name="total_revenue",
            filter_conditions={"status": "completed"},
            correlation_id=uuid4()
        ),
        ModelAggregationFunction(
            function_type="avg",
            field_name="transaction_value",
            output_name="average_transaction",
            precision=2,
            correlation_id=uuid4()
        ),
        ModelAggregationFunction(
            function_type="count_distinct",
            field_name="customer_id",
            output_name="unique_customers",
            correlation_id=uuid4()
        )
    ],
    data_grouping=ModelDataGrouping(
        group_by_fields=["region", "product_category"],
        sort_order="desc",
        sort_field="total_revenue",
        partition_strategy="hash",
        correlation_id=uuid4()
    ),
    performance_config=ModelAggregationPerformance(
        batch_size=5000,
        parallel_workers=8,
        memory_limit_mb=1024,
        enable_caching=True,
        cache_ttl_seconds=300,
        correlation_id=uuid4()
    ),
    correlation_id=uuid4()
)

# Real-time analytics aggregation
realtime_aggregation = ModelAggregationSubcontract(
    aggregation_functions=[
        ModelAggregationFunction(
            function_type="sliding_window_avg",
            field_name="response_time",
            output_name="avg_response_time_5min",
            window_size_seconds=300,
            correlation_id=uuid4()
        ),
        ModelAggregationFunction(
            function_type="percentile",
            field_name="response_time",
            output_name="p95_response_time",
            percentile=95,
            correlation_id=uuid4()
        )
    ],
    data_grouping=ModelDataGrouping(
        group_by_fields=["service_name", "environment"],
        time_window_seconds=300,
        correlation_id=uuid4()
    ),
    performance_config=ModelAggregationPerformance(
        batch_size=1000,
        parallel_workers=4,
        memory_limit_mb=512,
        streaming_mode=True,
        correlation_id=uuid4()
    ),
    correlation_id=uuid4()
)
```

**Integration with REDUCER Nodes**:

```
from omnibase_core.models.service.model_service_reducer import ModelServiceReducer
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

class AggregationReducerService(ModelServiceReducer):
    """REDUCER node with aggregation subcontract support."""

    async def execute_reduction(self, contract: ModelContractReducer) -> ModelReducerOutput:
        """Execute reduction with aggregation subcontract."""
        # Extract aggregation subcontract
        aggregation_subcontract = contract.get_subcontract(ModelAggregationSubcontract)

        if aggregation_subcontract:
            # Execute aggregation operations
            aggregation_result = await self._execute_aggregation_subcontract(
                aggregation_subcontract
            )

            # Integrate results into reducer output
            return ModelReducerOutput(
                correlation_id=contract.correlation_id,
                aggregated_data=aggregation_result.data,
                subcontract_results={
                    "aggregation": aggregation_result.metadata
                }
            )

        # Fallback to standard reduction
        return await super().execute_reduction(contract)
```

### 2. Finite State Machine (FSM) Subcontract

**Primary Purpose**: State-based workflow processing

**File**: `model_fsm_subcontract.py`

**Key Features**:
- Complete state machine definition with transitions
- Conditional logic and automated actions
- Timeout handling and recovery
- State persistence and restoration
- Parallel state processing support

**Usage Pattern**:

```
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import ModelFSMSubcontract
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import ModelFSMStateDefinition
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import ModelFSMStateTransition
from omnibase_core.models.contracts.subcontracts.model_fsm_transition_condition import ModelFSMTransitionCondition
from omnibase_core.models.contracts.subcontracts.model_fsm_transition_action import ModelFSMTransitionAction

# Order processing FSM
order_processing_fsm = ModelFSMSubcontract(
    state_definitions={
        "order_received": ModelFSMStateDefinition(
            name="order_received",
            description="Initial order received state",
            allowed_operations=["validate_order", "check_inventory"],
            timeout_seconds=30,
            entry_actions=["log_order_received"],
            exit_actions=["update_status"],
            metadata={"requires_validation": True},
            correlation_id=uuid4()
        ),
        "validation_in_progress": ModelFSMStateDefinition(
            name="validation_in_progress",
            description="Order validation processing",
            allowed_operations=["continue_validation", "request_additional_info"],
            timeout_seconds=120,
            entry_actions=["start_validation_timer"],
            exit_actions=["log_validation_result"],
            correlation_id=uuid4()
        ),
        "order_approved": ModelFSMStateDefinition(
            name="order_approved",
            description="Order successfully validated and approved",
            allowed_operations=["process_payment", "allocate_inventory"],
            timeout_seconds=300,
            entry_actions=["send_approval_notification"],
            correlation_id=uuid4()
        ),
        "order_rejected": ModelFSMStateDefinition(
            name="order_rejected",
            description="Order validation failed",
            allowed_operations=["send_rejection_notice", "cleanup_resources"],
            metadata={"terminal": True},
            correlation_id=uuid4()
        ),
        "order_completed": ModelFSMStateDefinition(
            name="order_completed",
            description="Order successfully processed",
            allowed_operations=["generate_confirmation", "update_analytics"],
            metadata={"terminal": True, "success": True},
            correlation_id=uuid4()
        )
    },
    transitions=[
        ModelFSMStateTransition(
            from_state="order_received",
            to_state="validation_in_progress",
            condition=ModelFSMTransitionCondition(
                condition_type="field_not_empty",
                field_name="customer_info",
                correlation_id=uuid4()
            ),
            action=ModelFSMTransitionAction(
                action_type="log_transition",
                parameters={"message": "Starting order validation"},
                correlation_id=uuid4()
            ),
            correlation_id=uuid4()
        ),
        ModelFSMStateTransition(
            from_state="validation_in_progress",
            to_state="order_approved",
            condition=ModelFSMTransitionCondition(
                condition_type="all_validations_passed",
                parameters={"required_validations": ["customer", "payment", "inventory"]},
                correlation_id=uuid4()
            ),
            action=ModelFSMTransitionAction(
                action_type="send_notification",
                parameters={"type": "order_approved", "recipient": "customer"},
                correlation_id=uuid4()
            ),
            correlation_id=uuid4()
        ),
        ModelFSMStateTransition(
            from_state="validation_in_progress",
            to_state="order_rejected",
            condition=ModelFSMTransitionCondition(
                condition_type="validation_failed",
                parameters={"max_retry_attempts": 3},
                correlation_id=uuid4()
            ),
            action=ModelFSMTransitionAction(
                action_type="log_rejection_reason",
                parameters={"include_details": True},
                correlation_id=uuid4()
            ),
            correlation_id=uuid4()
        )
    ],
    initial_state="order_received",
    final_states=["order_completed", "order_rejected"],
    timeout_config={
        "global_timeout": 1800,  # 30 minutes
        "state_timeout": 300,    # 5 minutes per state
        "transition_timeout": 60 # 1 minute per transition
    },
    correlation_id=uuid4()
)

# Data pipeline FSM with parallel processing
pipeline_fsm = ModelFSMSubcontract(
    state_definitions={
        "data_ingestion": ModelFSMStateDefinition(
            name="data_ingestion",
            description="Parallel data ingestion from multiple sources",
            allowed_operations=["ingest_api", "ingest_file", "ingest_stream"],
            parallel_execution=True,
            max_parallel_operations=5,
            correlation_id=uuid4()
        ),
        "data_transformation": ModelFSMStateDefinition(
            name="data_transformation",
            description="Data cleaning and transformation",
            allowed_operations=["clean_data", "transform_schema", "validate_quality"],
            timeout_seconds=600,
            correlation_id=uuid4()
        ),
        "data_storage": ModelFSMStateDefinition(
            name="data_storage",
            description="Store processed data with backup",
            allowed_operations=["store_primary", "create_backup", "update_index"],
            parallel_execution=True,
            correlation_id=uuid4()
        ),
        "pipeline_complete": ModelFSMStateDefinition(
            name="pipeline_complete",
            description="Pipeline successfully completed",
            metadata={"terminal": True, "success": True},
            correlation_id=uuid4()
        )
    },
    transitions=[
        # Define transitions with proper correlation tracking
    ],
    initial_state="data_ingestion",
    final_states=["pipeline_complete"],
    correlation_id=uuid4()
)
```

**Integration with ORCHESTRATOR Nodes**:

```
from omnibase_core.models.service.model_service_orchestrator import ModelServiceOrchestrator

class FSMOrchestratorService(ModelServiceOrchestrator):
    """ORCHESTRATOR node with FSM subcontract support."""

    async def execute_orchestration(self, contract: ModelContractOrchestrator):
        """Execute orchestration with FSM subcontract."""
        fsm_subcontract = contract.get_subcontract(ModelFSMSubcontract)

        if fsm_subcontract:
            # Initialize FSM execution engine
            fsm_engine = FSMExecutionEngine(fsm_subcontract)

            # Execute FSM workflow
            fsm_result = await fsm_engine.execute()

            return ModelOrchestratorOutput(
                correlation_id=contract.correlation_id,
                orchestration_result=fsm_result,
                subcontract_results={
                    "fsm": {
                        "final_state": fsm_result.final_state,
                        "transitions_executed": fsm_result.transition_count,
                        "execution_time": fsm_result.total_time
                    }
                }
            )

        return await super().execute_orchestration(contract)
```

### 3. Routing Subcontract

**Primary Purpose**: Request routing and load balancing

**File**: `model_routing_subcontract.py`

**Key Features**:
- Multiple routing strategies (round-robin, weighted, hash-based)
- Load balancing with health checks
- Request transformation and filtering
- Circuit breaker integration
- Performance metrics collection

**Usage Pattern**:

```
from omnibase_core.models.contracts.subcontracts.model_routing_subcontract import ModelRoutingSubcontract
from omnibase_core.models.contracts.subcontracts.model_route_definition import ModelRouteDefinition
from omnibase_core.models.contracts.subcontracts.model_load_balancing import ModelLoadBalancing
from omnibase_core.models.contracts.subcontracts.model_request_transformation import ModelRequestTransformation

# API Gateway routing configuration
api_gateway_routing = ModelRoutingSubcontract(
    route_definitions=[
        ModelRouteDefinition(
            route_id="user_service_v2",
            path_pattern="/api/v2/users/*",
            target_services=["user-service-1", "user-service-2", "user-service-3"],
            routing_strategy="weighted",
            weights={"user-service-1": 50, "user-service-2": 30, "user-service-3": 20},
            health_check_path="/health",
            timeout_seconds=30,
            correlation_id=uuid4()
        ),
        ModelRouteDefinition(
            route_id="payment_service",
            path_pattern="/api/payments/*",
            target_services=["payment-service-1", "payment-service-2"],
            routing_strategy="hash_based",
            hash_field="customer_id",
            health_check_path="/health",
            timeout_seconds=60,
            correlation_id=uuid4()
        ),
        ModelRouteDefinition(
            route_id="analytics_service",
            path_pattern="/api/analytics/*",
            target_services=["analytics-service"],
            routing_strategy="direct",
            health_check_path="/status",
            timeout_seconds=120,
            correlation_id=uuid4()
        )
    ],
    load_balancing=ModelLoadBalancing(
        strategy="least_connections",
        health_check_interval_seconds=30,
        max_retry_attempts=3,
        circuit_breaker_config={
            "failure_threshold": 5,
            "recovery_timeout": 60,
            "half_open_max_calls": 3
        },
        correlation_id=uuid4()
    ),
    request_transformation=ModelRequestTransformation(
        add_headers={"X-Gateway-Version": "2.0", "X-Request-ID": "{{correlation_id}}"},
        remove_headers=["Internal-Auth-Token"],
        path_rewrite_rules=[
            {"pattern": "^/api/v2/users/", "replacement": "/users/"},
            {"pattern": "^/api/payments/", "replacement": "/payments/v1/"}
        ],
        correlation_id=uuid4()
    ),
    correlation_id=uuid4()
)

# Microservice mesh routing
microservice_routing = ModelRoutingSubcontract(
    route_definitions=[
        ModelRouteDefinition(
            route_id="order_processing_chain",
            path_pattern="internal://order-processing/*",
            target_services=["inventory-service", "payment-service", "shipping-service"],
            routing_strategy="sequential",
            dependency_order=["inventory-service", "payment-service", "shipping-service"],
            correlation_id=uuid4()
        ),
        ModelRouteDefinition(
            route_id="data_pipeline",
            path_pattern="internal://data-pipeline/*",
            target_services=["ingestion-service", "transformation-service", "storage-service"],
            routing_strategy="pipeline",
            buffer_sizes={"ingestion": 1000, "transformation": 500, "storage": 200},
            correlation_id=uuid4()
        )
    ],
    load_balancing=ModelLoadBalancing(
        strategy="adaptive",
        performance_metrics=["response_time", "error_rate", "cpu_usage"],
        adaptation_interval_seconds=60,
        correlation_id=uuid4()
    ),
    correlation_id=uuid4()
)
```

**Integration with EFFECT Nodes**:

```
from omnibase_core.infrastructure.infrastructure_bases import ModelServiceEffect

class RoutingEffectService(ModelServiceEffect):
    """EFFECT node with routing subcontract support."""

    async def execute_effect(self, contract: ModelContractEffect):
        """Execute effect with routing subcontract."""
        routing_subcontract = contract.get_subcontract(ModelRoutingSubcontract)

        if routing_subcontract:
            # Initialize routing engine
            routing_engine = RoutingEngine(routing_subcontract)

            # Route request based on configuration
            route_result = await routing_engine.route_request(
                request_path=contract.request_path,
                request_data=contract.request_data,
                correlation_id=contract.correlation_id
            )

            # Execute routed request
            response = await self._execute_routed_request(route_result)

            return ModelEffectOutput(
                correlation_id=contract.correlation_id,
                operation_result=response,
                routing_metadata={
                    "selected_route": route_result.route_id,
                    "target_service": route_result.target_service,
                    "routing_time": route_result.routing_time,
                    "transformations_applied": route_result.transformations
                }
            )

        return await super().execute_effect(contract)
```

### 4. Caching Subcontract

**Primary Purpose**: Intelligent caching strategies and cache management

**File**: `model_caching_subcontract.py`

**Key Features**:
- Multiple cache levels (L1, L2, distributed)
- TTL and invalidation strategies
- Cache warming and preloading
- Performance optimization
- Cache coherence protocols

**Usage Pattern**:

```
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import ModelCachingSubcontract

# Multi-tier caching strategy
caching_strategy = ModelCachingSubcontract(
    cache_levels=[
        {
            "level": "L1",
            "type": "memory",
            "size_mb": 256,
            "ttl_seconds": 300,
            "eviction_policy": "LRU"
        },
        {
            "level": "L2",
            "type": "redis",
            "connection_string": "redis://cache-cluster:6379",
            "ttl_seconds": 3600,
            "key_prefix": "onex_cache"
        },
        {
            "level": "L3",
            "type": "database",
            "connection_string": "postgresql://cache-db:5432/cache",
            "ttl_seconds": 86400,
            "table_name": "cache_entries"
        }
    ],
    invalidation_strategy={
        "type": "event_driven",
        "events": ["data_updated", "configuration_changed"],
        "pattern_matching": True,
        "cascade_levels": ["L1", "L2"]
    },
    warming_strategy={
        "enabled": True,
        "preload_patterns": ["/api/*/popular", "/config/*"],
        "warming_schedule": "0 6 * * *",  # Daily at 6 AM
        "parallel_workers": 4
    },
    correlation_id=uuid4()
)
```

## Advanced Subcontract Patterns

### 1. Composite Subcontract Pattern

Combining multiple subcontracts for complex operations:

```
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

# Complex data processing with multiple subcontracts
complex_reducer_contract = ModelContractReducer(
    correlation_id=uuid4(),
    subcontracts=[
        # First: Cache frequently accessed data
        ModelCachingSubcontract(
            cache_levels=[{"level": "L1", "type": "memory", "size_mb": 512}],
            correlation_id=uuid4()
        ),
        # Second: Aggregate data with parallel processing
        ModelAggregationSubcontract(
            aggregation_functions=[
                ModelAggregationFunction(
                    function_type="sum",
                    field_name="revenue",
                    output_name="total_revenue",
                    correlation_id=uuid4()
                )
            ],
            performance_config=ModelAggregationPerformance(
                parallel_workers=8,
                memory_limit_mb=1024,
                correlation_id=uuid4()
            ),
            correlation_id=uuid4()
        ),
        # Third: Manage state transitions
        ModelFSMSubcontract(
            state_definitions={"processing": ModelFSMStateDefinition(
                name="processing",
                allowed_operations=["aggregate", "cache", "validate"],
                correlation_id=uuid4()
            )},
            initial_state="processing",
            final_states=["completed"],
            correlation_id=uuid4()
        )
    ],
    execution_order=["caching", "aggregation", "fsm"],
    failure_handling="rollback_on_error"
)
```

### 2. Event-Driven Subcontract Coordination

Using events to coordinate subcontract execution:

```
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import ModelEventTypeSubcontract

# Event-driven processing pipeline
event_driven_processing = ModelEventTypeSubcontract(
    event_subscriptions=[
        {
            "event_type": "data.received",
            "subcontract_type": "aggregation",
            "processing_mode": "immediate",
            "correlation_required": True
        },
        {
            "event_type": "aggregation.completed",
            "subcontract_type": "routing",
            "processing_mode": "batch",
            "batch_size": 100
        },
        {
            "event_type": "routing.completed",
            "subcontract_type": "fsm",
            "processing_mode": "sequential",
            "state_context": "data_pipeline"
        }
    ],
    event_correlation_strategy={
        "correlation_field": "correlation_id",
        "timeout_seconds": 300,
        "max_correlation_age": 3600
    },
    correlation_id=uuid4()
)
```

### 3. Performance-Optimized Subcontract Chain

Optimizing subcontract execution for high-performance scenarios:

```
# High-performance trading system subcontract
trading_subcontract_chain = [
    # Ultra-fast caching for market data
    ModelCachingSubcontract(
        cache_levels=[{
            "level": "L1",
            "type": "cpu_cache",
            "size_kb": 64,
            "ttl_milliseconds": 100,
            "access_pattern": "sequential"
        }],
        performance_mode="ultra_fast",
        correlation_id=uuid4()
    ),
    # Real-time aggregation for price calculations
    ModelAggregationSubcontract(
        aggregation_functions=[
            ModelAggregationFunction(
                function_type="weighted_average",
                field_name="price",
                output_name="vwap",
                window_size_milliseconds=1000,
                correlation_id=uuid4()
            )
        ],
        performance_config=ModelAggregationPerformance(
            processing_mode="stream",
            latency_target_microseconds=50,
            memory_optimization="aggressive",
            correlation_id=uuid4()
        ),
        correlation_id=uuid4()
    ),
    # Intelligent routing for order execution
    ModelRoutingSubcontract(
        route_definitions=[
            ModelRouteDefinition(
                route_id="market_maker",
                routing_strategy="lowest_latency",
                latency_threshold_microseconds=100,
                correlation_id=uuid4()
            )
        ],
        performance_optimization={
            "pre_warm_connections": True,
            "connection_pooling": True,
            "circuit_breaker_fast_fail": True
        },
        correlation_id=uuid4()
    )
]
```

## Subcontract Testing Strategies

### Unit Testing Individual Subcontracts

```
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

class TestAggregationSubcontract:
    """Comprehensive tests for aggregation subcontract."""

    @pytest.fixture
    def aggregation_subcontract(self):
        """Create test aggregation subcontract."""
        return ModelAggregationSubcontract(
            aggregation_functions=[
                ModelAggregationFunction(
                    function_type="sum",
                    field_name="amount",
                    output_name="total",
                    correlation_id=uuid4()
                )
            ],
            data_grouping=ModelDataGrouping(
                group_by_fields=["category"],
                correlation_id=uuid4()
            ),
            performance_config=ModelAggregationPerformance(
                batch_size=1000,
                parallel_workers=2,
                correlation_id=uuid4()
            ),
            correlation_id=uuid4()
        )

    async def test_aggregation_execution(self, aggregation_subcontract):
        """Test aggregation subcontract execution."""
        # Mock input data
        input_data = [
            {"category": "A", "amount": 100},
            {"category": "A", "amount": 200},
            {"category": "B", "amount": 150},
            {"category": "B", "amount": 250}
        ]

        # Execute aggregation
        executor = AggregationExecutor(aggregation_subcontract)
        result = await executor.execute(input_data)

        # Verify results
        assert result.correlation_id == aggregation_subcontract.correlation_id
        assert "total" in result.aggregated_data
        assert result.aggregated_data["total"] == {"A": 300, "B": 400}

    async def test_correlation_tracking(self, aggregation_subcontract):
        """Test correlation ID propagation through subcontract."""
        correlation_id = aggregation_subcontract.correlation_id

        # Verify all subcomponents have same correlation ID
        for function in aggregation_subcontract.aggregation_functions:
            assert function.correlation_id == correlation_id

        assert aggregation_subcontract.data_grouping.correlation_id == correlation_id
        assert aggregation_subcontract.performance_config.correlation_id == correlation_id

    def test_validation_rules(self):
        """Test subcontract validation."""
        # Test invalid configuration
        with pytest.raises(ValidationError):
            ModelAggregationSubcontract(
                aggregation_functions=[],  # Empty list should fail
                correlation_id=uuid4()
            )

        # Test valid configuration
        valid_subcontract = ModelAggregationSubcontract(
            aggregation_functions=[
                ModelAggregationFunction(
                    function_type="count",
                    field_name="id",
                    output_name="record_count",
                    correlation_id=uuid4()
                )
            ],
            correlation_id=uuid4()
        )
        assert valid_subcontract.correlation_id is not None
```

### Integration Testing with Node Services

```
class TestSubcontractIntegration:
    """Integration tests for subcontracts with ONEX nodes."""

    async def test_reducer_with_aggregation_subcontract(self):
        """Test REDUCER node with aggregation subcontract."""
        # Create reducer contract with aggregation subcontract
        reducer_contract = ModelContractReducer(
            subcontracts=[
                ModelAggregationSubcontract(
                    aggregation_functions=[
                        ModelAggregationFunction(
                            function_type="average",
                            field_name="score",
                            output_name="avg_score",
                            correlation_id=uuid4()
                        )
                    ],
                    correlation_id=uuid4()
                )
            ],
            input_data=[
                {"score": 85}, {"score": 90}, {"score": 88}
            ],
            correlation_id=uuid4()
        )

        # Execute through reducer node
        reducer_service = AggregationReducerService(mock_container)
        result = await reducer_service.execute_reduction(reducer_contract)

        # Verify integration
        assert result.correlation_id == reducer_contract.correlation_id
        assert result.subcontract_results["aggregation"]["avg_score"] == 87.67

    async def test_orchestrator_with_fsm_subcontract(self):
        """Test ORCHESTRATOR node with FSM subcontract."""
        # Create orchestrator contract with FSM subcontract
        orchestrator_contract = ModelContractOrchestrator(
            subcontracts=[
                ModelFSMSubcontract(
                    state_definitions={
                        "start": ModelFSMStateDefinition(
                            name="start",
                            allowed_operations=["initialize"],
                            correlation_id=uuid4()
                        ),
                        "end": ModelFSMStateDefinition(
                            name="end",
                            correlation_id=uuid4()
                        )
                    },
                    initial_state="start",
                    final_states=["end"],
                    correlation_id=uuid4()
                )
            ],
            correlation_id=uuid4()
        )

        # Execute through orchestrator node
        orchestrator_service = FSMOrchestratorService(mock_container)
        result = await orchestrator_service.execute_orchestration(orchestrator_contract)

        # Verify FSM execution
        assert result.correlation_id == orchestrator_contract.correlation_id
        assert result.subcontract_results["fsm"]["final_state"] == "end"
```

## Performance Optimization Guidelines

### 1. Memory Management

```
# Efficient memory usage in aggregation subcontracts
memory_optimized_aggregation = ModelAggregationSubcontract(
    aggregation_functions=[
        ModelAggregationFunction(
            function_type="incremental_sum",  # Avoids storing all values
            field_name="revenue",
            output_name="running_total",
            correlation_id=uuid4()
        )
    ],
    performance_config=ModelAggregationPerformance(
        batch_size=10000,  # Larger batches for better throughput
        memory_limit_mb=256,  # Strict memory limits
        garbage_collection_enabled=True,
        memory_monitoring=True,
        correlation_id=uuid4()
    ),
    correlation_id=uuid4()
)
```

### 2. Parallel Processing

```
# Optimized parallel processing configuration
parallel_processing_config = ModelAggregationPerformance(
    parallel_workers=multiprocessing.cpu_count(),  # Use all available cores
    worker_memory_limit_mb=128,  # Per-worker memory limit
    load_balancing_strategy="dynamic",  # Adapt to workload
    worker_coordination="lock_free",  # Minimize synchronization overhead
    result_consolidation="streaming",  # Stream results as they become available
    correlation_id=uuid4()
)
```

### 3. Caching Optimization

```
# High-performance caching configuration
performance_caching = ModelCachingSubcontract(
    cache_levels=[
        {
            "level": "L1",
            "type": "cpu_cache_aligned",  # CPU cache-friendly data structures
            "size_mb": 64,
            "ttl_seconds": 60,
            "prefetch_enabled": True,
            "compression": "lz4"  # Fast compression algorithm
        },
        {
            "level": "L2",
            "type": "numa_aware_memory",  # NUMA-optimized memory allocation
            "size_mb": 512,
            "ttl_seconds": 300,
            "memory_mapping": "huge_pages"
        }
    ],
    performance_optimization={
        "batch_operations": True,
        "async_write_behind": True,
        "background_eviction": True,
        "memory_prefault": True
    },
    correlation_id=uuid4()
)
```

## Monitoring and Observability

### Subcontract Metrics Collection

```
from omnibase_core.types.typed_dict_performance_metric_data import TypedDictPerformanceMetricData

class SubcontractMetricsCollector:
    """Collect performance metrics from subcontract execution."""

    async def collect_aggregation_metrics(
        self,
        subcontract: ModelAggregationSubcontract,
        execution_result: AggregationResult
    ) -> List[TypedDictPerformanceMetricData]:
        """Collect metrics from aggregation subcontract execution."""
        metrics = []

        # Execution time metric
        metrics.append({
            "metric_name": "subcontract.aggregation.execution_time",
            "value": execution_result.execution_time_ms,
            "timestamp": datetime.now(UTC),
            "component_id": subcontract.correlation_id,
            "unit": "ms",
            "tags": {
                "subcontract_type": "aggregation",
                "function_count": str(len(subcontract.aggregation_functions)),
                "parallel_workers": str(subcontract.performance_config.parallel_workers)
            },
            "context": {
                "correlation_id": str(subcontract.correlation_id),
                "records_processed": execution_result.records_processed,
                "memory_peak_mb": execution_result.peak_memory_usage_mb
            }
        })

        # Throughput metric
        throughput = execution_result.records_processed / (execution_result.execution_time_ms / 1000)
        metrics.append({
            "metric_name": "subcontract.aggregation.throughput",
            "value": throughput,
            "timestamp": datetime.now(UTC),
            "component_id": subcontract.correlation_id,
            "unit": "records/sec",
            "tags": {
                "subcontract_type": "aggregation"
            },
            "context": {
                "correlation_id": str(subcontract.correlation_id)
            }
        })

        return metrics

    async def collect_fsm_metrics(
        self,
        subcontract: ModelFSMSubcontract,
        execution_result: FSMResult
    ) -> List[TypedDictPerformanceMetricData]:
        """Collect metrics from FSM subcontract execution."""
        metrics = []

        # State transition count
        metrics.append({
            "metric_name": "subcontract.fsm.transitions_executed",
            "value": execution_result.transition_count,
            "timestamp": datetime.now(UTC),
            "component_id": subcontract.correlation_id,
            "unit": "count",
            "tags": {
                "subcontract_type": "fsm",
                "initial_state": subcontract.initial_state,
                "final_state": execution_result.final_state
            },
            "context": {
                "correlation_id": str(subcontract.correlation_id),
                "execution_path": execution_result.execution_path
            }
        })

        return metrics
```

### Health Monitoring

```
class SubcontractHealthMonitor:
    """Monitor health of subcontract operations."""

    async def check_aggregation_health(
        self,
        subcontract: ModelAggregationSubcontract
    ) -> dict[str, Any]:
        """Check health of aggregation subcontract."""
        health_status = {
            "subcontract_type": "aggregation",
            "correlation_id": str(subcontract.correlation_id),
            "status": "healthy",
            "checks": {}
        }

        # Check memory usage
        memory_usage = await self._get_memory_usage(subcontract.correlation_id)
        memory_limit = subcontract.performance_config.memory_limit_mb
        memory_percentage = (memory_usage / memory_limit) * 100

        health_status["checks"]["memory"] = {
            "status": "healthy" if memory_percentage < 80 else "warning" if memory_percentage < 95 else "critical",
            "usage_mb": memory_usage,
            "limit_mb": memory_limit,
            "percentage": memory_percentage
        }

        # Check worker availability
        available_workers = await self._get_available_workers()
        required_workers = subcontract.performance_config.parallel_workers

        health_status["checks"]["workers"] = {
            "status": "healthy" if available_workers >= required_workers else "critical",
            "available": available_workers,
            "required": required_workers
        }

        # Determine overall health
        if any(check["status"] == "critical" for check in health_status["checks"].values()):
            health_status["status"] = "critical"
        elif any(check["status"] == "warning" for check in health_status["checks"].values()):
            health_status["status"] = "warning"

        return health_status
```

## New Subcontracts (v1.0.0)

### 5. Introspection Subcontract ⭐

**Primary Purpose**: Node metadata exposure, schema export, and discovery support

**File**: `model_introspection_subcontract.py`

**Key Features**:
- Comprehensive node metadata introspection (32 configurable fields)
- JSON schema and OpenAPI schema export
- Security-focused field filtering and redaction
- Depth-limited introspection to prevent performance issues
- Caching support for introspection responses
- Integration with discovery and registration systems

**Field Categories**:

**Metadata Inclusion Controls** (8 fields):
- `include_metadata` - Master switch for metadata inclusion
- `include_core_metadata` - Core fields (name, version, type)
- `include_organization_metadata` - Author, description, tags
- `include_contract` - Contract details
- `include_input_schema` / `include_output_schema` - I/O schemas
- `include_cli_interface` - CLI interface details
- `include_capabilities` - Node capabilities

**Dependency and Configuration** (5 fields):
- `include_dependencies` - Runtime dependencies
- `include_optional_dependencies` - Optional dependencies
- `include_external_tools` - External tool dependencies
- `include_state_models` - State model information
- `include_error_codes` - Error code definitions

**Filtering and Security** (7 fields):
- `depth_limit` - Maximum introspection depth (1-50, recommended ≤30)
- `exclude_fields` - Specific fields to exclude
- `exclude_field_patterns` - Security patterns (password, secret, token, api_key, etc.)
- `redact_sensitive_info` - Auto-redact sensitive information
- `require_authentication` - Require auth for introspection
- `allowed_introspection_sources` - IP allowlist for introspection

**Performance and Output** (6 fields):
- `cache_introspection_response` - Cache responses
- `cache_ttl_seconds` - Cache TTL (60-3600s, default 300s)
- `export_json_schema` / `export_openapi_schema` - Schema export formats
- `compact_output` - Compact JSON output
- `include_timestamps` / `include_version_info` - Timestamp/version controls

**Discovery Integration** (4 fields):
- `enable_auto_discovery` - Auto-discovery by registry services
- `enable_health_check` - Include health check endpoint
- `enable_lifecycle_hooks` - Include lifecycle hook info

**Validators** (4):
1. `validate_depth_limit()` - Warns if depth > 30 (performance)
2. `validate_cache_ttl()` - Ensures TTL ≥ 60s when caching enabled
3. `validate_introspection_consistency()` - Validates enabled features when introspection enabled
4. `validate_security_consistency()` - Ensures redaction enabled when auth required

**Usage Pattern**:

```
from omnibase_core.models.contracts.subcontracts.model_introspection_subcontract import ModelIntrospectionSubcontract

# Production introspection with security controls
production_introspection = ModelIntrospectionSubcontract(
    introspection_enabled=True,

    # Metadata configuration
    include_metadata=True,
    include_core_metadata=True,
    include_organization_metadata=True,
    include_contract=True,
    include_input_schema=True,
    include_output_schema=True,

    # Security controls
    redact_sensitive_info=True,
    require_authentication=True,
    exclude_field_patterns=[
        "password", "secret", "token", "api_key",
        "private_key", "credential", "auth_token"
    ],
    depth_limit=10,  # Reasonable depth

    # Performance optimization
    cache_introspection_response=True,
    cache_ttl_seconds=300,  # 5 minutes

    # Schema export
    export_json_schema=True,
    export_openapi_schema=False,  # Disable for internal nodes

    # Discovery integration
    enable_auto_discovery=True,
    enable_health_check=True,
)
```

**YAML Contract Example**:

```
introspection:
  introspection_enabled: true

  # Metadata controls
  include_metadata: true
  include_core_metadata: true
  include_contract: true
  include_input_schema: true
  include_output_schema: true
  include_capabilities: true

  # Security
  redact_sensitive_info: true
  exclude_field_patterns:
    - password
    - secret
    - token
    - api_key

  # Performance
  depth_limit: 10
  cache_introspection_response: true
  cache_ttl_seconds: 300

  # Discovery
  enable_auto_discovery: true
  enable_health_check: true
```

**Common Use Cases**:
- Service discovery and registration
- API documentation generation
- Health monitoring dashboards
- Debugging and troubleshooting

---

### 6. Discovery Subcontract ⭐

**Primary Purpose**: Service discovery responder configuration and broadcast handling

**File**: `model_discovery_subcontract.py`

**Key Features**:
- Automatic discovery broadcast response (24 configurable fields)
- Rate limiting and throttling to prevent discovery spam
- Capability advertisement and filtering
- Event bus integration with dedicated consumer groups
- Health status integration
- Response compression for large payloads

**Field Categories**:

**Core Configuration** (2 fields):
- `enabled` - Enable/disable discovery responder
- `auto_start` - Auto-start on node initialization

**Rate Limiting** (2 fields):
- `response_throttle_seconds` - Min time between responses (0.1-300s, default 1.0s)
- `response_timeout_seconds` - Max response generation time (0.5-60s, default 5.0s)

**Capability Advertisement** (2 fields):
- `advertise_capabilities` - Include capabilities in responses
- `custom_capabilities` - Additional custom capabilities beyond auto-detected

**Event Bus Integration** (2 fields):
- `discovery_channels` - Event channels (default: `["onex.discovery.broadcast", "onex.discovery.response"]`)
- `use_dedicated_consumer_group` - Node-specific consumer group

**Response Content** (5 fields):
- `include_introspection` - Full node introspection data
- `include_event_channels` - Event channel information
- `include_version_info` - Node version information
- `include_health_status` - Current health status
- `default_health_status` - Fallback status (healthy/degraded/unhealthy)

**Filtering** (3 fields):
- `filter_enabled` - Enable custom request filtering
- `match_node_types` - Node types to match (empty = match all)
- `required_capabilities_filter` - Only respond if request requires these capabilities

**Monitoring** (4 fields):
- `enable_metrics` - Discovery response metrics
- `enable_detailed_logging` - Detailed operation logging
- `log_throttled_requests` - Log throttled requests (can be noisy)
- `log_filtered_requests` - Log filtered requests (can be noisy)

**Performance** (2 fields):
- `max_response_size_bytes` - Max response size (1KB-1MB, default 100KB)
- `enable_response_compression` - Compress large payloads

**Validators** (5):
1. Validates `default_health_status` must be healthy/degraded/unhealthy
2. Validates `discovery_channels` cannot be empty
3. Validates `response_throttle_seconds` < `response_timeout_seconds`
4. Warns if `max_response_size_bytes` > 512KB (performance)
5. Validates at least one response content type enabled

**YAML Contract Example**:

```
discovery:
  enabled: true
  auto_start: true

  # Rate limiting
  response_throttle_seconds: 1.0
  response_timeout_seconds: 5.0

  # Capabilities
  advertise_capabilities: true
  custom_capabilities:
    - data-processing
    - ml-inference

  # Response content
  include_introspection: true
  include_health_status: true
  default_health_status: healthy

  # Performance
  max_response_size_bytes: 102400
  enable_metrics: true
```

**Integration with MixinDiscoveryResponder**: Designed for use with `MixinDiscoveryResponder` mixin.

---

### 7. Event Handling Subcontract ⭐

**Primary Purpose**: Event subscription, filtering, and handler lifecycle management

**File**: `model_event_handling_subcontract.py`

**Key Features**:
- Comprehensive event handling configuration (25+ fields)
- Pattern-based event filtering (node ID, node name, fnmatch patterns)
- Automatic introspection and discovery request handling
- Retry logic with exponential backoff
- Dead letter queue for failed events
- Async and sync event bus support

**Field Categories**:

**Core Configuration** (2 fields):
- `enabled` - Enable event handling functionality
- `subscribed_events` - Event types to subscribe to (default: `["NODE_INTROSPECTION_REQUEST", "NODE_DISCOVERY_REQUEST"]`)

**Subscription Management** (1 field):
- `auto_subscribe_on_init` - Auto-subscribe during initialization

**Event Filtering** (4 fields):
- `event_filters` - Custom filtering rules (dict with patterns)
- `enable_node_id_filtering` - Filter by node ID (fnmatch patterns)
- `enable_node_name_filtering` - Filter by node name (fnmatch patterns)
- `respond_to_all_when_no_filter` - Respond to all when no filters present

**Introspection Handling** (3 fields):
- `handle_introspection_requests` - Handle NODE_INTROSPECTION_REQUEST events
- `handle_discovery_requests` - Handle NODE_DISCOVERY_REQUEST events
- `filter_introspection_data` - Filter based on requested_types in metadata

**Event Bus Support** (3 fields):
- `async_event_bus_support` - Support async event bus (subscribe_async)
- `sync_event_bus_fallback` - Fall back to sync when async unavailable
- `cleanup_on_shutdown` - Auto-cleanup handlers on shutdown

**Retry and Resilience** (3 fields):
- `max_retries` - Maximum retry attempts (0-10, default 3)
- `retry_delay_seconds` - Delay between retries (0.1-60s, default 1.0s)
- `retry_exponential_backoff` - Use exponential backoff

**Dead Letter Queue** (3 fields):
- `dead_letter_channel` - DLQ channel (None = no DLQ)
- `dead_letter_max_events` - Max events in DLQ (10-10000, default 1000)
- `dead_letter_overflow_strategy` - DLQ overflow: drop_oldest/drop_newest/block

**Validators** (4):
1. Validates `subscribed_events` cannot be empty when enabled
2. Validates `dead_letter_channel` format (alphanumeric + _ . -)
3. Validates `dead_letter_overflow_strategy` in allowed values
4. Comprehensive configuration validation

**YAML Contract Example**:

```
event_handling:
  enabled: true

  # Subscriptions
  subscribed_events:
    - NODE_INTROSPECTION_REQUEST
    - NODE_DISCOVERY_REQUEST
    - DATA_PROCESSING_REQUEST
  auto_subscribe_on_init: true

  # Filtering
  event_filters:
    node_name: "compute-*"
    environment: production
  enable_node_id_filtering: true

  # Retry
  max_retries: 3
  retry_delay_seconds: 1.0
  retry_exponential_backoff: true

  # Dead letter queue
  dead_letter_channel: onex.dlq.events
  dead_letter_max_events: 1000
  dead_letter_overflow_strategy: drop_oldest

  # Performance
  handler_timeout_seconds: 30.0
  track_handler_performance: true
```

**Test Coverage**: 43 comprehensive tests validating all validators, edge cases, and integration patterns.

---

### 8. Lifecycle Subcontract ⭐

**Primary Purpose**: Node startup/shutdown management and lifecycle hooks

**File**: `model_lifecycle_subcontract.py`

**Key Features**:
- Comprehensive lifecycle management (29 configurable fields)
- Startup and shutdown timeout configuration
- Graceful shutdown with proper resource cleanup
- Pre/post lifecycle hooks
- Automatic node registration/deregistration
- Health checks during lifecycle transitions

**Field Categories**:

**Startup Configuration** (4 fields):
- `startup_timeout_seconds` - Max startup time (1-3600s, default 30s)
- `startup_retry_enabled` - Retry on startup failure
- `max_startup_retries` - Max retry attempts (0-10, default 3)
- `startup_retry_delay_seconds` - Delay between retries (1-60s, default 5s)

**Shutdown Configuration** (3 fields):
- `shutdown_timeout_seconds` - Max graceful shutdown time (1-3600s, default 30s)
- `enable_graceful_shutdown` - Enable graceful shutdown
- `force_shutdown_after_timeout` - Force shutdown if timeout exceeded

**Registration** (3 fields):
- `auto_register_on_startup` - Auto-register on event bus
- `auto_deregister_on_shutdown` - Auto-deregister from event bus
- `publish_shutdown_event` - Publish NODE_SHUTDOWN event

**Lifecycle Hooks** (4 fields):
- `pre_startup_hooks` - Hook functions before startup
- `post_startup_hooks` - Hook functions after startup
- `pre_shutdown_hooks` - Hook functions before shutdown
- `post_shutdown_hooks` - Hook functions after shutdown

**Validators** (8):
1. Validates hook names must be valid Python identifiers
2. Validates shutdown timeout allows adequate cleanup time
3. Validates hook timeout < startup/shutdown timeout
4. Validates cleanup timeout ≤ shutdown timeout
5. Validates health check timeout < startup timeout
6. Validates event emission requires corresponding registration

**YAML Contract Example**:

```
lifecycle:
  # Startup
  startup_timeout_seconds: 60.0
  startup_retry_enabled: true
  max_startup_retries: 3

  # Shutdown
  shutdown_timeout_seconds: 60.0
  enable_graceful_shutdown: true
  force_shutdown_after_timeout: true

  # Hooks
  pre_startup_hooks:
    - initialize_database
    - connect_to_services
  post_startup_hooks:
    - warm_cache

  # Events
  emit_lifecycle_events: true
  emit_node_announce: true
  emit_node_shutdown: true

  # Cleanup
  cleanup_event_handlers: true
  cleanup_resources: true
```

---

### 9. Observability Subcontract ⭐

**Primary Purpose**: Unified observability configuration (logging, metrics, distributed tracing)

**File**: `model_observability_subcontract.py`

**Key Features**:
- Unified observability across all three pillars (20+ fields)
- Distributed tracing with OpenTelemetry support
- Performance profiling with CPU, memory, I/O instrumentation
- Configurable sampling rates for production efficiency
- Export format configuration (JSON, OpenTelemetry, Prometheus)
- Sensitive data redaction

**Field Categories**:

**Logging** (3 fields):
- `log_level` - Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `enable_structured_logging` - Structured logging with consistent fields
- `enable_correlation_tracking` - Track correlation IDs

**Distributed Tracing** (5 fields):
- `enable_tracing` - Enable distributed tracing
- `trace_sampling_rate` - Sampling rate (0.0-1.0, default 0.1)
- `trace_propagation_format` - Context format (w3c/b3/jaeger)
- `trace_exporter_endpoint` - OTLP collector endpoint
- `trace_service_name` - Service name (defaults to node name)

**Performance Profiling** (6 fields):
- `enable_profiling` - Enable performance profiling
- `profiling_sampling_rate` - Sampling rate (0.0-1.0, default 0.01)
- `profile_cpu` - CPU profiling
- `profile_memory` - Memory profiling
- `profile_io` - I/O profiling (higher overhead)
- `profiling_output_path` - Output path (defaults to temp)

**Validators** (7):
1. Validates log level must be DEBUG/INFO/WARNING/ERROR/CRITICAL
2. Validates trace propagation format must be w3c/b3/jaeger
3. Validates export format must be json/opentelemetry/prometheus
4. Warns if trace sampling rate > 0.5 (50% overhead)
5. Warns if profiling sampling rate > 0.1 (10% overhead)
6. Requires trace_exporter_endpoint when tracing enabled
7. Validates at least one profiler enabled when profiling enabled

**YAML Contract Example**:

```
observability:
  enabled: true

  # Logging
  log_level: INFO
  enable_structured_logging: true
  enable_correlation_tracking: true

  # Tracing
  enable_tracing: true
  trace_sampling_rate: 0.1
  trace_propagation_format: w3c
  trace_exporter_endpoint: http://otel-collector:4318

  # Profiling
  enable_profiling: true
  profiling_sampling_rate: 0.01
  profile_cpu: true
  profile_memory: true

  # Export
  export_format: opentelemetry
  export_interval_seconds: 60

  # Security
  enable_sensitive_data_redaction: true
```

**Test Coverage**: 44 comprehensive tests validating all validators, sampling rates, and integration patterns.

---

### 10. Tool Execution Subcontract ⭐

**Primary Purpose**: Standardized tool execution with resource management

**File**: `model_tool_execution_subcontract.py`

**Key Features**:
- Comprehensive tool execution configuration (30+ fields)
- Execution timeout and parallel execution limits
- Retry logic with exponential backoff
- Output capture and buffering
- Environment variable management
- Resource isolation and limits

**Field Categories**:

**Core Execution** (2 fields):
- `enabled` - Enable tool execution
- `timeout_seconds` - Max execution time (0.1-3600s, default 30s)

**Parallel Execution** (3 fields):
- `max_parallel_executions` - Max concurrent executions (1-100, default 1)
- `queue_overflow_policy` - Overflow policy (block/reject/drop_oldest)
- `max_queue_size` - Max queue size (1-10000, default 100)

**Retry Configuration** (4 fields):
- `retry_on_failure` - Auto-retry failed executions
- `max_retry_attempts` - Max retries (0-10, default 3)
- `retry_delay_seconds` - Delay between retries (0-60s, default 1s)
- `retry_exponential_backoff` - Exponential backoff

**Helper Methods** (5):
1. `get_effective_timeout(attempt)` - Timeout with exponential backoff
2. `get_retry_delay(attempt)` - Retry delay with exponential backoff
3. `should_retry(attempt, error)` - Retry decision logic
4. `get_output_buffer_size_bytes()` - Buffer size in bytes
5. `get_effective_environment(additional_vars)` - Merged environment with sanitization
6. `is_within_resource_limits(memory_mb, cpu_percent)` - Resource limit check

**Validators** (5):
1. Validates `queue_overflow_policy` must be block/reject/drop_oldest
2. Validates `error_handling_strategy` must be propagate/suppress/log_and_continue
3. Validates retry configuration consistency
4. Validates resource limits require resource_isolation=True
5. Validates event execution requires enabled=True

**YAML Contract Example**:

```
tool_execution:
  enabled: true
  timeout_seconds: 60.0

  # Parallel execution
  max_parallel_executions: 4
  queue_overflow_policy: block

  # Retry
  retry_on_failure: true
  max_retry_attempts: 3
  retry_exponential_backoff: true

  # Resource limits
  resource_isolation: true
  max_memory_mb: 2048
  max_cpu_percent: 80

  # Monitoring
  emit_execution_metrics: true
```

**Security**: The `sanitize_environment` flag removes potentially dangerous environment variables to prevent library injection attacks.

---

## Mixin-Subcontract Integration Matrix

This table shows which mixins are designed to work with which subcontracts:

| Mixin | Subcontract | Purpose |
|-------|-------------|---------|
| **MixinDiscoveryResponder** | ModelDiscoverySubcontract | Service discovery broadcast response |
| **MixinEventHandler** | ModelEventHandlingSubcontract | Event subscription and filtering |
| **MixinNodeLifecycle** | ModelLifecycleSubcontract | Startup/shutdown management |
| **MixinIntrospection** | ModelIntrospectionSubcontract | Node metadata and schema exposure |
| **MixinToolExecution** | ModelToolExecutionSubcontract | Tool execution and resource management |
| **MixinMetrics** | ModelObservabilitySubcontract | Performance metrics collection |
| **MixinFSMExecution** | ModelFSMSubcontract | State machine execution |
| **MixinCaching** | ModelCachingSubcontract | Cache management |
| **MixinEventListener** | ModelEventTypeSubcontract | Event type routing |
| **MixinHealthCheck** | ModelHealthCheckSubcontract | Health monitoring |

## Best Practices and Recommendations

### 1. Subcontract Design Principles

- **Single Responsibility**: Each subcontract should handle one specific aspect of processing
- **Correlation Tracking**: Always include correlation IDs for complete request traceability
- **Error Handling**: Implement comprehensive error handling with proper recovery mechanisms
- **Performance Optimization**: Design with performance requirements in mind from the beginning
- **Testing**: Include comprehensive unit and integration tests for all subcontract functionality

### 2. Integration Guidelines

- **Node Compatibility**: Ensure subcontracts are compatible with their target node types
- **Resource Management**: Monitor and manage resource usage to prevent system overload
- **Configuration Validation**: Validate all subcontract configurations before execution
- **Monitoring Integration**: Include proper monitoring and observability from the start
- **Documentation**: Maintain comprehensive documentation for all subcontract patterns

### 3. Performance Considerations

- **Memory Usage**: Monitor and optimize memory usage, especially for large-scale operations
- **Parallel Processing**: Use parallel processing judiciously based on workload characteristics
- **Caching Strategy**: Implement appropriate caching strategies for frequently accessed data
- **Network Optimization**: Minimize network overhead in distributed subcontract operations
- **Resource Pooling**: Use connection pooling and resource reuse where appropriate

---

*This subcontract architecture documentation provides comprehensive coverage of all subcontract patterns with zero tolerance for incomplete specifications and practical usage examples for all scenarios.*
