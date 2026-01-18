> **Navigation**: [Home](../index.md) > Reference > API Documentation

# ONEX Contract Models API Documentation

## Overview

This document provides comprehensive API documentation for all contract models introduced in PR #36, following the ONEX Four-Node Architecture with zero tolerance for incomplete documentation.

## Table of Contents

- [Contract Model Architecture](#contract-model-architecture)
- [Core Contract Models](#core-contract-models)
- [Subcontract Models](#subcontract-models)
- [Configuration Models](#configuration-models)
- [Enums](#enums)
- [TypedDict Definitions](#typeddict-definitions)
- [Error Handling](#error-handling)
- [Migration Guide](#migration-guide)

## Contract Model Architecture

### ONEX Four-Node Pattern Implementation

All contract models follow the ONEX Four-Node Architecture:

```
EFFECT → COMPUTE → REDUCER → ORCHESTRATOR
```

#### Node Types and Responsibilities

1. **EFFECT Node**: External system interactions (APIs, databases, files)
2. **COMPUTE Node**: Data processing and transformation
3. **REDUCER Node**: State aggregation and management
4. **ORCHESTRATOR Node**: Workflow coordination and service orchestration

### One-Model-Per-File Convention

Following ONEX standards, each model is defined in its own file:
- File naming: `model_<name>.py`
- Class naming: `Model<Name>`
- No multiple models per file

## Core Contract Models

### ModelContractBase

**File**: `src/omnibase_core/models/contracts/model_contract_base.py`

```
class ModelContractBase(BaseModel):
    """
    Base class for all ONEX contract models.

    This class provides foundational contract functionality including:
    - UUID-based correlation tracking
    - ONEX compliance validation
    - Standard configuration patterns
    - Error handling integration

    Attributes:
        correlation_id (UUID): Unique identifier for request/response correlation
        created_at (datetime): Timestamp when the contract was created
        updated_at (Optional[datetime]): Timestamp of last modification

    Example:
        ```python
        class MyContract(ModelContractBase):
            name: str
            config: dict[str, Any]

            def validate_contract(self) -> bool:
                return self.name and bool(self.config)
        ```

    Note:
        All contract models must inherit from this base class to ensure
        ONEX architectural compliance and proper correlation tracking.
    """

    correlation_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True
    )
```

### ModelContractCompute

**File**: `src/omnibase_core/models/contracts/model_contract_compute.py`

```
class ModelContractCompute(ModelContractBase):
    """
    Contract model for COMPUTE node operations.

    Defines computational processing contracts including data transformation,
    algorithm execution, and processing pipeline configuration.

    Attributes:
        algorithm_config (ModelAlgorithmConfig): Algorithm execution configuration
        input_validation (ModelInputValidationConfig): Input data validation rules
        output_transformation (ModelOutputTransformationConfig): Output formatting rules
        performance_requirements (ModelPerformanceRequirements): Performance constraints
        parallel_config (Optional[ModelParallelConfig]): Parallel execution settings

    Example:
        ```python
        compute_contract = ModelContractCompute(
            correlation_id=uuid4(),
            algorithm_config=ModelAlgorithmConfig(
                algorithm_type="machine_learning",
                parameters={"model_path": "/path/to/model"}
            ),
            input_validation=ModelInputValidationConfig(
                required_fields=["data", "metadata"],
                data_types={"data": "array", "metadata": "dict"}
            ),
            performance_requirements=ModelPerformanceRequirements(
                max_execution_time=30.0,
                memory_limit_mb=512
            )
        )
        ```

    Raises:
        ValidationError: If configuration is invalid or incompatible
        ModelOnexError: If ONEX compliance requirements are not met

    Note:
        COMPUTE contracts must define clear input/output specifications
        and performance boundaries for proper ONEX node coordination.
    """

    algorithm_config: ModelAlgorithmConfig
    input_validation: ModelInputValidationConfig
    output_transformation: ModelOutputTransformationConfig
    performance_requirements: ModelPerformanceRequirements
    parallel_config: Optional[ModelParallelConfig] = None
```

### ModelContractEffect

**File**: `src/omnibase_core/models/contracts/model_contract_effect.py`

```
class ModelContractEffect(ModelContractBase):
    """
    Contract model for EFFECT node operations.

    Defines external system interaction contracts including API calls,
    database operations, file system access, and third-party integrations.

    Attributes:
        external_service_config (ModelExternalServiceConfig): External service connection settings
        io_operation_config (ModelIOOperationConfig): I/O operation configuration
        retry_config (ModelEffectRetryConfig): Retry and error handling configuration
        caching_config (Optional[ModelCachingConfig]): Response caching settings
        validation_rules (ModelValidationRules): Data validation requirements

    Example:
        ```python
        effect_contract = ModelContractEffect(
            correlation_id=uuid4(),
            external_service_config=ModelExternalServiceConfig(
                service_url="https://api.example.com",
                authentication_method="bearer_token",
                timeout_seconds=30
            ),
            io_operation_config=ModelIOOperationConfig(
                operation_type="http_request",
                retry_attempts=3,
                batch_size=100
            ),
            retry_config=ModelEffectRetryConfig(
                max_retries=3,
                backoff_strategy="exponential",
                retry_conditions=["timeout", "server_error"]
            )
        )
        ```

    Raises:
        ConnectionError: If external service configuration is invalid
        ValidationError: If contract parameters are incompatible
        ModelOnexError: If ONEX effect node requirements are not satisfied

    Note:
        EFFECT contracts must handle all external dependencies gracefully
        and provide clear failure modes for upstream error handling.
    """

    external_service_config: ModelExternalServiceConfig
    io_operation_config: ModelIOOperationConfig
    retry_config: ModelEffectRetryConfig
    caching_config: Optional[ModelCachingConfig] = None
    validation_rules: ModelValidationRules
```

### ModelContractReducer

**File**: `src/omnibase_core/models/contracts/model_contract_reducer.py`

```
class ModelContractReducer(ModelContractBase):
    """
    Contract model for REDUCER node operations.

    Defines state aggregation and reduction contracts including data consolidation,
    state management, and result aggregation patterns.

    Attributes:
        reduction_config (ModelReductionConfig): Data reduction configuration
        memory_management (ModelMemoryManagementConfig): Memory usage optimization
        streaming_config (Optional[ModelStreamingConfig]): Streaming data handling
        transaction_config (Optional[ModelTransactionConfig]): Transaction management
        backup_config (Optional[ModelBackupConfig]): State backup configuration

    Example:
        ```python
        reducer_contract = ModelContractReducer(
            correlation_id=uuid4(),
            reduction_config=ModelReductionConfig(
                aggregation_method="sum",
                grouping_fields=["category", "timestamp"],
                output_format="json"
            ),
            memory_management=ModelMemoryManagementConfig(
                buffer_size_mb=256,
                garbage_collection_threshold=0.8,
                compression_enabled=True
            ),
            streaming_config=ModelStreamingConfig(
                chunk_size=1000,
                processing_mode="batch"
            )
        )
        ```

    Raises:
        MemoryError: If memory management configuration exceeds system limits
        ValidationError: If reduction parameters are invalid
        ModelOnexError: If ONEX reducer requirements are not met

    Note:
        REDUCER contracts must ensure proper state management and provide
        rollback capabilities for transaction-based operations.
    """

    reduction_config: ModelReductionConfig
    memory_management: ModelMemoryManagementConfig
    streaming_config: Optional[ModelStreamingConfig] = None
    transaction_config: Optional[ModelTransactionConfig] = None
    backup_config: Optional[ModelBackupConfig] = None
```

### ModelContractOrchestrator

**File**: `src/omnibase_core/models/contracts/model_contract_orchestrator.py`

```
class ModelContractOrchestrator(ModelContractBase):
    """
    Contract model for ORCHESTRATOR node operations.

    Defines workflow coordination contracts including service orchestration,
    dependency management, and execution flow control.

    Attributes:
        workflow_config (ModelWorkflowConfig): Workflow execution configuration
        event_coordination (ModelEventCoordinationConfig): Event handling setup
        dependency_resolution (List[ModelDependency]): Service dependency definitions
        lifecycle_config (ModelLifecycleConfig): Component lifecycle management
        conflict_resolution (ModelConflictResolutionConfig): Conflict handling rules

    Example:
        ```python
        orchestrator_contract = ModelContractOrchestrator(
            correlation_id=uuid4(),
            workflow_config=ModelWorkflowConfig(
                execution_mode="sequential",
                max_parallel_tasks=5,
                timeout_seconds=300
            ),
            event_coordination=ModelEventCoordinationConfig(
                event_bus_type="redis",
                subscription_topics=["task.completed", "error.occurred"]
            ),
            dependency_resolution=[
                ModelDependency(
                    service_name="data_processor",
                    dependency_type=EnumDependencyType.REQUIRED,
                    version_constraint=">=1.0.0"
                )
            ]
        )
        ```

    Raises:
        DependencyError: If required dependencies are not available
        ValidationError: If orchestration parameters are invalid
        ModelOnexError: If ONEX orchestrator requirements are not satisfied

    Note:
        ORCHESTRATOR contracts must define clear execution order and
        provide comprehensive error handling for all coordinated services.
    """

    workflow_config: ModelWorkflowConfig
    event_coordination: ModelEventCoordinationConfig
    dependency_resolution: List[ModelDependency]
    lifecycle_config: ModelLifecycleConfig
    conflict_resolution: ModelConflictResolutionConfig
```

## Configuration Models

### ModelAlgorithmConfig

**File**: `src/omnibase_core/models/contracts/model_algorithm_config.py`

```
class ModelAlgorithmConfig(BaseModel):
    """
    Configuration for algorithm execution in COMPUTE nodes.

    Defines algorithm-specific parameters, execution modes, and performance
    optimization settings for computational processing.

    Attributes:
        algorithm_type (str): Type of algorithm to execute (e.g., "machine_learning", "statistical")
        parameters (dict[str, Any]): Algorithm-specific parameters
        optimization_level (str): Performance optimization level ("low", "medium", "high")
        factor_config (Optional[ModelAlgorithmFactorConfig]): Advanced factor configuration
        performance_monitoring (bool): Whether to collect performance metrics

    Example:
        ```python
        config = ModelAlgorithmConfig(
            algorithm_type="neural_network",
            parameters={
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs": 100
            },
            optimization_level="high",
            performance_monitoring=True
        )
        ```

    Validation Rules:
        - algorithm_type must be a recognized algorithm identifier
        - parameters must contain required keys for the specified algorithm type
        - optimization_level must be one of: "low", "medium", "high"

    Note:
        Algorithm configurations are validated against a registry of supported
        algorithms to ensure compatibility with the COMPUTE node infrastructure.
    """

    algorithm_type: str
    parameters: dict[str, Any]
    optimization_level: str = "medium"
    factor_config: Optional[ModelAlgorithmFactorConfig] = None
    performance_monitoring: bool = False

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True
    )

    @field_validator("optimization_level")
    @classmethod
    def validate_optimization_level(cls, v: str) -> str:
        """Validate optimization level is supported."""
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"optimization_level must be one of {allowed}")
        return v

    @field_validator("algorithm_type")
    @classmethod
    def validate_algorithm_type(cls, v: str) -> str:
        """Validate algorithm type is recognized."""
        # This would validate against a registry in practice
        if not v or not isinstance(v, str):
            raise ValueError("algorithm_type must be a non-empty string")
        return v.lower()
```

### ModelValidationRules

**File**: `src/omnibase_core/models/contracts/model_validation_rules.py`

```
class ModelValidationRules(BaseModel):
    """
    Comprehensive validation rules for data processing contracts.

    Defines validation constraints, data quality requirements, and
    compliance checks for contract execution.

    Attributes:
        required_fields (List[str]): Fields that must be present in input data
        field_types (dict[str, str]): Expected data types for each field
        value_constraints (dict[str, Any]): Value range and format constraints
        custom_validators (List[str]): Custom validation function names
        strict_mode (bool): Whether to enforce strict validation

    Example:
        ```python
        rules = ModelValidationRules(
            required_fields=["user_id", "timestamp", "data"],
            field_types={
                "user_id": "uuid",
                "timestamp": "datetime",
                "data": "dict"
            },
            value_constraints={
                "user_id": {"format": "uuid4"},
                "timestamp": {"min": "2023-01-01", "max": "2025-12-31"},
                "data": {"min_keys": 1, "max_keys": 100}
            },
            strict_mode=True
        )
        ```

    Validation Process:
        1. Check required fields presence
        2. Validate field data types
        3. Apply value constraints
        4. Execute custom validators
        5. Generate validation report

    Note:
        Validation rules are applied at contract execution time and
        can be dynamically modified based on operational requirements.
    """

    required_fields: List[str]
    field_types: dict[str, str] = Field(default_factory=dict)
    value_constraints: dict[str, Any] = Field(default_factory=dict)
    custom_validators: List[str] = Field(default_factory=list)
    strict_mode: bool = True

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True
    )

    def validate_data(self, data: dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate data against defined rules.

        Args:
            data: Data dictionary to validate

        Returns:
            Tuple of (is_valid, error_messages)

        Example:
            ```python
            rules = ModelValidationRules(required_fields=["id", "name"])
            is_valid, errors = rules.validate_data({"id": "123", "name": "test"})
            ```
        """
        errors = []

        # Check required fields
        for field in self.required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate field types
        for field, expected_type in self.field_types.items():
            if field in data:
                if not self._validate_type(data[field], expected_type):
                    errors.append(f"Invalid type for {field}: expected {expected_type}")

        # Apply value constraints
        for field, constraints in self.value_constraints.items():
            if field in data:
                constraint_errors = self._validate_constraints(data[field], constraints, field)
                errors.extend(constraint_errors)

        return len(errors) == 0, errors

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value matches expected type."""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "uuid": (str, UUID),
            "datetime": datetime
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, skip validation

        return isinstance(value, expected)

    def _validate_constraints(self, value: Any, constraints: dict[str, Any], field_name: str) -> List[str]:
        """Validate value against constraints."""
        errors = []

        if "min" in constraints and value < constraints["min"]:
            errors.append(f"{field_name} below minimum value {constraints['min']}")

        if "max" in constraints and value > constraints["max"]:
            errors.append(f"{field_name} above maximum value {constraints['max']}")

        if "format" in constraints and isinstance(value, str):
            if constraints["format"] == "uuid4" and not self._is_valid_uuid(value):
                errors.append(f"{field_name} is not a valid UUID")

        return errors

    def _is_valid_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            UUID(value)
            return True
        except ValueError:
            return False
```

## Subcontract Models

### ModelAggregationSubcontract

**File**: `src/omnibase_core/models/contracts/subcontracts/model_aggregation_subcontract.py`

```
class ModelAggregationSubcontract(BaseModel):
    """
    Subcontract for data aggregation operations.

    Defines aggregation patterns, data grouping strategies, and performance
    optimization for large-scale data consolidation operations.

    Attributes:
        aggregation_functions (List[ModelAggregationFunction]): Aggregation operations to perform
        data_grouping (ModelDataGrouping): Data grouping configuration
        performance_config (ModelAggregationPerformance): Performance optimization settings
        circuit_breaker (Optional[ModelCircuitBreaker]): Circuit breaker for fault tolerance
        correlation_id (UUID): Request correlation identifier

    Example:
        ```python
        subcontract = ModelAggregationSubcontract(
            aggregation_functions=[
                ModelAggregationFunction(
                    function_type="sum",
                    field_name="revenue",
                    output_name="total_revenue"
                ),
                ModelAggregationFunction(
                    function_type="avg",
                    field_name="rating",
                    output_name="average_rating"
                )
            ],
            data_grouping=ModelDataGrouping(
                group_by_fields=["category", "region"],
                sort_order="asc"
            ),
            performance_config=ModelAggregationPerformance(
                batch_size=1000,
                parallel_workers=4,
                memory_limit_mb=512
            )
        )
        ```

    Performance Considerations:
        - Batch size should be tuned based on available memory
        - Parallel workers should not exceed CPU core count
        - Circuit breaker prevents cascading failures in high-load scenarios

    Note:
        Aggregation subcontracts are optimized for streaming data processing
        and can handle real-time updates to aggregation results.
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

### ModelFSMSubcontract

**File**: `src/omnibase_core/models/contracts/subcontracts/model_fsm_subcontract.py`

```
class ModelFSMSubcontract(BaseModel):
    """
    Finite State Machine (FSM) subcontract for state-based processing.

    Defines state transitions, conditions, and actions for complex workflow
    management with deterministic state progression.

    Attributes:
        state_definitions (dict[str, ModelFSMStateDefinition]): Available states and their properties
        transitions (List[ModelFSMStateTransition]): Valid state transitions
        initial_state (str): Starting state for the FSM
        final_states (List[str]): Terminal states that end processing
        operations (List[ModelFSMOperation]): Operations available in each state
        correlation_id (UUID): Request correlation identifier

    Example:
        ```python
        fsm_contract = ModelFSMSubcontract(
            state_definitions={
                "initial": ModelFSMStateDefinition(
                    name="initial",
                    description="Starting state",
                    allowed_operations=["validate_input"]
                ),
                "processing": ModelFSMStateDefinition(
                    name="processing",
                    description="Data processing state",
                    allowed_operations=["process_data", "check_progress"]
                ),
                "completed": ModelFSMStateDefinition(
                    name="completed",
                    description="Final successful state",
                    allowed_operations=["generate_report"]
                )
            },
            transitions=[
                ModelFSMStateTransition(
                    from_state="initial",
                    to_state="processing",
                    condition=ModelFSMTransitionCondition(
                        condition_type="data_valid",
                        parameters={"required_fields": ["input_data"]}
                    ),
                    action=ModelFSMTransitionAction(
                        action_type="log_transition",
                        parameters={"message": "Starting processing"}
                    )
                )
            ],
            initial_state="initial",
            final_states=["completed", "failed"]
        )
        ```

    State Management Rules:
        - All transitions must be explicitly defined
        - States must have unique names within the FSM
        - Circular references are allowed but should be carefully managed
        - Final states cannot have outgoing transitions

    Note:
        FSM subcontracts provide deterministic processing with full audit
        trails of state changes for compliance and debugging purposes.
    """

    state_definitions: dict[str, ModelFSMStateDefinition]
    transitions: List[ModelFSMStateTransition]
    initial_state: str
    final_states: List[str]
    operations: List[ModelFSMOperation] = Field(default_factory=list)
    correlation_id: UUID = Field(default_factory=uuid4)

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True
    )

    @field_validator("initial_state")
    @classmethod
    def validate_initial_state(cls, v: str, info: ValidationInfo) -> str:
        """Ensure initial state exists in state definitions."""
        if hasattr(info, 'data') and 'state_definitions' in info.data:
            if v not in info.data['state_definitions']:
                raise ValueError(f"Initial state '{v}' not found in state_definitions")
        return v

    @field_validator("final_states")
    @classmethod
    def validate_final_states(cls, v: List[str], info: ValidationInfo) -> List[str]:
        """Ensure all final states exist in state definitions."""
        if hasattr(info, 'data') and 'state_definitions' in info.data:
            state_defs = info.data['state_definitions']
            for state in v:
                if state not in state_defs:
                    raise ValueError(f"Final state '{state}' not found in state_definitions")
        return v

    def validate_transitions(self) -> List[str]:
        """
        Validate all transitions reference valid states.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        for transition in self.transitions:
            if transition.from_state not in self.state_definitions:
                errors.append(f"Transition from unknown state: {transition.from_state}")
            if transition.to_state not in self.state_definitions:
                errors.append(f"Transition to unknown state: {transition.to_state}")

        return errors
```

## Enums

### EnumDependencyType

**File**: `src/omnibase_core/enums/enum_dependency_type.py`

```
class EnumDependencyType(str, Enum):
    """
    Types of dependencies between services and components.

    Defines the relationship strength and behavior for service dependencies
    in the ONEX architecture.

    Values:
        REQUIRED: Dependency must be available for service to function
        OPTIONAL: Dependency enhances functionality but is not required
        PREFERRED: Service can function without but performance may be degraded

    Example:
        ```python
        dependency = ModelDependency(
            service_name="database_service",
            dependency_type=EnumDependencyType.REQUIRED,
            version_constraint=">=2.0.0"
        )
        ```

    Usage Guidelines:
        - Use REQUIRED for critical dependencies (databases, message queues)
        - Use OPTIONAL for features like caching or monitoring
        - Use PREFERRED for performance optimizations
    """

    REQUIRED = "required"
    OPTIONAL = "optional"
    PREFERRED = "preferred"
```

### EnumWorkflowCoordination

**File**: `src/omnibase_core/enums/enum_workflow_coordination.py`

```
class EnumWorkflowCoordination(str, Enum):
    """
    Workflow coordination patterns for orchestrator nodes.

    Defines execution strategies for coordinating multiple services
    and managing workflow complexity.

    Values:
        SEQUENTIAL: Execute tasks one after another in order
        PARALLEL: Execute all tasks simultaneously
        PIPELINE: Execute tasks in overlapping pipeline stages
        CONDITIONAL: Execute tasks based on runtime conditions
        EVENT_DRIVEN: Execute tasks in response to events
        HYBRID: Combine multiple coordination patterns

    Example:
        ```python
        workflow_config = ModelWorkflowConfig(
            coordination_type=EnumWorkflowCoordination.PIPELINE,
            max_concurrent_tasks=5,
            timeout_seconds=300
        )
        ```

    Performance Characteristics:
        - SEQUENTIAL: Predictable, lower resource usage
        - PARALLEL: Fastest execution, higher resource usage
        - PIPELINE: Balanced throughput and resource utilization
        - CONDITIONAL: Dynamic execution based on runtime state
        - EVENT_DRIVEN: Reactive processing with loose coupling
        - HYBRID: Maximum flexibility, requires careful configuration
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"
```

## TypedDict Definitions

### TypedDictCapabilityFactoryKwargs

**File**: `src/omnibase_core/types/typed_dict_capability_factory_kwargs.py`

```
class TypedDictCapabilityFactoryKwargs(TypedDict):
    """
    Keyword arguments for capability factory instantiation.

    Defines the required and optional parameters for creating capability
    instances in the ONEX dependency injection system.

    Required Keys:
        capability_type (str): Type identifier for the capability
        configuration (dict[str, Any]): Capability-specific configuration

    Optional Keys:
        priority (int): Execution priority (default: 0)
        tags (List[str]): Capability tags for categorization
        metadata (dict[str, Any]): Additional capability metadata

    Example:
        ```python
        factory_kwargs: TypedDictCapabilityFactoryKwargs = {
            "capability_type": "data_processor",
            "configuration": {
                "batch_size": 100,
                "timeout": 30
            },
            "priority": 10,
            "tags": ["processor", "batch"],
            "metadata": {"version": "1.0.0"}
        }
        ```

    Validation Rules:
        - capability_type must be a registered capability identifier
        - configuration must contain required keys for the capability type
        - priority must be between -100 and 100

    Note:
        TypedDict definitions provide static type checking while maintaining
        runtime flexibility for dynamic capability creation.
    """

    capability_type: str
    configuration: dict[str, Any]
    priority: NotRequired[int]
    tags: NotRequired[List[str]]
    metadata: NotRequired[dict[str, Any]]
```

### TypedDictPerformanceMetricData

**File**: `src/omnibase_core/types/typed_dict_performance_metric_data.py`

```
class TypedDictPerformanceMetricData(TypedDict):
    """
    Performance metric data structure for monitoring and analytics.

    Standardized format for collecting and reporting performance metrics
    across all ONEX components.

    Required Keys:
        metric_name (str): Name of the performance metric
        value (Union[int, float]): Metric value
        timestamp (datetime): When the metric was recorded
        component_id (UUID): Identifier of the component being measured

    Optional Keys:
        unit (str): Unit of measurement (e.g., "ms", "bytes", "requests/sec")
        tags (dict[str, str]): Metric tags for categorization and filtering
        context (dict[str, Any]): Additional context information

    Example:
        ```python
        metric_data: TypedDictPerformanceMetricData = {
            "metric_name": "response_time",
            "value": 245.7,
            "timestamp": datetime.now(UTC),
            "component_id": UUID("12345678-1234-5678-9012-123456789abc"),
            "unit": "ms",
            "tags": {
                "environment": "production",
                "service": "api_gateway"
            },
            "context": {
                "request_id": "req_abc123",
                "user_id": "user_456"
            }
        }
        ```

    Metric Categories:
        - Latency metrics: response_time, processing_time, queue_time
        - Throughput metrics: requests_per_second, bytes_per_second
        - Resource metrics: cpu_usage, memory_usage, disk_io
        - Error metrics: error_rate, timeout_rate, retry_count

    Note:
        Performance metrics are automatically aggregated and analyzed
        for system health monitoring and capacity planning.
    """

    metric_name: str
    value: Union[int, float]
    timestamp: datetime
    component_id: UUID
    unit: NotRequired[str]
    tags: NotRequired[dict[str, str]]
    context: NotRequired[dict[str, Any]]
```

## Error Handling

### ONEX Error Patterns

All contract models follow standardized error handling patterns:

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError

class ContractValidationError(ModelOnexError):
    """Contract-specific validation error."""
    pass

class ConfigurationError(ModelOnexError):
    """Configuration-related error."""
    pass
```

### Error Context

All errors include rich context information:

```
try:
    contract.validate()
except ValidationError as e:
    raise ContractValidationError(
        message="Contract validation failed",
        correlation_id=contract.correlation_id,
        error_context={
            "contract_type": type(contract).__name__,
            "validation_errors": e.errors(),
            "timestamp": datetime.now(UTC)
        }
    ) from e
```

## Migration Guide

### From Legacy Contracts

1. **Update Base Class**:
   ```python
   # Old
   class MyContract(BaseModel):
       pass

   # New
   class MyContract(ModelContractBase):
       correlation_id: UUID = Field(default_factory=uuid4)
   ```

2. **Add Required Fields**:
   ```python
   from datetime import UTC, datetime
   # Add correlation tracking
   correlation_id: UUID
   created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
   ```

3. **Update Configuration**:
   ```python
   # Old
   class Config:
       extra = "forbid"

   # New
   model_config = ConfigDict(
       extra="forbid",
       validate_assignment=True,
       use_enum_values=True
   )
   ```

### TypedDict Migration

TypedDict classes moved from `models/` to `types/` directory:

```
# Old import
from omnibase_core.models.some_typed_dict import SomeTypedDict

# New import
from omnibase_core.types.typed_dict_some_typed_dict import TypedDictSomeTypedDict
```

### Enum Migration

Enums moved to dedicated `enums/` directory:

```
# Old import
from omnibase_core.models.enums import SomeEnum

# New import
from omnibase_core.enums.enum_some_enum import EnumSomeEnum
```

## Best Practices

### 1. Documentation Standards
- Every class must have comprehensive docstrings
- Include parameter descriptions, return values, and examples
- Document validation rules and constraints
- Provide usage examples for complex configurations

### 2. Type Safety
- Use specific types instead of `Any` when possible
- Leverage Union types for multiple valid types
- Use Optional for nullable fields
- Implement custom validators for complex constraints

### 3. Error Handling
- Always inherit from `ModelOnexError` for custom exceptions
- Include correlation IDs in error contexts
- Provide clear error messages with actionable guidance
- Chain exceptions to preserve error context

### 4. Performance
- Use appropriate field defaults to avoid unnecessary computations
- Implement lazy loading for expensive operations
- Consider memory usage in large data structures
- Profile performance-critical paths

### 5. Maintainability
- Follow one-model-per-file convention
- Use descriptive naming for all components
- Maintain backward compatibility when possible
- Document breaking changes clearly

---

*This documentation follows the zero-tolerance standard for completeness and provides comprehensive coverage of all public interfaces in PR #36.*
