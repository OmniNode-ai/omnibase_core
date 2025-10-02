# ONEX Four-Node Architecture Documentation

## Overview

The ONEX Four-Node Architecture is a foundational design pattern that provides structured, scalable, and maintainable microservice organization. Each node has specific responsibilities within the processing pipeline, enabling clear separation of concerns and optimal system performance.

## Architecture Pattern

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EFFECT    │───▶│   COMPUTE   │───▶│   REDUCER   │───▶│ORCHESTRATOR │
│   (Input)   │    │ (Process)   │    │(Aggregate)  │    │(Coordinate) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Data Flow Direction

The ONEX pattern enforces unidirectional data flow from left to right:
- **EFFECT** → **COMPUTE** → **REDUCER** → **ORCHESTRATOR**
- No backwards dependencies allowed
- Clear input/output contracts between nodes
- Deterministic processing pipeline

## Node Types and Responsibilities

### 1. EFFECT Node

**Primary Responsibility**: External system interactions and side effects

**Key Functions**:
- API calls to external services
- Database read/write operations
- File system operations
- Message queue interactions
- Third-party service integrations

**Design Principles**:
- Handle all external dependencies
- Implement retry logic and circuit breakers
- Provide idempotent operations where possible
- Maintain connection pooling and resource management
- Log all external interactions for audit trails

**Implementation Example**:

```python
from omnibase_core.core.infrastructure_service_bases import NodeEffectService
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect

class DatabaseEffectService(NodeEffectService):
    """
    EFFECT node for database operations.

    Handles all database interactions with proper connection management,
    retry logic, and error handling.
    """

    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.db_pool = container.get_service("ProtocolDatabasePool")
        self.logger = container.get_service("ProtocolLogger")

    async def execute_effect(self, contract: ModelContractEffect) -> ModelEffectOutput:
        """
        Execute database operation based on contract specification.

        Args:
            contract: Effect contract with operation details

        Returns:
            ModelEffectOutput: Operation results with metadata

        Raises:
            DatabaseConnectionError: If database is unreachable
            OnexError: If contract validation fails
        """
        try:
            # Validate contract
            if not self._validate_database_contract(contract):
                raise OnexError("Invalid database contract")

            # Execute database operation with retry logic
            result = await self._execute_with_retry(contract)

            # Log successful operation
            self.logger.info(f"Database operation completed",
                           correlation_id=contract.correlation_id)

            return ModelEffectOutput(
                correlation_id=contract.correlation_id,
                operation_result=result,
                metadata=self._generate_metadata(contract)
            )

        except Exception as e:
            self.logger.error(f"Database operation failed: {e}",
                            correlation_id=contract.correlation_id)
            raise OnexError("Database operation failed") from e

    async def _execute_with_retry(self, contract: ModelContractEffect):
        """Execute operation with exponential backoff retry."""
        for attempt in range(contract.retry_config.max_retries):
            try:
                async with self.db_pool.acquire() as conn:
                    return await self._perform_operation(conn, contract)
            except TemporaryDatabaseError as e:
                if attempt == contract.retry_config.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    def _validate_database_contract(self, contract: ModelContractEffect) -> bool:
        """Validate contract has required database operation parameters."""
        required_params = ["query", "parameters"]
        return all(param in contract.io_operation_config.parameters
                  for param in required_params)
```

**Best Practices**:
- Always include correlation IDs in external calls
- Implement comprehensive error handling and recovery
- Use connection pooling for database operations
- Cache responses when appropriate
- Monitor external service health and availability

### 2. COMPUTE Node

**Primary Responsibility**: Data processing and computational operations

**Key Functions**:
- Data transformation and manipulation
- Algorithm execution
- Business logic processing
- Validation and normalization
- Statistical computations

**Design Principles**:
- Pure functions where possible (no side effects)
- Optimized for CPU-intensive operations
- Scalable through parallel processing
- Memory-efficient processing patterns
- Comprehensive input validation

**Implementation Example**:

