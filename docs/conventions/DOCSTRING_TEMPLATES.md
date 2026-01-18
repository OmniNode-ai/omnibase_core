> **Navigation**: [Home](../INDEX.md) > Conventions > Docstring Templates

# ONEX Contract Model Docstring Templates

## Overview

This document provides comprehensive docstring templates for all contract model classes introduced in PR #36. These templates ensure zero tolerance for incomplete documentation and establish consistent documentation standards across the ONEX framework.

## Docstring Standards

### Required Elements
1. **Brief Description**: One-line summary of the class purpose
2. **Detailed Description**: Comprehensive explanation of functionality
3. **Attributes Section**: Complete attribute documentation with types and descriptions
4. **Example Section**: Practical usage examples with realistic data
5. **Raises Section**: All possible exceptions with conditions
6. **Note Section**: Important usage considerations and architectural context
7. **Validation Rules**: Any validation constraints or business rules

### Formatting Requirements
- Use Google-style docstrings for consistency
- Include type information in attribute descriptions
- Provide realistic, runnable examples
- Document all validation rules and constraints
- Include correlation ID usage patterns

## Contract Model Docstring Templates

### ModelAlgorithmConfig Template

```
class ModelAlgorithmConfig(BaseModel):
    """
    Configuration for algorithm execution in COMPUTE nodes.

    Defines algorithm-specific parameters, execution modes, and performance
    optimization settings for computational processing within the ONEX
    Four-Node Architecture.

    This configuration class supports various algorithm types including machine
    learning models, statistical computations, data transformations, and custom
    processing algorithms. It provides fine-grained control over execution
    parameters and performance optimization strategies.

    Attributes:
        algorithm_type (str): Type identifier for the algorithm to execute.
            Supported types include: "machine_learning", "statistical",
            "data_transformation", "custom". Must match a registered algorithm
            in the algorithm registry.
        parameters (dict[str, Any]): Algorithm-specific configuration parameters.
            The structure depends on the algorithm_type. For machine learning
            algorithms, may include learning_rate, batch_size, epochs. For
            statistical algorithms, may include confidence_level, sample_size.
        optimization_level (str): Performance optimization level affecting
            execution speed and resource usage. Options: "low" (minimal
            optimization), "medium" (balanced), "high" (maximum performance).
            Default: "medium".
        factor_config (Optional[ModelAlgorithmFactorConfig]): Advanced factor
            configuration for complex algorithms requiring multi-dimensional
            parameter tuning. None for simple algorithms.
        performance_monitoring (bool): Whether to collect detailed performance
            metrics during execution. Enables execution time tracking, memory
            usage monitoring, and throughput measurement. Default: False.

    Example:
        ```python
        # Machine learning algorithm configuration
        ml_config = ModelAlgorithmConfig(
            algorithm_type="machine_learning",
            parameters={
                "model_path": "/models/neural_network_v2.pkl",
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs": 100,
                "validation_split": 0.2
            },
            optimization_level="high",
            performance_monitoring=True
        )

        # Statistical analysis configuration
        stats_config = ModelAlgorithmConfig(
            algorithm_type="statistical",
            parameters={
                "analysis_type": "regression",
                "confidence_level": 0.95,
                "sample_size": 1000
            },
            optimization_level="medium"
        )

        # Custom algorithm with factor configuration
        custom_config = ModelAlgorithmConfig(
            algorithm_type="custom",
            parameters={"custom_param": "value"},
            factor_config=ModelAlgorithmFactorConfig(
                primary_factors=["accuracy", "speed"],
                weight_distribution={"accuracy": 0.7, "speed": 0.3}
            )
        )
        ```

    Validation Rules:
        - algorithm_type must be a recognized algorithm identifier registered
          in the system algorithm registry
        - parameters must contain all required keys for the specified algorithm_type
        - optimization_level must be one of: "low", "medium", "high"
        - When factor_config is provided, algorithm_type should support
          factor-based optimization

    Raises:
        ValidationError: If algorithm_type is not recognized, required parameters
            are missing, or optimization_level is invalid.
        AlgorithmRegistryError: If the specified algorithm_type is not registered
            or is currently unavailable.

    Note:
        Algorithm configurations are validated against the algorithm registry
        at runtime to ensure compatibility with the COMPUTE node infrastructure.
        Performance monitoring incurs additional overhead but provides valuable
        insights for optimization and debugging.

        For ONEX compliance, all algorithm configurations must include proper
        error handling and should be designed to work within the Four-Node
        Architecture's data flow patterns.
    """

    algorithm_type: str
    parameters: dict[str, Any]
    optimization_level: str = "medium"
    factor_config: Optional[ModelAlgorithmFactorConfig] = None
    performance_monitoring: bool = False

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True
    )
```

### ModelBackupConfig Template

