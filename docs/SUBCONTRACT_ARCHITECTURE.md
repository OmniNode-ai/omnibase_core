# ONEX Subcontract Package Architecture

## Overview

The ONEX Subcontract Package provides specialized contract models for complex operations within the Four-Node Architecture. Subcontracts enable sophisticated processing patterns including finite state machines, data aggregation, routing, and workflow coordination while maintaining ONEX compliance and correlation tracking.

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

```python
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

```python
from omnibase_core.core.infrastructure_service_bases import NodeReducerService
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

class AggregationReducerService(NodeReducerService):
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

```python
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

```python
from omnibase_core.core.infrastructure_service_bases import NodeOrchestratorService

class FSMOrchestratorService(NodeOrchestratorService):
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

```python
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

```python
from omnibase_core.core.infrastructure_service_bases import NodeEffectService

class RoutingEffectService(NodeEffectService):
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

```python
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

```python
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

```python
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

```python
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

```python
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

```python
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

```python
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

```python
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

```python
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

```python
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
            "timestamp": datetime.utcnow(),
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
            "timestamp": datetime.utcnow(),
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
            "timestamp": datetime.utcnow(),
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

```python
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