```python
from omnibase_core.core.infrastructure_service_bases import NodeComputeService
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute

class DataTransformationComputeService(NodeComputeService):
    """
    COMPUTE node for data transformation operations.

    Processes input data according to algorithm specifications with
    optimized performance and parallel execution support.
    """

    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.algorithm_registry = container.get_service("ProtocolAlgorithmRegistry")
        self.performance_monitor = container.get_service("ProtocolPerformanceMonitor")

    async def execute_compute(self, contract: ModelContractCompute) -> ModelComputeOutput:
        """
        Execute computational processing based on contract specification.

        Args:
            contract: Compute contract with algorithm and data specifications

        Returns:
            ModelComputeOutput: Processed data with performance metrics

        Raises:
            AlgorithmNotFoundError: If specified algorithm is not available
            ValidationError: If input data validation fails
            OnexError: If computation fails
        """
        start_time = time.time()

        try:
            # Validate input data
            self._validate_input_data(contract)

            # Get algorithm implementation
            algorithm = self.algorithm_registry.get_algorithm(
                contract.algorithm_config.algorithm_type
            )

            # Configure parallel processing if specified
            if contract.parallel_config:
                result = await self._execute_parallel(algorithm, contract)
            else:
                result = await self._execute_sequential(algorithm, contract)

            # Apply output transformation
            transformed_result = self._transform_output(result, contract)

            # Record performance metrics
            execution_time = time.time() - start_time
            self._record_performance_metrics(contract, execution_time)

            return ModelComputeOutput(
                correlation_id=contract.correlation_id,
                processed_data=transformed_result,
                performance_metrics={
                    "execution_time": execution_time,
                    "data_size": len(transformed_result),
                    "algorithm_type": contract.algorithm_config.algorithm_type
                }
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.performance_monitor.record_error(contract.correlation_id, e, execution_time)
            raise OnexError("Computation failed") from e

    async def _execute_parallel(self, algorithm, contract: ModelContractCompute):
        """Execute algorithm with parallel processing."""
        parallel_config = contract.parallel_config
        chunk_size = len(contract.input_data) // parallel_config.worker_count

        tasks = []
        for i in range(parallel_config.worker_count):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < parallel_config.worker_count - 1 else len(contract.input_data)
            chunk = contract.input_data[start_idx:end_idx]

            task = asyncio.create_task(algorithm.process_chunk(chunk))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return self._merge_parallel_results(results, parallel_config)

    def _validate_input_data(self, contract: ModelContractCompute):
        """Validate input data against contract validation rules."""
        validation_config = contract.input_validation

        # Check required fields
        for field in validation_config.required_fields:
            if field not in contract.input_data:
                raise ValidationError(f"Missing required field: {field}")

        # Validate data types
        for field, expected_type in validation_config.data_types.items():
            if field in contract.input_data:
                actual_value = contract.input_data[field]
                if not isinstance(actual_value, self._get_python_type(expected_type)):
                    raise ValidationError(
                        f"Field {field} has incorrect type. Expected {expected_type}, "
                        f"got {type(actual_value).__name__}"
                    )

    def _transform_output(self, data, contract: ModelContractCompute):
        """Apply output transformation based on contract specifications."""
        transform_config = contract.output_transformation

        if transform_config.format == "json":
            return json.dumps(data, default=str)
        elif transform_config.format == "dataframe":
            return pd.DataFrame(data)
        elif transform_config.format == "array":
            return list(data)
        else:
            return data  # No transformation needed
```

**Best Practices**:
- Implement comprehensive input validation
- Use appropriate data structures for performance
- Consider memory usage for large datasets
- Implement progress tracking for long-running operations
- Provide detailed performance metrics

### 3. REDUCER Node

**Primary Responsibility**: State aggregation and data consolidation

**Key Functions**:
- Data aggregation and summarization
- State management and persistence
- Result consolidation from multiple sources
- Incremental processing support
- Transaction management