```
class ModelBackupConfig(BaseModel):
    """
    Configuration for state backup and recovery operations in REDUCER nodes.

    Defines backup strategies, storage locations, retention policies, and
    recovery procedures for maintaining data integrity and disaster recovery
    capabilities within the ONEX architecture.

    This configuration supports multiple backup strategies including incremental,
    full, and differential backups with configurable retention policies and
    compression options. It ensures data durability and provides rollback
    capabilities for transaction-based operations.

    Attributes:
        backup_strategy (str): Backup strategy type determining how backups are
            created and managed. Options: "incremental" (only changed data),
            "full" (complete state backup), "differential" (changes since last
            full backup). Default: "incremental".
        storage_location (str): Backup storage location URL or path. Supports
            local filesystem paths, cloud storage URLs (s3://, gcs://), and
            network storage locations. Must be accessible to the REDUCER node.
        retention_policy (dict[str, Any]): Backup retention configuration
            defining how long backups are kept and cleanup policies.
            Structure: {"max_backups": int, "retention_days": int,
            "compression_enabled": bool}.
        encryption_config (Optional[dict[str, str]]): Encryption settings for
            backup data. Structure: {"encryption_key": str, "algorithm": str}.
            None for unencrypted backups (not recommended for production).
        compression_level (int): Backup compression level from 0 (no compression)
            to 9 (maximum compression). Higher levels reduce storage space but
            increase CPU usage. Default: 6.
        verification_enabled (bool): Whether to verify backup integrity after
            creation using checksums. Recommended for critical data. Default: True.

    Example:
        ```python
        # Production backup configuration with encryption
        production_backup = ModelBackupConfig(
            backup_strategy="incremental",
            storage_location="s3://prod-backups/reducer-states/",
            retention_policy={
                "max_backups": 30,
                "retention_days": 90,
                "compression_enabled": True
            },
            encryption_config={
                "encryption_key": "backup_key_id",
                "algorithm": "AES256"
            },
            compression_level=7,
            verification_enabled=True
        )

        # Development backup configuration
        dev_backup = ModelBackupConfig(
            backup_strategy="full",
            storage_location="/tmp/dev-backups/",
            retention_policy={
                "max_backups": 5,
                "retention_days": 7,
                "compression_enabled": False
            },
            compression_level=3,
            verification_enabled=False
        )

        # High-frequency backup for critical systems
        critical_backup = ModelBackupConfig(
            backup_strategy="differential",
            storage_location="gcs://critical-backups/states/",
            retention_policy={
                "max_backups": 100,
                "retention_days": 365,
                "compression_enabled": True
            },
            encryption_config={
                "encryption_key": "critical_backup_key",
                "algorithm": "AES256"
            },
            compression_level=9,
            verification_enabled=True
        )
        ```

    Validation Rules:
        - backup_strategy must be one of: "incremental", "full", "differential"
        - storage_location must be a valid, accessible path or URL
        - retention_policy.max_backups must be positive integer
        - retention_policy.retention_days must be positive integer
        - compression_level must be between 0 and 9 inclusive
        - If encryption_config is provided, both encryption_key and algorithm are required

    Raises:
        ValidationError: If backup_strategy is invalid, storage_location is
            inaccessible, or retention_policy values are out of range.
        StorageError: If the specified storage_location cannot be accessed
            or lacks required permissions.
        EncryptionError: If encryption_config is provided but encryption
            key is invalid or algorithm is unsupported.

    Note:
        Backup configurations should be tested regularly to ensure recovery
        procedures work correctly. For ONEX compliance, backup operations
        must not interfere with normal REDUCER node operations and should
        be designed to handle concurrent access safely.

        Storage locations should have appropriate access controls and monitoring
        in place. Consider network latency when using remote storage locations
        as it may impact backup performance and node response times.
    """

    backup_strategy: str = "incremental"
    storage_location: str
    retention_policy: dict[str, Any]
    encryption_config: Optional[dict[str, str]] = None
    compression_level: int = 6
    verification_enabled: bool = True

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True
    )
```

### ModelEventDescriptor Template

