#!/usr/bin/env python3
"""
Contract Model Specialization Tests - ONEX Standards Compliant.

Comprehensive test suite for the 4-node architecture contract model hierarchy:
- ModelContractBase foundation validation
- All 4 specialized contract models (Compute, Effect, Reducer, Orchestrator)
- Event Registry integration testing
- Contract validation framework testing
- Strong typing compliance verification

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.node import EnumNodeType
from omnibase_core.models.rsd.model_contract_base import (
    ModelContractBase,
    ModelLifecycleConfig,
    ModelPerformanceRequirements,
    ModelValidationRules,
)
from omnibase_core.models.rsd.model_contract_compute import (
    ModelAlgorithmConfig,
    ModelAlgorithmFactorConfig,
    ModelCachingConfig,
    ModelContractCompute,
    ModelParallelConfig,
)
from omnibase_core.models.rsd.model_contract_effect import (
    ModelContractEffect,
    ModelIOOperationConfig,
    ModelRetryConfig,
    ModelTransactionConfig,
)
from omnibase_core.models.rsd.model_contract_orchestrator import (
    ModelBranchingConfig,
    ModelContractOrchestrator,
    ModelEventCoordinationConfig,
    ModelEventDescriptor,
    ModelEventSubscription,
    ModelThunkEmissionConfig,
    ModelWorkflowConfig,
)
from omnibase_core.models.rsd.model_contract_reducer import (
    ModelAggregationConfig,
    ModelContractReducer,
    ModelReductionConfig,
    ModelStreamingConfig,
)


class TestContractModelBase:
    """Test ModelContractBase foundation and validation."""

    def test_enum_node_type_values(self):
        """Test EnumNodeType has all required values."""
        assert EnumNodeType.COMPUTE == "COMPUTE"
        assert EnumNodeType.EFFECT == "EFFECT"
        assert EnumNodeType.REDUCER == "REDUCER"
        assert EnumNodeType.ORCHESTRATOR == "ORCHESTRATOR"

    def test_performance_requirements_model(self):
        """Test ModelPerformanceRequirements validation."""
        # Valid configuration
        perf = ModelPerformanceRequirements(
            single_operation_max_ms=100,
            batch_operation_max_s=5,
            memory_limit_mb=512,
            cpu_limit_percent=50,
            throughput_min_ops_per_second=10.0,
        )
        assert perf.single_operation_max_ms == 100
        assert perf.throughput_min_ops_per_second == 10.0

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(single_operation_max_ms=0)  # Must be >= 1

        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(cpu_limit_percent=101)  # Must be <= 100

    def test_lifecycle_config_model(self):
        """Test ModelLifecycleConfig validation."""
        lifecycle = ModelLifecycleConfig(
            initialization_timeout_s=60,
            cleanup_timeout_s=30,
            error_recovery_enabled=True,
            state_persistence_enabled=False,
            health_check_interval_s=120,
        )
        assert lifecycle.initialization_timeout_s == 60
        assert lifecycle.error_recovery_enabled is True

        # Invalid timeout should raise ValidationError
        with pytest.raises(ValidationError):
            ModelLifecycleConfig(initialization_timeout_s=0)  # Must be >= 1

    def test_validation_rules_model(self):
        """Test ModelValidationRules model."""
        rules = ModelValidationRules(
            strict_typing_enabled=True,
            input_validation_enabled=True,
            output_validation_enabled=True,
            performance_validation_enabled=True,
            constraint_definitions={"field1": "constraint1", "field2": "constraint2"},
        )
        assert rules.strict_typing_enabled is True
        assert len(rules.constraint_definitions) == 2


class TestContractCompute:
    """Test ModelContractCompute specialized contract model."""

    def create_valid_algorithm_config(self) -> ModelAlgorithmConfig:
        """Create a valid algorithm configuration for testing."""
        return ModelAlgorithmConfig(
            algorithm_type="weighted_factor_algorithm",
            factors={
                "dependency_distance": ModelAlgorithmFactorConfig(
                    weight=0.40,
                    calculation_method="graph_traversal_depth",
                ),
                "failure_surface": ModelAlgorithmFactorConfig(
                    weight=0.25,
                    calculation_method="compound_risk_analysis",
                ),
                "time_decay": ModelAlgorithmFactorConfig(
                    weight=0.15,
                    calculation_method="exponential_decay",
                ),
                "agent_utility": ModelAlgorithmFactorConfig(
                    weight=0.10,
                    calculation_method="weighted_frequency",
                ),
                "user_weighting": ModelAlgorithmFactorConfig(
                    weight=0.10,
                    calculation_method="manual_override",
                ),
            },
        )

    def test_algorithm_factor_config(self):
        """Test ModelAlgorithmFactorConfig validation."""
        factor = ModelAlgorithmFactorConfig(
            weight=0.25,
            calculation_method="compound_risk_analysis",
            parameters={"param1": 1.0},
            normalization_enabled=True,
            caching_enabled=True,
        )
        assert factor.weight == 0.25
        assert factor.calculation_method == "compound_risk_analysis"

        # Invalid weight should raise ValidationError
        with pytest.raises(ValidationError):
            ModelAlgorithmFactorConfig(
                weight=1.5,
                calculation_method="test",
            )  # Weight > 1.0

    def test_algorithm_config_factor_weights_validation(self):
        """Test algorithm config validates factor weights sum to 1.0."""
        # Valid configuration (weights sum to 1.0)
        valid_config = self.create_valid_algorithm_config()
        assert valid_config.algorithm_type == "weighted_factor_algorithm"

        # Invalid configuration (weights don't sum to 1.0)
        with pytest.raises(ValidationError):
            ModelAlgorithmConfig(
                algorithm_type="weighted_factor_algorithm",
                factors={
                    "factor1": ModelAlgorithmFactorConfig(
                        weight=0.60,
                        calculation_method="method1",
                    ),
                    "factor2": ModelAlgorithmFactorConfig(
                        weight=0.20,
                        calculation_method="method2",
                    ),
                    # Total: 0.80, should fail validation
                },
            )

    def test_parallel_config(self):
        """Test ModelParallelConfig validation."""
        parallel = ModelParallelConfig(
            enabled=True,
            max_workers=8,
            batch_size=200,
            async_enabled=True,
            thread_pool_type="ThreadPoolExecutor",
            queue_size=2000,
        )
        assert parallel.max_workers == 8
        assert parallel.async_enabled is True

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError):
            ModelParallelConfig(max_workers=0)  # Must be >= 1

    def test_caching_config(self):
        """Test ModelCachingConfig validation."""
        caching = ModelCachingConfig(
            strategy="lru",
            max_size=2000,
            ttl_seconds=600,
            enabled=True,
            cache_key_strategy="input_hash",
            eviction_policy="least_recently_used",
        )
        assert caching.strategy == "lru"
        assert caching.max_size == 2000

        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError):
            ModelCachingConfig(max_size=0)  # Must be >= 1

    def test_contract_compute_creation(self):
        """Test ModelContractCompute creation and validation."""
        algorithm_config = self.create_valid_algorithm_config()

        contract = ModelContractCompute(
            name="RSDPriorityComputeContract",
            version="1.0.0",
            description="5-factor RSD priority calculation with performance optimization",
            input_model="ModelRSDPriorityInput",
            output_model="ModelRSDPriorityOutput",
            algorithm=algorithm_config,
            performance=ModelPerformanceRequirements(single_operation_max_ms=100),
        )

        assert contract.node_type == EnumNodeType.COMPUTE
        assert contract.name == "RSDPriorityComputeContract"
        assert contract.algorithm.algorithm_type == "weighted_factor_algorithm"
        assert contract.deterministic_execution is True

    def test_contract_compute_validation_failures(self):
        """Test ModelContractCompute validation failures."""
        algorithm_config = self.create_valid_algorithm_config()

        # Missing performance requirement should fail
        with pytest.raises(ValidationError):
            ModelContractCompute(
                name="InvalidContract",
                version="1.0.0",
                description="Test contract",
                input_model="TestInput",
                output_model="TestOutput",
                algorithm=algorithm_config,
                # Missing required performance.single_operation_max_ms
            )


class TestContractEffect:
    """Test ModelContractEffect specialized contract model."""

    def create_valid_io_operation(self) -> ModelIOOperationConfig:
        """Create a valid I/O operation configuration for testing."""
        return ModelIOOperationConfig(
            operation_type="file_write",
            atomic=True,
            backup_enabled=True,
            permissions="0644",
            recursive=False,
            buffer_size=8192,
            timeout_seconds=30,
            validation_enabled=True,
        )

    def test_io_operation_config(self):
        """Test ModelIOOperationConfig validation."""
        io_op = self.create_valid_io_operation()
        assert io_op.operation_type == "file_write"
        assert io_op.atomic is True
        assert io_op.buffer_size == 8192

        # Invalid buffer size should raise ValidationError
        with pytest.raises(ValidationError):
            ModelIOOperationConfig(
                operation_type="test",
                buffer_size=512,
            )  # Must be >= 1024

    def test_transaction_config(self):
        """Test ModelTransactionConfig validation."""
        transaction = ModelTransactionConfig(
            enabled=True,
            isolation_level="read_committed",
            timeout_seconds=60,
            rollback_on_error=True,
            lock_timeout_seconds=15,
            deadlock_retry_count=5,
            consistency_check_enabled=True,
        )
        assert transaction.isolation_level == "read_committed"
        assert transaction.deadlock_retry_count == 5

    def test_retry_config(self):
        """Test ModelRetryConfig validation."""
        retry = ModelRetryConfig(
            max_attempts=5,
            backoff_strategy="exponential",
            base_delay_ms=200,
            max_delay_ms=10000,
            jitter_enabled=True,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout_s=120,
        )
        assert retry.backoff_strategy == "exponential"
        assert retry.circuit_breaker_threshold == 3

        # max_delay_ms must be greater than base_delay_ms
        with pytest.raises(ValidationError):
            ModelRetryConfig(base_delay_ms=1000, max_delay_ms=500)

    def test_contract_effect_creation(self):
        """Test ModelContractEffect creation and validation."""
        io_operation = self.create_valid_io_operation()

        contract = ModelContractEffect(
            name="RSDFileOperationsContract",
            version="1.0.0",
            description="Atomic file operations for work ticket management",
            input_model="ModelFileOperationInput",
            output_model="ModelFileOperationOutput",
            io_operations=[io_operation],
        )

        assert contract.node_type == EnumNodeType.EFFECT
        assert contract.name == "RSDFileOperationsContract"
        assert len(contract.io_operations) == 1
        assert contract.idempotent_operations is True

    def test_contract_effect_validation_failures(self):
        """Test ModelContractEffect validation failures."""
        # Empty I/O operations should fail validation
        with pytest.raises(ValidationError):
            ModelContractEffect(
                name="InvalidContract",
                version="1.0.0",
                description="Test contract",
                input_model="TestInput",
                output_model="TestOutput",
                io_operations=[],  # Must have at least one I/O operation
            )


class TestContractReducer:
    """Test ModelContractReducer specialized contract model."""

    def create_valid_reduction_config(self) -> ModelReductionConfig:
        """Create a valid reduction configuration for testing."""
        return ModelReductionConfig(
            operation_type="fold",
            reduction_function="weighted_sum",
            associative=True,
            commutative=False,
            identity_element="0",
            chunk_size=1000,
            parallel_enabled=True,
            intermediate_results_caching=True,
        )

    def create_valid_aggregation_config(self) -> ModelAggregationConfig:
        """Create a valid aggregation configuration for testing."""
        return ModelAggregationConfig(
            aggregation_functions=["sum", "count", "avg", "max"],
            grouping_fields=["category", "priority"],
            statistical_functions=["median", "std"],
            precision_digits=6,
            null_handling_strategy="ignore",
            duplicate_handling="include",
        )

    def test_reduction_config(self):
        """Test ModelReductionConfig validation."""
        reduction = self.create_valid_reduction_config()
        assert reduction.operation_type == "fold"
        assert reduction.associative is True
        assert reduction.chunk_size == 1000

    def test_streaming_config(self):
        """Test ModelStreamingConfig validation."""
        streaming = ModelStreamingConfig(
            enabled=True,
            buffer_size=16384,
            window_size=2000,
            window_overlap=100,
            memory_threshold_mb=1024,
            backpressure_enabled=True,
            checkpoint_interval=20000,
            flow_control_enabled=True,
        )
        assert streaming.window_size == 2000
        assert streaming.window_overlap == 100

        # window_overlap must be less than window_size
        with pytest.raises(ValidationError):
            ModelStreamingConfig(window_size=1000, window_overlap=1000)

    def test_aggregation_config(self):
        """Test ModelAggregationConfig validation."""
        aggregation = self.create_valid_aggregation_config()
        assert "sum" in aggregation.aggregation_functions
        assert len(aggregation.grouping_fields) == 2

        # Empty aggregation functions should fail
        with pytest.raises(ValidationError):
            ModelAggregationConfig(aggregation_functions=[])

        # Unsupported aggregation function should fail
        with pytest.raises(ValidationError):
            ModelAggregationConfig(aggregation_functions=["unsupported_function"])

    def test_contract_reducer_creation(self):
        """Test ModelContractReducer creation and validation."""
        reduction_config = self.create_valid_reduction_config()
        aggregation_config = self.create_valid_aggregation_config()

        contract = ModelContractReducer(
            name="RSDDataAggregationContract",
            version="1.0.0",
            description="Data aggregation and reduction for RSD metrics",
            input_model="ModelAggregationInput",
            output_model="ModelAggregationOutput",
            reduction_operations=[reduction_config],
            aggregation=aggregation_config,
            performance=ModelPerformanceRequirements(batch_operation_max_s=10),
        )

        assert contract.node_type == EnumNodeType.REDUCER
        assert contract.name == "RSDDataAggregationContract"
        assert len(contract.reduction_operations) == 1
        assert contract.incremental_processing is True

    def test_contract_reducer_validation_failures(self):
        """Test ModelContractReducer validation failures."""
        aggregation_config = self.create_valid_aggregation_config()

        # Missing reduction operations should fail
        with pytest.raises(ValidationError):
            ModelContractReducer(
                name="InvalidContract",
                version="1.0.0",
                description="Test contract",
                input_model="TestInput",
                output_model="TestOutput",
                reduction_operations=[],  # Must have at least one reduction operation
                aggregation=aggregation_config,
            )


class TestContractOrchestrator:
    """Test ModelContractOrchestrator specialized contract model."""

    def create_valid_event_descriptor(self) -> ModelEventDescriptor:
        """Create a valid event descriptor for testing."""
        return ModelEventDescriptor(
            event_name="rsd_priority_calculated",
            event_type="computation_complete",
            schema_reference="schemas/events/rsd_priority_calculated.json",
            description="Event emitted when RSD priority calculation completes",
            version="1.0.0",
            payload_structure={"ticket_id": "string", "priority_score": "float"},
            metadata_fields=["timestamp", "correlation_id"],
            criticality_level="normal",
        )

    def create_valid_event_subscription(self) -> ModelEventSubscription:
        """Create a valid event subscription for testing."""
        return ModelEventSubscription(
            event_pattern="ticket_*",
            filter_conditions={"priority": "high"},
            handler_function="handle_high_priority_ticket",
            batch_processing=False,
            batch_size=1,
            timeout_ms=5000,
            retry_enabled=True,
            dead_letter_enabled=True,
        )

    def test_thunk_emission_config(self):
        """Test ModelThunkEmissionConfig validation."""
        thunk = ModelThunkEmissionConfig(
            emission_strategy="on_demand",
            batch_size=20,
            max_deferred_thunks=2000,
            execution_delay_ms=100,
            priority_based_emission=True,
            dependency_aware_emission=True,
            retry_failed_thunks=True,
        )
        assert thunk.emission_strategy == "on_demand"
        assert thunk.batch_size == 20

    def test_workflow_config(self):
        """Test ModelWorkflowConfig validation."""
        workflow = ModelWorkflowConfig(
            execution_mode="parallel",
            max_parallel_branches=8,
            checkpoint_enabled=True,
            checkpoint_interval_ms=10000,
            state_persistence_enabled=True,
            rollback_enabled=True,
            timeout_ms=60000,
            recovery_enabled=True,
        )
        assert workflow.execution_mode == "parallel"
        assert workflow.max_parallel_branches == 8

    def test_branching_config(self):
        """Test ModelBranchingConfig validation."""
        branching = ModelBranchingConfig(
            decision_points=["priority_check", "resource_availability"],
            condition_evaluation_strategy="eager",
            branch_merge_strategy="wait_all",
            default_branch_enabled=True,
            condition_timeout_ms=2000,
            nested_branching_enabled=True,
            max_branch_depth=15,
        )
        assert len(branching.decision_points) == 2
        assert branching.max_branch_depth == 15

    def test_event_descriptor(self):
        """Test ModelEventDescriptor validation."""
        event = self.create_valid_event_descriptor()
        assert event.event_name == "rsd_priority_calculated"
        assert event.version == "1.0.0"
        assert len(event.payload_structure) == 2

    def test_event_subscription(self):
        """Test ModelEventSubscription validation."""
        subscription = self.create_valid_event_subscription()
        assert subscription.event_pattern == "ticket_*"
        assert subscription.handler_function == "handle_high_priority_ticket"

    def test_event_coordination_config(self):
        """Test ModelEventCoordinationConfig validation."""
        coordination = ModelEventCoordinationConfig(
            trigger_mappings={"ticket_created": "start_priority_calculation"},
            coordination_strategy="immediate",
            buffer_size=200,
            correlation_enabled=True,
            correlation_timeout_ms=15000,
            ordering_guaranteed=True,
            duplicate_detection_enabled=True,
        )
        assert coordination.coordination_strategy == "immediate"
        assert coordination.ordering_guaranteed is True

        # Invalid buffer size for buffered coordination
        with pytest.raises(ValidationError):
            ModelEventCoordinationConfig(
                coordination_strategy="buffered",
                buffer_size=0,  # Must be positive for buffered strategy
            )

    def test_contract_orchestrator_creation(self):
        """Test ModelContractOrchestrator creation and validation."""
        event_descriptor = self.create_valid_event_descriptor()
        event_subscription = self.create_valid_event_subscription()

        contract = ModelContractOrchestrator(
            name="RSDWorkflowOrchestratorContract",
            version="1.0.0",
            description="Workflow coordination for RSD ticket processing",
            input_model="ModelWorkflowInput",
            output_model="ModelWorkflowOutput",
            published_events=[event_descriptor],
            consumed_events=[event_subscription],
            performance=ModelPerformanceRequirements(single_operation_max_ms=200),
        )

        assert contract.node_type == EnumNodeType.ORCHESTRATOR
        assert contract.name == "RSDWorkflowOrchestratorContract"
        assert len(contract.published_events) == 1
        assert len(contract.consumed_events) == 1
        assert contract.load_balancing_enabled is True

    def test_contract_orchestrator_validation_failures(self):
        """Test ModelContractOrchestrator validation failures."""
        # Duplicate published event names should fail
        event1 = self.create_valid_event_descriptor()
        event2 = self.create_valid_event_descriptor()  # Same name

        with pytest.raises(ValidationError):
            ModelContractOrchestrator(
                name="InvalidContract",
                version="1.0.0",
                description="Test contract",
                input_model="TestInput",
                output_model="TestOutput",
                published_events=[event1, event2],  # Duplicate event names
                performance=ModelPerformanceRequirements(single_operation_max_ms=100),
            )


class TestContractValidationFramework:
    """Test contract validation framework and compliance checking."""

    def test_protocol_dependency_validation(self):
        """Test protocol dependency naming validation."""
        # Valid protocol dependencies
        contract = ModelContractCompute(
            name="TestContract",
            version="1.0.0",
            description="Test contract",
            input_model="TestInput",
            output_model="TestOutput",
            algorithm=ModelAlgorithmConfig(
                algorithm_type="test",
                factors={
                    "test": ModelAlgorithmFactorConfig(
                        weight=1.0,
                        calculation_method="test",
                    ),
                },
            ),
            dependencies=["ProtocolRSDPriorityCalculator"],
            protocol_interfaces=["ProtocolComputeNode"],
            performance=ModelPerformanceRequirements(single_operation_max_ms=100),
        )
        assert len(contract.dependencies) == 1
        assert len(contract.protocol_interfaces) == 1

        # Invalid protocol dependency (doesn't start with "Protocol")
        with pytest.raises(ValidationError):
            ModelContractCompute(
                name="InvalidContract",
                version="1.0.0",
                description="Test contract",
                input_model="TestInput",
                output_model="TestOutput",
                algorithm=ModelAlgorithmConfig(
                    algorithm_type="test",
                    factors={
                        "test": ModelAlgorithmFactorConfig(
                            weight=1.0,
                            calculation_method="test",
                        ),
                    },
                ),
                dependencies=["InvalidDependency"],  # Must start with "Protocol"
                performance=ModelPerformanceRequirements(single_operation_max_ms=100),
            )

    def test_version_pattern_validation(self):
        """Test semantic version pattern validation."""
        # Valid version patterns
        valid_versions = ["1.0.0", "2.1.3", "10.20.30"]
        for version in valid_versions:
            contract = ModelContractCompute(
                name="TestContract",
                version=version,
                description="Test contract",
                input_model="TestInput",
                output_model="TestOutput",
                algorithm=ModelAlgorithmConfig(
                    algorithm_type="test",
                    factors={
                        "test": ModelAlgorithmFactorConfig(
                            weight=1.0,
                            calculation_method="test",
                        ),
                    },
                ),
                performance=ModelPerformanceRequirements(single_operation_max_ms=100),
            )
            assert contract.version == version

        # Invalid version patterns
        invalid_versions = ["1.0", "1.0.0.0", "v1.0.0", "1.0.0-beta"]
        for version in invalid_versions:
            with pytest.raises(ValidationError):
                ModelContractCompute(
                    name="TestContract",
                    version=version,  # Invalid pattern
                    description="Test contract",
                    input_model="TestInput",
                    output_model="TestOutput",
                    algorithm=ModelAlgorithmConfig(
                        algorithm_type="test",
                        factors={
                            "test": ModelAlgorithmFactorConfig(
                                weight=1.0,
                                calculation_method="test",
                            ),
                        },
                    ),
                    performance=ModelPerformanceRequirements(
                        single_operation_max_ms=100,
                    ),
                )

    def test_strong_typing_compliance(self):
        """Test that no Any types are used in contract models."""
        # This test verifies that the contract models maintain strong typing
        # by checking that all fields have proper type annotations

        from typing import get_type_hints

        # Check ModelContractBase
        base_hints = get_type_hints(ModelContractBase)
        for field_name, field_type in base_hints.items():
            assert field_type != Any, f"Field {field_name} uses Any type"
            assert "Any" not in str(
                field_type,
            ), f"Field {field_name} contains Any in type: {field_type}"

        # Check all specialized contract models
        contract_models = [
            ModelContractCompute,
            ModelContractEffect,
            ModelContractReducer,
            ModelContractOrchestrator,
        ]

        for model_class in contract_models:
            hints = get_type_hints(model_class)
            for field_name, field_type in hints.items():
                assert (
                    field_type != Any
                ), f"Field {field_name} in {model_class.__name__} uses Any type"
                assert "Any" not in str(
                    field_type,
                ), f"Field {field_name} in {model_class.__name__} contains Any: {field_type}"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden in contract models."""
        # This should raise ValidationError due to extra="forbid" in Config
        with pytest.raises(ValidationError):
            ModelContractCompute(
                name="TestContract",
                version="1.0.0",
                description="Test contract",
                input_model="TestInput",
                output_model="TestOutput",
                algorithm=ModelAlgorithmConfig(
                    algorithm_type="test",
                    factors={
                        "test": ModelAlgorithmFactorConfig(
                            weight=1.0,
                            calculation_method="test",
                        ),
                    },
                ),
                performance=ModelPerformanceRequirements(single_operation_max_ms=100),
                extra_field="This should cause validation error",  # Extra field not allowed
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