**Design Principles**:
- Maintain consistent state across operations
- Support both batch and streaming processing
- Implement proper transaction boundaries
- Optimize for memory efficiency
- Provide rollback capabilities

**Implementation Example**:

```python
from omnibase_core.core.infrastructure_service_bases import NodeReducerService
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

class DataAggregationReducerService(NodeReducerService):
    """
    REDUCER node for data aggregation and state management.

    Consolidates processed data into aggregated results with support
    for streaming updates and transactional consistency.
    """

    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.state_manager = container.get_service("ProtocolStateManager")
        self.transaction_manager = container.get_service("ProtocolTransactionManager")

    async def execute_reduction(self, contract: ModelContractReducer) -> ModelReducerOutput:
        """
        Execute data reduction and aggregation based on contract specification.

        Args:
            contract: Reducer contract with aggregation specifications

        Returns:
            ModelReducerOutput: Aggregated results with state information

        Raises:
            StateConsistencyError: If state consistency cannot be maintained
            TransactionError: If transaction management fails
            OnexError: If reduction operation fails
        """
        transaction_id = None

        try:
            # Start transaction if configured
            if contract.transaction_config:
                transaction_id = await self.transaction_manager.begin_transaction(
                    contract.correlation_id
                )

            # Load existing state
            current_state = await self.state_manager.get_state(
                contract.correlation_id,
                contract.reduction_config.state_key
            )

            # Perform reduction operation
            if contract.streaming_config and contract.streaming_config.enabled:
                result = await self._execute_streaming_reduction(contract, current_state)
            else:
                result = await self._execute_batch_reduction(contract, current_state)

            # Update state with results
            await self.state_manager.update_state(
                contract.correlation_id,
                contract.reduction_config.state_key,
                result.aggregated_state
            )

            # Create backup if configured
            if contract.backup_config:
                await self._create_state_backup(contract, result)

            # Commit transaction
            if transaction_id:
                await self.transaction_manager.commit_transaction(transaction_id)

            return ModelReducerOutput(
                correlation_id=contract.correlation_id,
                aggregated_data=result.aggregated_data,
                state_metadata=result.state_metadata,
                reduction_metrics={
                    "records_processed": result.records_processed,
                    "reduction_ratio": result.reduction_ratio,
                    "state_size": len(result.aggregated_state)
                }
            )

        except Exception as e:
            # Rollback transaction on error
            if transaction_id:
                await self.transaction_manager.rollback_transaction(transaction_id)
            raise OnexError("Reduction operation failed") from e

    async def _execute_streaming_reduction(self, contract: ModelContractReducer, current_state):
        """Execute reduction with streaming data support."""
        streaming_config = contract.streaming_config
        reduction_config = contract.reduction_config

        aggregator = StreamingAggregator(
            aggregation_method=reduction_config.aggregation_method,
            chunk_size=streaming_config.chunk_size,
            current_state=current_state
        )

        async for data_chunk in self._stream_input_data(contract.input_data, streaming_config):
            chunk_result = await aggregator.process_chunk(data_chunk)

            # Update progress tracking
            await self._update_progress(contract.correlation_id, chunk_result.progress)

            # Handle memory management
            if chunk_result.memory_usage > contract.memory_management.buffer_size_mb * 0.8:
                await aggregator.flush_intermediate_results()

        return await aggregator.finalize()

    async def _execute_batch_reduction(self, contract: ModelContractReducer, current_state):
        """Execute reduction in batch mode."""
        reduction_config = contract.reduction_config

        # Apply aggregation method
        if reduction_config.aggregation_method == "sum":
            result = self._sum_aggregation(contract.input_data, current_state)
        elif reduction_config.aggregation_method == "average":
            result = self._average_aggregation(contract.input_data, current_state)
        elif reduction_config.aggregation_method == "count":
            result = self._count_aggregation(contract.input_data, current_state)
        elif reduction_config.aggregation_method == "custom":
            result = await self._custom_aggregation(contract.input_data, current_state, reduction_config)
        else:
            raise ValueError(f"Unsupported aggregation method: {reduction_config.aggregation_method}")

        return BatchReductionResult(
            aggregated_data=result,
            aggregated_state=self._merge_state(current_state, result),
            records_processed=len(contract.input_data),
            reduction_ratio=self._calculate_reduction_ratio(contract.input_data, result)
        )

    async def _create_state_backup(self, contract: ModelContractReducer, result):
        """Create backup of aggregated state."""
        backup_config = contract.backup_config
        backup_data = {
            "timestamp": datetime.now(UTC),
            "correlation_id": contract.correlation_id,
            "aggregated_state": result.aggregated_state,
            "backup_metadata": {
                "version": backup_config.version,
                "backup_type": backup_config.backup_type
            }
        }

        await self.state_manager.create_backup(
            backup_config.backup_location,
            backup_data
        )
```