```
class ModelEventDescriptor(BaseModel):
    """
    Event descriptor for event-driven processing in ORCHESTRATOR nodes.

    Defines event metadata, routing information, and processing requirements
    for event-driven workflows within the ONEX Four-Node Architecture.
    Supports complex event patterns, conditional routing, and event aggregation.

    This descriptor enables sophisticated event-driven orchestration patterns
    including event correlation, temporal event processing, and conditional
    workflow execution based on event characteristics and content.

    Attributes:
        event_type (str): Unique identifier for the event type. Used for
            event routing and subscriber matching. Should follow reverse
            domain naming convention (e.g., "com.company.service.event").
        event_source (str): Source system or component that generates this
            event type. Used for event filtering and source-based routing.
        event_version (str): Event schema version following semantic versioning.
            Enables schema evolution and backward compatibility. Format: "major.minor.patch".
        routing_key (str): Event routing key for message broker routing.
            Supports pattern matching and hierarchical routing structures.
        priority_level (int): Event processing priority from 1 (lowest) to
            10 (highest). Higher priority events are processed first.
        correlation_patterns (List[str]): Patterns for correlating related
            events. Supports regex patterns and field-based correlation.
        timeout_seconds (Optional[int]): Maximum time to wait for event
            processing completion. None for no timeout. Default: None.
        retry_policy (Optional[dict[str, Any]]): Retry configuration for
            failed event processing. Structure: {"max_retries": int,
            "backoff_strategy": str, "retry_conditions": List[str]}.

    Example:
        ```python
        # High-priority system event
        system_event = ModelEventDescriptor(
            event_type="com.system.node.health_check",
            event_source="health_monitor_service",
            event_version="1.2.0",
            routing_key="system.health.*",
            priority_level=9,
            correlation_patterns=[
                "correlation_id:(.*)",
                "node_id:(.*)"
            ],
            timeout_seconds=30,
            retry_policy={
                "max_retries": 3,
                "backoff_strategy": "exponential",
                "retry_conditions": ["timeout", "temporary_failure"]
            }
        )

        # Business workflow event
        workflow_event = ModelEventDescriptor(
            event_type="com.business.order.created",
            event_source="order_management_service",
            event_version="2.0.1",
            routing_key="business.orders.created",
            priority_level=5,
            correlation_patterns=[
                "order_id:(.*)",
                "customer_id:(.*)"
            ],
            timeout_seconds=300
        )

        # Low-priority analytics event
        analytics_event = ModelEventDescriptor(
            event_type="com.analytics.user.action",
            event_source="web_application",
            event_version="1.0.0",
            routing_key="analytics.user.*",
            priority_level=2,
            correlation_patterns=["session_id:(.*)"],
            # No timeout for analytics events
        )
        ```

    Validation Rules:
        - event_type must follow reverse domain naming convention
        - event_version must be valid semantic version (major.minor.patch)
        - priority_level must be between 1 and 10 inclusive
        - routing_key must be non-empty and contain valid routing patterns
        - correlation_patterns must be valid regex patterns
        - timeout_seconds must be positive integer if provided
        - retry_policy.max_retries must be non-negative integer if provided

    Raises:
        ValidationError: If event_type format is invalid, event_version is not
            a valid semantic version, or priority_level is out of range.
        PatternValidationError: If correlation_patterns contain invalid regex
            expressions that cannot be compiled.
        ConfigurationError: If retry_policy is provided but contains invalid
            configuration parameters.

    Note:
        Event descriptors are used by ORCHESTRATOR nodes to configure event
        handling, routing, and processing pipelines. They should be designed
        to support the expected event volume and processing requirements.

        For ONEX compliance, event descriptors must include proper correlation
        support to maintain request traceability across the Four-Node pipeline.
        Consider event ordering and duplicate handling when designing event
        processing workflows.

        Correlation patterns are crucial for event aggregation and multi-event
        workflows. Use consistent correlation strategies across related events
        to enable effective event correlation and processing.
    """

    event_type: str
    event_source: str
    event_version: str
    routing_key: str
    priority_level: int = 5
    correlation_patterns: List[str] = Field(default_factory=list)
    timeout_seconds: Optional[int] = None
    retry_policy: Optional[dict[str, Any]] = None

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True
    )
```

## Subcontract Model Docstring Templates

### ModelAggregationSubcontract Template

```
class ModelAggregationSubcontract(BaseModel):
    """
    Subcontract for data aggregation operations in ONEX pipeline processing.

    Defines comprehensive aggregation patterns, data grouping strategies, and
    performance optimization settings for large-scale data consolidation
    operations within REDUCER nodes.

    This subcontract supports various aggregation methods including statistical
    operations (sum, average, count, median), custom aggregation functions,
    and complex multi-dimensional grouping with optimized performance for
    both batch and streaming data processing scenarios.

    Attributes:
        aggregation_functions (List[ModelAggregationFunction]): List of
            aggregation operations to perform on the input data. Each function
            defines the operation type, target fields, and output specifications.
            Supports chaining multiple aggregations on the same dataset.
        data_grouping (ModelDataGrouping): Configuration for data grouping
            and partitioning before aggregation. Defines group-by fields,
            sorting criteria, and partition strategies for optimal performance.
        performance_config (ModelAggregationPerformance): Performance
            optimization settings including batch sizes, parallel processing
            configuration, memory limits, and caching strategies.
        circuit_breaker (Optional[ModelCircuitBreaker]): Circuit breaker
            configuration for fault tolerance during high-load scenarios.
            Prevents cascade failures and maintains system stability. None
            to disable circuit breaker protection.
        correlation_id (UUID): Unique identifier for request correlation and
            distributed tracing across the ONEX Four-Node Architecture.
            Automatically generated if not provided.

    Example:
        ```python
        # Financial data aggregation subcontract
        financial_aggregation = ModelAggregationSubcontract(
            aggregation_functions=[
                ModelAggregationFunction(
                    function_type="sum",
                    field_name="transaction_amount",
                    output_name="total_revenue",
                    filter_conditions={"status": "completed"}
                ),
                ModelAggregationFunction(
                    function_type="avg",
                    field_name="customer_rating",
                    output_name="average_rating",
                    precision=2
                ),
                ModelAggregationFunction(
                    function_type="count_distinct",
                    field_name="customer_id",
                    output_name="unique_customers"
                )
            ],
            data_grouping=ModelDataGrouping(
                group_by_fields=["product_category", "sales_region"],
                sort_order="desc",
                sort_field="total_revenue"
            ),
            performance_config=ModelAggregationPerformance(
                batch_size=5000,
                parallel_workers=8,
                memory_limit_mb=1024,
                enable_caching=True,
                cache_ttl_seconds=300
            ),
            circuit_breaker=ModelCircuitBreaker(
                failure_threshold=5,
                recovery_timeout_seconds=60,
                half_open_max_calls=3
            )
        )

        # Real-time analytics aggregation
        realtime_aggregation = ModelAggregationSubcontract(
            aggregation_functions=[
                ModelAggregationFunction(
                    function_type="sliding_window_avg",
                    field_name="response_time",
                    output_name="avg_response_time_5min",
                    window_size_seconds=300
                ),
                ModelAggregationFunction(
                    function_type="percentile",
                    field_name="response_time",
                    output_name="p95_response_time",
                    percentile=95
                )
            ],
            data_grouping=ModelDataGrouping(
                group_by_fields=["service_name", "environment"],
                time_window_seconds=300
            ),
            performance_config=ModelAggregationPerformance(
                batch_size=1000,
                parallel_workers=4,
                memory_limit_mb=512,
                streaming_mode=True
            )
        )
        ```

    Performance Considerations:
        - Batch size should be tuned based on available memory and data characteristics
        - Parallel workers should not exceed CPU core count for optimal performance
        - Circuit breaker prevents resource exhaustion during high-load scenarios
        - Streaming mode enables real-time processing with lower latency
        - Caching can significantly improve performance for repeated aggregations

    Validation Rules:
        - aggregation_functions list must contain at least one function
        - All aggregation function field names must exist in input data schema
        - data_grouping.group_by_fields must be valid field names
        - performance_config.parallel_workers must be positive integer
        - performance_config.memory_limit_mb must be positive and within system limits
        - circuit_breaker thresholds must be positive integers if configured

    Raises:
        ValidationError: If aggregation_functions is empty, field names are invalid,
            or performance configuration values are out of acceptable ranges.
        SchemaValidationError: If specified field names do not exist in the
            input data schema or have incompatible data types.
        ResourceLimitError: If performance configuration exceeds system resource
            limits or conflicts with other running processes.

    Note:
        Aggregation subcontracts are optimized for both batch and streaming
        data processing scenarios. They integrate seamlessly with the ONEX
        REDUCER node architecture and support real-time updates to aggregation
        results.

        For optimal performance, consider data distribution and partitioning
        strategies when defining group-by fields. Use circuit breakers in
        production environments to maintain system stability under high load.

        Correlation IDs are essential for tracking aggregation operations
        across the ONEX Four-Node pipeline and enable comprehensive monitoring
        and debugging capabilities.
    """

    aggregation_functions: List[ModelAggregationFunction]
    data_grouping: ModelDataGrouping
    performance_config: ModelAggregationPerformance
    circuit_breaker: Optional[ModelCircuitBreaker] = None
    correlation_id: UUID = Field(default_factory=uuid4)

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True
    )
```

### ModelFSMSubcontract Template