**Best Practices**:
- Implement transactional consistency where required
- Use appropriate data structures for aggregation operations
- Provide incremental processing capabilities
- Monitor memory usage during aggregation
- Support both batch and streaming processing modes

### 4. ORCHESTRATOR Node

**Primary Responsibility**: Workflow coordination and service orchestration

**Key Functions**:
- Service coordination and dependency management
- Workflow execution control
- Event-driven processing coordination
- Resource allocation and management
- Cross-service communication

**Design Principles**:
- Centralized coordination logic
- Event-driven architecture support
- Fault tolerance and recovery
- Service discovery and health monitoring
- Scalable workflow management

**Implementation Example**:

```python
from omnibase_core.core.infrastructure_service_bases import NodeOrchestratorService
from omnibase_core.models.contracts.model_contract_orchestrator import ModelContractOrchestrator

class WorkflowOrchestratorService(NodeOrchestratorService):
    """
    ORCHESTRATOR node for workflow coordination and service management.

    Coordinates execution across multiple services with support for complex
    workflow patterns, dependency management, and fault tolerance.
    """

    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.service_registry = container.get_service("ProtocolServiceRegistry")
        self.event_bus = container.get_service("ProtocolEventBus")
        self.health_monitor = container.get_service("ProtocolHealthMonitor")

    async def execute_orchestration(self, contract: ModelContractOrchestrator) -> ModelOrchestratorOutput:
        """
        Execute workflow orchestration based on contract specification.

        Args:
            contract: Orchestrator contract with workflow and dependency specifications

        Returns:
            ModelOrchestratorOutput: Orchestration results with execution metadata

        Raises:
            DependencyResolutionError: If required dependencies are not available
            WorkflowExecutionError: If workflow execution fails
            OnexError: If orchestration fails
        """
        workflow_id = str(uuid4())

        try:
            # Validate service dependencies
            await self._validate_dependencies(contract.dependency_resolution)

            # Initialize workflow execution context
            execution_context = await self._initialize_execution_context(contract, workflow_id)

            # Execute workflow based on coordination pattern
            if contract.workflow_config.coordination_type == EnumWorkflowCoordination.SEQUENTIAL:
                result = await self._execute_sequential_workflow(contract, execution_context)
            elif contract.workflow_config.coordination_type == EnumWorkflowCoordination.PARALLEL:
                result = await self._execute_parallel_workflow(contract, execution_context)
            elif contract.workflow_config.coordination_type == EnumWorkflowCoordination.PIPELINE:
                result = await self._execute_pipeline_workflow(contract, execution_context)
            elif contract.workflow_config.coordination_type == EnumWorkflowCoordination.EVENT_DRIVEN:
                result = await self._execute_event_driven_workflow(contract, execution_context)
            else:
                raise ValueError(f"Unsupported coordination type: {contract.workflow_config.coordination_type}")

            # Handle lifecycle completion
            await self._finalize_workflow(contract, execution_context, result)

            return ModelOrchestratorOutput(
                correlation_id=contract.correlation_id,
                workflow_id=workflow_id,
                orchestration_result=result,
                execution_metadata={
                    "total_services": len(contract.dependency_resolution),
                    "execution_time": result.total_execution_time,
                    "success_rate": result.success_rate,
                    "coordination_type": contract.workflow_config.coordination_type
                }
            )

        except Exception as e:
            await self._handle_orchestration_failure(contract, workflow_id, e)
            raise OnexError("Workflow orchestration failed") from e

    async def _execute_sequential_workflow(self, contract: ModelContractOrchestrator, execution_context):
        """Execute workflow with sequential service coordination."""
        results = []
        total_execution_time = 0

        for step in execution_context.workflow_steps:
            start_time = time.time()

            try:
                # Execute service call
                service = self.service_registry.get_service(step.service_name)
                step_result = await service.execute(step.parameters)

                # Update execution context with results
                execution_context.update_step_result(step.step_id, step_result)

                # Record success
                step_execution_time = time.time() - start_time
                total_execution_time += step_execution_time

                results.append(WorkflowStepResult(
                    step_id=step.step_id,
                    result=step_result,
                    execution_time=step_execution_time,
                    status="completed"
                ))

                # Publish step completion event
                await self.event_bus.publish(WorkflowStepCompletedEvent(
                    workflow_id=execution_context.workflow_id,
                    step_id=step.step_id,
                    correlation_id=contract.correlation_id
                ))

            except Exception as e:
                # Handle step failure based on conflict resolution configuration
                failure_action = await self._resolve_step_failure(
                    contract.conflict_resolution, step, e
                )

                if failure_action == "abort":
                    raise WorkflowExecutionError(f"Step {step.step_id} failed: {e}") from e
                elif failure_action == "skip":
                    results.append(WorkflowStepResult(
                        step_id=step.step_id,
                        result=None,
                        execution_time=time.time() - start_time,
                        status="skipped",
                        error=str(e)
                    ))
                elif failure_action == "retry":
                    # Implement retry logic
                    retry_result = await self._retry_step(step, contract.conflict_resolution.retry_config)
                    results.append(retry_result)

        return SequentialWorkflowResult(
            step_results=results,
            total_execution_time=total_execution_time,
            success_rate=len([r for r in results if r.status == "completed"]) / len(results)
        )

    async def _execute_parallel_workflow(self, contract: ModelContractOrchestrator, execution_context):
        """Execute workflow with parallel service coordination."""
        # Group steps by dependency levels
        dependency_levels = self._analyze_step_dependencies(execution_context.workflow_steps)

        results = []
        total_execution_time = 0
        start_time = time.time()

        for level_steps in dependency_levels:
            # Execute all steps in this level concurrently
            level_tasks = []
            for step in level_steps:
                service = self.service_registry.get_service(step.service_name)
                task = asyncio.create_task(
                    service.execute(step.parameters),
                    name=f"step_{step.step_id}"
                )
                level_tasks.append((step, task))

            # Wait for all tasks in this level to complete
            level_results = await asyncio.gather(*[task for _, task in level_tasks], return_exceptions=True)

            # Process results and handle exceptions
            for (step, task), result in zip(level_tasks, level_results):
                if isinstance(result, Exception):
                    # Handle step failure
                    failure_action = await self._resolve_step_failure(
                        contract.conflict_resolution, step, result
                    )
                    if failure_action == "abort":
                        # Cancel remaining tasks
                        for _, remaining_task in level_tasks:
                            if not remaining_task.done():
                                remaining_task.cancel()
                        raise WorkflowExecutionError(f"Step {step.step_id} failed: {result}") from result
                else:
                    # Record successful result
                    execution_context.update_step_result(step.step_id, result)
                    results.append(WorkflowStepResult(
                        step_id=step.step_id,
                        result=result,
                        status="completed"
                    ))

        total_execution_time = time.time() - start_time

        return ParallelWorkflowResult(
            step_results=results,
            total_execution_time=total_execution_time,
            parallelism_achieved=len(max(dependency_levels, key=len)),
            success_rate=len([r for r in results if r.status == "completed"]) / len(results)
        )

    async def _validate_dependencies(self, dependencies: List[ModelDependency]):
        """Validate all required dependencies are available and healthy."""
        for dependency in dependencies:
            if dependency.dependency_type == EnumDependencyType.REQUIRED:
                # Check service availability
                service_health = await self.health_monitor.check_service_health(
                    dependency.service_name
                )
                if not service_health.is_healthy:
                    raise DependencyResolutionError(
                        f"Required dependency {dependency.service_name} is not healthy"
                    )

                # Check version compatibility
                if dependency.version_constraint:
                    service_version = await self.service_registry.get_service_version(
                        dependency.service_name
                    )
                    if not self._check_version_compatibility(service_version, dependency.version_constraint):
                        raise DependencyResolutionError(
                            f"Version incompatibility for {dependency.service_name}: "
                            f"required {dependency.version_constraint}, found {service_version}"
                        )

    async def _resolve_step_failure(self, conflict_resolution: ModelConflictResolutionConfig,
                                  step: WorkflowStep, error: Exception) -> str:
        """Resolve step failure based on configuration."""
        if error.__class__.__name__ in conflict_resolution.retry_conditions:
            if conflict_resolution.retry_enabled and step.retry_count < conflict_resolution.max_retries:
                return "retry"

        if conflict_resolution.continue_on_error:
            return "skip"
        else:
            return "abort"
```