```
class ModelFSMSubcontract(BaseModel):
    """
    Finite State Machine (FSM) subcontract for state-based workflow processing.

    Defines deterministic state transitions, conditional logic, and actions
    for complex workflow management within ORCHESTRATOR nodes. Provides
    comprehensive state machine capabilities with audit trails, rollback
    support, and parallel state handling.

    This subcontract enables sophisticated workflow orchestration through
    well-defined state machines with conditional transitions, timeout handling,
    and comprehensive error recovery mechanisms. It supports both simple
    linear workflows and complex branching state machines.

    Attributes:
        state_definitions (dict[str, ModelFSMStateDefinition]): Complete
            definition of all available states in the FSM. Each state includes
            metadata, allowed operations, timeout configurations, and exit
            conditions. Keys are state names, values are state definitions.
        transitions (List[ModelFSMStateTransition]): All valid state transitions
            with conditions, actions, and metadata. Defines the complete state
            transition graph with conditional logic and automated actions.
        initial_state (str): Starting state name for FSM execution. Must exist
            in state_definitions. This state is entered when FSM is initialized.
        final_states (List[str]): Terminal states that end FSM processing.
            All states in this list must exist in state_definitions. FSM
            execution completes when any final state is reached.
        operations (List[ModelFSMOperation]): Operations available within
            FSM states. Defines what actions can be performed in each state
            and their execution parameters.
        correlation_id (UUID): Unique identifier for request correlation and
            FSM execution tracking across distributed systems.
        timeout_config (Optional[dict[str, int]]): Global timeout configuration
            for FSM execution. Structure: {"global_timeout": seconds,
            "state_timeout": seconds, "operation_timeout": seconds}.

    Example:
        ```python
        # Order processing FSM subcontract
        order_fsm = ModelFSMSubcontract(
            state_definitions={
                "order_received": ModelFSMStateDefinition(
                    name="order_received",
                    description="Initial state when order is received",
                    allowed_operations=["validate_order", "check_inventory"],
                    timeout_seconds=30,
                    metadata={"requires_validation": True}
                ),
                "validating": ModelFSMStateDefinition(
                    name="validating",
                    description="Order validation in progress",
                    allowed_operations=["continue_validation", "cancel_order"],
                    timeout_seconds=60,
                    metadata={"validation_rules": ["customer", "payment", "inventory"]}
                ),
                "processing": ModelFSMStateDefinition(
                    name="processing",
                    description="Order processing and fulfillment",
                    allowed_operations=["process_payment", "allocate_inventory", "ship_order"],
                    timeout_seconds=300,
                    metadata={"processing_steps": 3}
                ),
                "completed": ModelFSMStateDefinition(
                    name="completed",
                    description="Order successfully completed",
                    allowed_operations=["generate_confirmation"],
                    metadata={"success": True}
                ),
                "cancelled": ModelFSMStateDefinition(
                    name="cancelled",
                    description="Order was cancelled",
                    allowed_operations=["cleanup_resources"],
                    metadata={"success": False}
                )
            },
            transitions=[
                ModelFSMStateTransition(
                    from_state="order_received",
                    to_state="validating",
                    condition=ModelFSMTransitionCondition(
                        condition_type="field_equals",
                        field_name="order_status",
                        expected_value="valid"
                    ),
                    action=ModelFSMTransitionAction(
                        action_type="log_transition",
                        parameters={"message": "Starting order validation"}
                    )
                ),
                ModelFSMStateTransition(
                    from_state="order_received",
                    to_state="cancelled",
                    condition=ModelFSMTransitionCondition(
                        condition_type="field_equals",
                        field_name="order_status",
                        expected_value="invalid"
                    ),
                    action=ModelFSMTransitionAction(
                        action_type="send_notification",
                        parameters={"type": "order_rejected"}
                    )
                ),
                ModelFSMStateTransition(
                    from_state="validating",
                    to_state="processing",
                    condition=ModelFSMTransitionCondition(
                        condition_type="all_validations_passed",
                        parameters={"required_validations": ["customer", "payment", "inventory"]}
                    )
                ),
                ModelFSMStateTransition(
                    from_state="processing",
                    to_state="completed",
                    condition=ModelFSMTransitionCondition(
                        condition_type="all_operations_completed",
                        parameters={"required_operations": ["payment", "inventory", "shipping"]}
                    )
                )
            ],
            initial_state="order_received",
            final_states=["completed", "cancelled"],
            operations=[
                ModelFSMOperation(
                    name="validate_order",
                    operation_type="validation",
                    parameters={"validation_schema": "order_schema_v2"},
                    timeout_seconds=30
                ),
                ModelFSMOperation(
                    name="process_payment",
                    operation_type="external_service_call",
                    parameters={"service": "payment_processor", "timeout": 60},
                    retry_config={"max_retries": 3, "backoff": "exponential"}
                )
            ],
            timeout_config={
                "global_timeout": 1800,  # 30 minutes
                "state_timeout": 300,    # 5 minutes per state
                "operation_timeout": 60  # 1 minute per operation
            }
        )

        # Data processing pipeline FSM
        pipeline_fsm = ModelFSMSubcontract(
            state_definitions={
                "data_ingestion": ModelFSMStateDefinition(
                    name="data_ingestion",
                    description="Ingesting data from sources",
                    allowed_operations=["ingest_from_api", "ingest_from_file"],
                    timeout_seconds=120
                ),
                "data_transformation": ModelFSMStateDefinition(
                    name="data_transformation",
                    description="Transforming and cleaning data",
                    allowed_operations=["clean_data", "transform_schema"],
                    timeout_seconds=180
                ),
                "data_validation": ModelFSMStateDefinition(
                    name="data_validation",
                    description="Validating processed data quality",
                    allowed_operations=["validate_schema", "check_quality"],
                    timeout_seconds=60
                ),
                "data_storage": ModelFSMStateDefinition(
                    name="data_storage",
                    description="Storing processed data",
                    allowed_operations=["store_to_database", "create_backup"],
                    timeout_seconds=90
                ),
                "pipeline_complete": ModelFSMStateDefinition(
                    name="pipeline_complete",
                    description="Data pipeline successfully completed",
                    allowed_operations=["send_completion_notification"]
                )
            },
            transitions=[
                ModelFSMStateTransition(
                    from_state="data_ingestion",
                    to_state="data_transformation",
                    condition=ModelFSMTransitionCondition(
                        condition_type="data_ingestion_complete"
                    )
                ),
                ModelFSMStateTransition(
                    from_state="data_transformation",
                    to_state="data_validation",
                    condition=ModelFSMTransitionCondition(
                        condition_type="transformation_complete"
                    )
                ),
                ModelFSMStateTransition(
                    from_state="data_validation",
                    to_state="data_storage",
                    condition=ModelFSMTransitionCondition(
                        condition_type="validation_passed"
                    )
                ),
                ModelFSMStateTransition(
                    from_state="data_storage",
                    to_state="pipeline_complete",
                    condition=ModelFSMTransitionCondition(
                        condition_type="storage_complete"
                    )
                )
            ],
            initial_state="data_ingestion",
            final_states=["pipeline_complete"]
        )
        ```

    State Management Rules:
        - All state names must be unique within the FSM
        - Transitions must reference existing states in state_definitions
        - Initial state must exist in state_definitions
        - All final states must exist in state_definitions
        - Circular transitions are allowed but should be carefully designed
        - Each state should have at least one outgoing transition (except final states)

    Validation Rules:
        - state_definitions must not be empty
        - initial_state must exist in state_definitions keys
        - All states in final_states must exist in state_definitions
        - All transition from_state and to_state values must exist in state_definitions
        - Operation names must be unique within the operations list
        - State names must follow naming conventions (lowercase, underscore-separated)

    Raises:
        ValidationError: If state definitions are invalid, transitions reference
            non-existent states, or initial/final states are not properly defined.
        StateDefinitionError: If state definitions contain contradictory or
            impossible configurations.
        TransitionValidationError: If state transitions create unreachable states
            or violate FSM principles.
        TimeoutConfigurationError: If timeout values are invalid or conflicting.

    Note:
        FSM subcontracts provide deterministic workflow processing with complete
        audit trails of state changes for compliance and debugging purposes.
        They integrate seamlessly with ORCHESTRATOR nodes and support complex
        workflow patterns including parallel processing and conditional branching.

        State transitions are atomic operations that maintain consistency even
        in distributed environments. Use correlation IDs to track FSM execution
        across multiple services and enable comprehensive monitoring.

        For optimal performance, design FSMs with clear terminal conditions and
        avoid deeply nested state hierarchies. Consider timeout configurations
        carefully to balance responsiveness with operational requirements.

        FSM execution state can be persisted and resumed, making them suitable
        for long-running workflows that span multiple system restarts or
        maintenance windows.
    """

    state_definitions: dict[str, ModelFSMStateDefinition]
    transitions: List[ModelFSMStateTransition]
    initial_state: str
    final_states: List[str]
    operations: List[ModelFSMOperation] = Field(default_factory=list)
    correlation_id: UUID = Field(default_factory=uuid4)
    timeout_config: Optional[dict[str, int]] = None

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True
    )
```

## TypedDict Docstring Templates

### TypedDictPerformanceMetricData Template

```
class TypedDictPerformanceMetricData(TypedDict):
    """
    Performance metric data structure for ONEX monitoring and analytics.

    Standardized format for collecting, transmitting, and storing performance
    metrics across all components of the ONEX Four-Node Architecture. Provides
    comprehensive metric metadata, contextual information, and correlation
    support for distributed system monitoring.

    This TypedDict enables consistent performance data collection from EFFECT,
    COMPUTE, REDUCER, and ORCHESTRATOR nodes, supporting both real-time
    monitoring and historical analysis with proper correlation tracking.

    Required Keys:
        metric_name (str): Unique name identifying the specific performance
            metric being measured. Should follow hierarchical naming convention
            (e.g., "node.compute.execution_time", "pipeline.throughput").
            Used for metric aggregation and dashboard visualization.
        value (Union[int, float]): Numeric value of the performance metric.
            Supports both integer counters and floating-point measurements.
            Must be finite and non-NaN for proper metric processing.
        timestamp (datetime): UTC timestamp when the metric was recorded.
            Should be as close to the actual measurement time as possible
            for accurate temporal analysis and correlation.
        component_id (UUID): Unique identifier of the component being measured.
            Links metrics to specific service instances, nodes, or processes
            for detailed performance analysis and troubleshooting.

    Optional Keys:
        unit (str): Unit of measurement for the metric value. Standard units
            include: "ms" (milliseconds), "s" (seconds), "bytes", "MB", "GB",
            "requests/sec", "ops/sec", "percent". Used for proper metric
            display and aggregation calculations.
        tags (dict[str, str]): Key-value pairs for metric categorization and
            filtering. Common tags: "environment", "service", "version",
            "node_type", "region". Enables flexible metric querying and
            dashboard filtering.
        context (dict[str, Any]): Additional contextual information relevant
            to the metric. May include request IDs, user IDs, operation types,
            error codes, or any other relevant metadata for metric analysis.

    Example:
        ```python
        # EFFECT node response time metric
        effect_metric: TypedDictPerformanceMetricData = {
            "metric_name": "node.effect.api_response_time",
            "value": 245.7,
            "timestamp": datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc),
            "component_id": UUID("12345678-1234-5678-9012-123456789abc"),
            "unit": "ms",
            "tags": {
                "environment": "production",
                "service": "user_service",
                "api_version": "v2",
                "node_type": "effect"
            },
            "context": {
                "correlation_id": "req_abc123",
                "user_id": "user_456",
                "endpoint": "/api/v2/users/profile",
                "http_method": "GET",
                "status_code": 200
            }
        }

        # COMPUTE node throughput metric
        compute_metric: TypedDictPerformanceMetricData = {
            "metric_name": "node.compute.records_processed_per_second",
            "value": 1250,
            "timestamp": datetime.now(UTC),
            "component_id": UUID("87654321-4321-8765-2109-876543210def"),
            "unit": "records/sec",
            "tags": {
                "environment": "production",
                "service": "data_processor",
                "algorithm": "machine_learning",
                "node_type": "compute"
            },
            "context": {
                "correlation_id": "batch_xyz789",
                "batch_size": 5000,
                "algorithm_version": "v1.2.3",
                "parallel_workers": 8
            }
        }

        # REDUCER node memory usage metric
        reducer_metric: TypedDictPerformanceMetricData = {
            "metric_name": "node.reducer.memory_utilization",
            "value": 78.5,
            "timestamp": datetime.now(UTC),
            "component_id": UUID("abcdef12-3456-7890-abcd-ef1234567890"),
            "unit": "percent",
            "tags": {
                "environment": "production",
                "service": "aggregation_service",
                "node_type": "reducer",
                "region": "us-east-1"
            },
            "context": {
                "correlation_id": "agg_pqr456",
                "total_memory_mb": 2048,
                "used_memory_mb": 1607,
                "aggregation_type": "streaming"
            }
        }

        # ORCHESTRATOR node workflow success rate
        orchestrator_metric: TypedDictPerformanceMetricData = {
            "metric_name": "node.orchestrator.workflow_success_rate",
            "value": 98.7,
            "timestamp": datetime.now(UTC),
            "component_id": UUID("fedcba09-8765-4321-fedc-ba0987654321"),
            "unit": "percent",
            "tags": {
                "environment": "production",
                "service": "workflow_orchestrator",
                "workflow_type": "order_processing",
                "node_type": "orchestrator"
            },
            "context": {
                "correlation_id": "workflow_stu123",
                "total_workflows": 1500,
                "successful_workflows": 1481,
                "time_window_minutes": 60
            }
        }
        ```

    Metric Categories and Naming Conventions:
        - Latency metrics: "*.response_time", "*.processing_time", "*.queue_time"
        - Throughput metrics: "*.requests_per_second", "*.records_processed"
        - Resource metrics: "*.cpu_usage", "*.memory_utilization", "*.disk_io"
        - Error metrics: "*.error_rate", "*.timeout_count", "*.retry_count"
        - Business metrics: "*.success_rate", "*.completion_rate"

    Validation Rules:
        - metric_name must be non-empty string following naming conventions
        - value must be finite number (not NaN or infinite)
        - timestamp must be valid datetime object
        - component_id must be valid UUID
        - unit should use standard measurement units if provided
        - tags keys and values must be non-empty strings
        - context values must be JSON-serializable

    Usage Guidelines:
        - Record metrics as close to the measurement point as possible
        - Use consistent metric naming across similar components
        - Include relevant tags for flexible querying and aggregation
        - Provide sufficient context for troubleshooting and analysis
        - Consider metric cardinality impact on storage and query performance

    Note:
        Performance metrics are automatically aggregated and analyzed by the
        ONEX monitoring system for system health monitoring, capacity planning,
        and performance optimization. They provide essential insights into
        Four-Node Architecture performance and enable proactive system
        management.

        Correlation IDs in context enable tracing performance metrics across
        the entire ONEX pipeline, supporting end-to-end performance analysis
        and bottleneck identification.

        For high-frequency metrics, consider batch collection and transmission
        to reduce overhead on the monitored components. Metric timestamps
        should reflect the actual measurement time, not the transmission time.
    """

    metric_name: str
    value: Union[int, float]
    timestamp: datetime
    component_id: UUID
    unit: NotRequired[str]
    tags: NotRequired[dict[str, str]]
    context: NotRequired[dict[str, Any]]
```