**Best Practices**:
- Implement comprehensive dependency validation
- Support multiple workflow coordination patterns
- Provide detailed execution monitoring and logging
- Handle failures gracefully with appropriate recovery strategies
- Use event-driven patterns for loose coupling

## Inter-Node Communication

### Contract-Based Communication

All communication between nodes uses typed contracts:

```python
# EFFECT → COMPUTE
effect_output = await effect_node.execute_effect(effect_contract)
compute_contract = ModelContractCompute(
    correlation_id=effect_output.correlation_id,
    input_data=effect_output.operation_result,
    algorithm_config=algorithm_config
)
compute_output = await compute_node.execute_compute(compute_contract)
```

### Event-Driven Communication

Nodes can also communicate through events:

```python
# Publish event from EFFECT node
await event_bus.publish(DataAvailableEvent(
    correlation_id=correlation_id,
    data_location=data_location,
    metadata=processing_metadata
))

# COMPUTE node subscribes to events
@event_handler("DataAvailableEvent")
async def handle_data_available(event: DataAvailableEvent):
    # Process data from EFFECT node
    pass
```

## Error Handling Patterns

### Node-Level Error Handling

Each node implements standardized error handling:

```python
@standard_error_handling
async def execute_node_operation(self, contract):
    try:
        # Node-specific processing
        result = await self._process_contract(contract)
        return result
    except ValidationError as e:
        raise OnexError(
            message="Contract validation failed",
            correlation_id=contract.correlation_id,
            error_context={
                "node_type": self.__class__.__name__,
                "validation_errors": e.errors()
            }
        ) from e
    except Exception as e:
        raise OnexError(
            message=f"Node processing failed: {e}",
            correlation_id=contract.correlation_id,
            error_context={
                "node_type": self.__class__.__name__,
                "operation": "execute_node_operation"
            }
        ) from e
```

### Cross-Node Error Propagation

Errors propagate through the pipeline with context:

```python
class PipelineErrorContext:
    """Track errors across the entire ONEX pipeline."""

    def __init__(self, correlation_id: UUID):
        self.correlation_id = correlation_id
        self.error_chain: List[OnexError] = []
        self.failed_nodes: List[str] = []

    def add_error(self, error: OnexError, node_type: str):
        """Add error to the chain with node context."""
        self.error_chain.append(error)
        self.failed_nodes.append(node_type)

    def create_pipeline_error(self) -> OnexError:
        """Create comprehensive pipeline error."""
        return OnexError(
            message=f"Pipeline failed at nodes: {', '.join(self.failed_nodes)}",
            correlation_id=self.correlation_id,
            error_context={
                "pipeline_errors": [str(e) for e in self.error_chain],
                "failed_nodes": self.failed_nodes,
                "total_errors": len(self.error_chain)
            }
        )
```

## Performance Optimization

### Parallel Processing

Nodes support parallel processing within their operations:

```python
# COMPUTE node with parallel processing
class ParallelComputeService(NodeComputeService):
    async def execute_compute(self, contract: ModelContractCompute):
        if contract.parallel_config:
            # Split data into chunks for parallel processing
            chunks = self._split_data_into_chunks(
                contract.input_data,
                contract.parallel_config.worker_count
            )

            # Process chunks in parallel
            tasks = [self._process_chunk(chunk) for chunk in chunks]
            results = await asyncio.gather(*tasks)

            # Merge results
            final_result = self._merge_results(results)
            return final_result
```