## Enum Docstring Templates

### EnumWorkflowCoordination Template

```
class EnumWorkflowCoordination(str, Enum):
    """
    Workflow coordination patterns for ORCHESTRATOR node execution strategies.

    Defines execution methodologies for coordinating multiple services,
    managing workflow complexity, and optimizing resource utilization
    within the ONEX Four-Node Architecture.

    These coordination patterns enable sophisticated workflow orchestration
    from simple sequential execution to complex hybrid patterns combining
    multiple coordination strategies for optimal performance and reliability.

    Values:
        SEQUENTIAL: Execute tasks one after another in strictly defined order.
            Provides predictable execution with minimal resource contention
            but may have longer total execution time. Best for workflows
            with strong dependencies or resource constraints.

        PARALLEL: Execute all eligible tasks simultaneously with maximum
            concurrency. Provides fastest execution time and optimal resource
            utilization but requires careful resource management. Best for
            independent tasks with sufficient system resources.

        PIPELINE: Execute tasks in overlapping pipeline stages where outputs
            from earlier stages feed into later stages continuously. Provides
            balanced throughput and resource utilization with steady-state
            performance. Best for streaming data processing workflows.

        CONDITIONAL: Execute tasks based on runtime conditions, dynamic
            decision trees, and contextual information. Enables adaptive
            workflows that respond to changing conditions. Best for complex
            business logic with multiple execution paths.

        EVENT_DRIVEN: Execute tasks in response to events, messages, and
            external triggers with loose coupling between components. Provides
            reactive processing and high scalability. Best for distributed
            systems with asynchronous communication patterns.

        HYBRID: Combine multiple coordination patterns within a single
            workflow to optimize different stages. Provides maximum flexibility
            and optimization opportunities but requires careful configuration.
            Best for complex workflows with varying requirements.

    Example:
        ```python
        # Sequential workflow for data processing
        sequential_config = ModelWorkflowConfig(
            coordination_type=EnumWorkflowCoordination.SEQUENTIAL,
            max_concurrent_tasks=1,
            timeout_seconds=3600,
            execution_order=["ingest", "transform", "validate", "store"]
        )

        # Parallel workflow for independent API calls
        parallel_config = ModelWorkflowConfig(
            coordination_type=EnumWorkflowCoordination.PARALLEL,
            max_concurrent_tasks=10,
            timeout_seconds=300,
            resource_allocation={
                "cpu_cores": 8,
                "memory_mb": 2048
            }
        )

        # Pipeline workflow for streaming data
        pipeline_config = ModelWorkflowConfig(
            coordination_type=EnumWorkflowCoordination.PIPELINE,
            pipeline_stages=[
                {"name": "ingestion", "buffer_size": 1000},
                {"name": "processing", "buffer_size": 500},
                {"name": "output", "buffer_size": 200}
            ],
            stage_timeout_seconds=60
        )

        # Event-driven workflow for microservices
        event_driven_config = ModelWorkflowConfig(
            coordination_type=EnumWorkflowCoordination.EVENT_DRIVEN,
            event_subscriptions=[
                "user.created",
                "order.completed",
                "payment.processed"
            ],
            event_timeout_seconds=30,
            dead_letter_queue_enabled=True
        )

        # Hybrid workflow combining patterns
        hybrid_config = ModelWorkflowConfig(
            coordination_type=EnumWorkflowCoordination.HYBRID,
            coordination_stages=[
                {
                    "stage": "data_collection",
                    "pattern": "parallel",
                    "max_concurrent": 5
                },
                {
                    "stage": "data_processing",
                    "pattern": "pipeline",
                    "stages": 3
                },
                {
                    "stage": "result_distribution",
                    "pattern": "event_driven",
                    "events": ["processing.complete"]
                }
            ]
        )
        ```

    Performance Characteristics:
        - SEQUENTIAL: Predictable resource usage, longer execution time,
          minimal coordination overhead, strong consistency guarantees
        - PARALLEL: Maximum throughput, higher resource usage, coordination
          overhead, potential resource contention
        - PIPELINE: Steady throughput, balanced resource usage, continuous
          processing, good for streaming scenarios
        - CONDITIONAL: Variable performance based on conditions, adaptive
          resource usage, complex coordination logic
        - EVENT_DRIVEN: High scalability, loose coupling, asynchronous
          processing, eventual consistency patterns
        - HYBRID: Optimized for specific requirements, maximum flexibility,
          complex configuration and monitoring requirements

    Selection Guidelines:
        - Use SEQUENTIAL for workflows with strict ordering requirements
          or limited resources
        - Use PARALLEL for independent tasks when maximum speed is required
        - Use PIPELINE for continuous data processing and streaming scenarios
        - Use CONDITIONAL for complex business logic with multiple paths
        - Use EVENT_DRIVEN for loosely coupled, scalable distributed systems
        - Use HYBRID for complex workflows requiring multiple optimization
          strategies

    Monitoring Considerations:
        - SEQUENTIAL: Monitor total execution time and bottleneck identification
        - PARALLEL: Monitor resource utilization and coordination overhead
        - PIPELINE: Monitor stage buffer levels and throughput rates
        - CONDITIONAL: Monitor decision path frequency and condition evaluation
        - EVENT_DRIVEN: Monitor event processing latency and queue depths
        - HYBRID: Monitor performance across all coordination patterns used

    Note:
        Coordination patterns directly impact system performance, resource
        utilization, and fault tolerance characteristics. Choose patterns
        based on specific workflow requirements, available resources, and
        operational constraints.

        For ONEX compliance, all coordination patterns must support proper
        correlation tracking, error handling, and monitoring integration.
        Consider fallback patterns for high-availability requirements.

        Hybrid patterns offer maximum flexibility but require careful design
        and comprehensive testing to ensure optimal performance across all
        coordination stages.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"
```

## Best Practices for Docstring Implementation

### 1. Consistency Standards
- Use identical formatting across all docstrings
- Follow Google-style docstring conventions
- Include all required sections for every public class/method
- Maintain consistent terminology and naming

### 2. Content Requirements
- Provide comprehensive attribute descriptions with types
- Include realistic, executable examples
- Document all possible exceptions and their conditions
- Explain validation rules and business constraints

### 3. Example Quality
- Use realistic data that demonstrates actual usage patterns
- Show both simple and complex configuration examples
- Include error handling examples where appropriate
- Demonstrate integration with other ONEX components

### 4. Validation Documentation
- Document all validation rules and constraints
- Explain the reasoning behind validation requirements
- Provide guidance on how to handle validation failures
- Include examples of valid and invalid configurations

### 5. ONEX Architecture Integration
- Explain how each component fits into the Four-Node pattern
- Document correlation ID usage and requirements
- Show integration examples with other ONEX components
- Include performance and monitoring considerations

---

*These docstring templates ensure zero tolerance for incomplete documentation and provide comprehensive coverage of all public interfaces introduced in PR #36.*