### Resource Management

Nodes implement resource pooling and management:

```python
class ResourceManagedEffectService(NodeEffectService):
    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.connection_pool = container.get_service("ProtocolConnectionPool")
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent operations

    async def execute_effect(self, contract: ModelContractEffect):
        async with self.semaphore:  # Control concurrency
            async with self.connection_pool.acquire() as connection:
                # Use pooled connection for operation
                return await self._execute_with_connection(connection, contract)
```

## Monitoring and Observability

### Performance Metrics

All nodes collect performance metrics:

```python
class MonitoredNodeService:
    def __init__(self, container: ONEXContainer):
        self.metrics_collector = container.get_service("ProtocolMetricsCollector")

    async def execute_with_monitoring(self, contract):
        start_time = time.time()

        try:
            result = await self._execute_operation(contract)

            # Record success metrics
            execution_time = time.time() - start_time
            await self.metrics_collector.record_metric(
                metric_name="node_execution_time",
                value=execution_time,
                tags={
                    "node_type": self.__class__.__name__,
                    "correlation_id": str(contract.correlation_id),
                    "status": "success"
                }
            )

            return result

        except Exception as e:
            # Record error metrics
            execution_time = time.time() - start_time
            await self.metrics_collector.record_metric(
                metric_name="node_execution_time",
                value=execution_time,
                tags={
                    "node_type": self.__class__.__name__,
                    "correlation_id": str(contract.correlation_id),
                    "status": "error",
                    "error_type": e.__class__.__name__
                }
            )
            raise
```

### Health Checks

Nodes provide health check endpoints:

```python
class HealthCheckMixin:
    async def health_check(self) -> NodeHealthStatus:
        """Perform comprehensive health check."""
        try:
            # Check dependencies
            dependencies_healthy = await self._check_dependencies()

            # Check resource utilization
            resource_usage = await self._get_resource_usage()

            # Check recent error rates
            error_rate = await self._get_error_rate()

            if dependencies_healthy and resource_usage < 0.9 and error_rate < 0.1:
                return NodeHealthStatus(
                    status=EnumHealthStatus.HEALTHY,
                    details={
                        "dependencies": "healthy",
                        "resource_usage": resource_usage,
                        "error_rate": error_rate
                    }
                )
            else:
                return NodeHealthStatus(
                    status=EnumHealthStatus.DEGRADED,
                    details={
                        "dependencies": "healthy" if dependencies_healthy else "unhealthy",
                        "resource_usage": resource_usage,
                        "error_rate": error_rate
                    }
                )
        except Exception as e:
            return NodeHealthStatus(
                status=EnumHealthStatus.UNHEALTHY,
                details={"error": str(e)}
            )
```

## Testing Strategies

### Unit Testing

Each node type has specific testing patterns:

```python
class TestEffectNode(unittest.TestCase):
    async def test_external_service_interaction(self):
        """Test EFFECT node external service interaction."""
        # Mock external service
        mock_service = Mock()
        mock_service.call_api.return_value = {"result": "success"}

        # Create EFFECT node with mock
        effect_node = DatabaseEffectService(mock_container)
        effect_node.external_service = mock_service

        # Execute contract
        contract = ModelContractEffect(
            correlation_id=uuid4(),
            external_service_config=external_config,
            io_operation_config=io_config
        )

        result = await effect_node.execute_effect(contract)

        # Verify interaction
        mock_service.call_api.assert_called_once()
        self.assertEqual(result.operation_result["result"], "success")

class TestComputeNode(unittest.TestCase):
    async def test_algorithm_execution(self):
        """Test COMPUTE node algorithm execution."""
        compute_node = DataTransformationComputeService(mock_container)

        contract = ModelContractCompute(
            correlation_id=uuid4(),
            algorithm_config=ModelAlgorithmConfig(
                algorithm_type="sum",
                parameters={}
            ),
            input_data=[1, 2, 3, 4, 5]
        )

        result = await compute_node.execute_compute(contract)

        # Verify computation result
        self.assertEqual(result.processed_data, 15)
```

### Integration Testing

Test complete pipeline flows:

```python
class TestPipelineIntegration(unittest.TestCase):
    async def test_complete_pipeline_flow(self):
        """Test complete EFFECT → COMPUTE → REDUCER → ORCHESTRATOR flow."""
        # Setup all nodes
        effect_node = create_effect_node()
        compute_node = create_compute_node()
        reducer_node = create_reducer_node()
        orchestrator_node = create_orchestrator_node()

        # Create initial contract
        initial_data = {"input": "test_data"}
        correlation_id = uuid4()

        # Execute EFFECT
        effect_contract = ModelContractEffect(
            correlation_id=correlation_id,
            external_service_config=test_config,
            io_operation_config=test_io_config
        )
        effect_result = await effect_node.execute_effect(effect_contract)

        # Execute COMPUTE
        compute_contract = ModelContractCompute(
            correlation_id=correlation_id,
            input_data=effect_result.operation_result,
            algorithm_config=test_algorithm_config
        )
        compute_result = await compute_node.execute_compute(compute_contract)

        # Execute REDUCER
        reducer_contract = ModelContractReducer(
            correlation_id=correlation_id,
            input_data=compute_result.processed_data,
            reduction_config=test_reduction_config
        )
        reducer_result = await reducer_node.execute_reduction(reducer_contract)

        # Execute ORCHESTRATOR
        orchestrator_contract = ModelContractOrchestrator(
            correlation_id=correlation_id,
            workflow_config=test_workflow_config,
            dependency_resolution=test_dependencies
        )
        final_result = await orchestrator_node.execute_orchestration(orchestrator_contract)

        # Verify complete pipeline
        self.assertEqual(final_result.correlation_id, correlation_id)
        self.assertIsNotNone(final_result.orchestration_result)
```

## Best Practices Summary

### Architecture Principles
1. **Single Responsibility**: Each node has one clear purpose
2. **Unidirectional Flow**: Data flows left to right through the pipeline
3. **Contract-Based Communication**: All inter-node communication uses typed contracts
4. **Error Propagation**: Errors include correlation context and are properly chained
5. **Resource Management**: Proper resource pooling and cleanup

### Implementation Guidelines
1. **Comprehensive Documentation**: Every public method must have complete docstrings
2. **Type Safety**: Use specific types, avoid `Any` where possible
3. **Error Handling**: Always inherit from `OnexError` for custom exceptions
4. **Performance Monitoring**: Collect metrics for all operations
5. **Health Checks**: Implement comprehensive health monitoring

### Testing Requirements
1. **Unit Tests**: Test each node independently with mocked dependencies
2. **Integration Tests**: Test complete pipeline flows
3. **Performance Tests**: Validate performance under load
4. **Error Tests**: Verify proper error handling and propagation
5. **Resource Tests**: Test resource management and cleanup

This architecture documentation provides comprehensive coverage of the ONEX Four-Node pattern with zero tolerance for incomplete specifications. All components are fully documented with examples, best practices, and implementation guidelines.
