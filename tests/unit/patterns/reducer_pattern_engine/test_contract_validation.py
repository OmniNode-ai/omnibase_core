"""Tests for contract validation in Reducer Pattern Engine Phase 3."""

import pytest
from pydantic import ValidationError

from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.contracts.model_contract_reducer_pattern_engine import (
    EnumDependencyType,
    ModelComponentSpecification,
    ModelContractReducerPatternEngine,
    ModelDependencyCollection,
    ModelDependencySpecification,
    ModelPatternConfiguration,
    ModelStateConfiguration,
    ModelSubreducerSpecification,
)


class TestContractValidation:
    """Test contract validation for Reducer Pattern Engine Phase 3."""

    @pytest.fixture
    def valid_contract_data(self):
        """Create valid contract data."""
        return {
            "name": "reducer_pattern_engine",
            "version": "1.0.0",
            "description": "Multi-workflow reducer pattern engine",
            "node_type": "REDUCER",
            "pattern_type": "execution_pattern",
            "pattern_config": {
                "supported_workflows": ["DATA_ANALYSIS", "REPORT_GENERATION"],
                "features": {
                    "instance_isolation": True,
                    "concurrent_processing": True,
                    "enhanced_metrics": True,
                    "registry_system": True,
                    "state_management": True,
                    "routing_optimization": True,
                },
                "max_concurrent_workflows": 50,
                "isolation_level": "instance_based",
                "architecture": "multi_workflow",
            },
            "components": {
                "engine": {
                    "class_name": "ReducerPatternEngine",
                    "module": "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine",
                    "description": "Main orchestration engine",
                },
                "router": {
                    "class_name": "WorkflowRouter",
                    "module": "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router",
                    "description": "Workflow routing component",
                },
                "registry": {
                    "class_name": "ReducerSubreducerRegistry",
                    "module": "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.registry",
                    "description": "Subreducer registry",
                },
                "metrics": {
                    "class_name": "ReducerMetricsCollector",
                    "module": "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.metrics",
                    "description": "Metrics collection component",
                },
            },
            "subreducers": {
                "data_analysis": {
                    "class_name": "ReducerDataAnalysisSubreducer",
                    "module": "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_data_analysis",
                    "supported_workflows": ["DATA_ANALYSIS"],
                    "capabilities": ["descriptive_statistics", "correlation_analysis"],
                },
                "report_generation": {
                    "class_name": "ReducerReportGenerationSubreducer",
                    "module": "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_report_generation",
                    "supported_workflows": ["REPORT_GENERATION"],
                    "capabilities": ["json_output", "html_output"],
                },
            },
            "state_management": {
                "state_model": "ModelWorkflowStateModel",
                "validator": "StateTransitionValidator",
                "states": [
                    {
                        "name": "PENDING",
                        "description": "Workflow awaiting processing",
                        "initial": True,
                    },
                    {"name": "PROCESSING", "description": "Workflow being processed"},
                    {
                        "name": "COMPLETED",
                        "description": "Workflow completed successfully",
                        "final": True,
                    },
                    {
                        "name": "FAILED",
                        "description": "Workflow processing failed",
                        "final": True,
                    },
                ],
                "transitions": [
                    {
                        "from": "PENDING",
                        "to": "PROCESSING",
                        "trigger": "start_processing",
                    },
                    {
                        "from": "PROCESSING",
                        "to": "COMPLETED",
                        "trigger": "complete_workflow",
                    },
                    {"from": "PROCESSING", "to": "FAILED", "trigger": "fail_workflow"},
                ],
            },
            "dependencies": {
                "structured_dependencies": [
                    {
                        "name": "container",
                        "dependency_type": "CONTAINER",
                        "class_name": "ModelONEXContainer",
                        "module": "omnibase_core.core.model_onex_container",
                    }
                ],
                "simple_dependencies": ["ProtocolContainer"],
                "dict_dependencies": [{"name": "metrics", "type": "service"}],
            },
        }

    def test_valid_contract_creation(self, valid_contract_data):
        """Test creating a valid contract."""
        contract = ModelContractReducerPatternEngine(**valid_contract_data)

        assert contract.name == "reducer_pattern_engine"
        assert str(contract.version) == "1.0.0"
        assert contract.node_type.value == "REDUCER"
        assert contract.pattern_type == "execution_pattern"

        # Validate pattern configuration
        assert len(contract.pattern_config.supported_workflows) == 2
        assert "DATA_ANALYSIS" in contract.pattern_config.supported_workflows
        assert contract.pattern_config.features["instance_isolation"] is True

        # Validate components
        assert "engine" in contract.components
        assert contract.components["engine"].class_name == "ReducerPatternEngine"

        # Validate subreducers
        assert "data_analysis" in contract.subreducers
        assert len(contract.subreducers["data_analysis"].supported_workflows) == 1

    def test_contract_validation_success(self, valid_contract_data):
        """Test successful contract validation."""
        contract = ModelContractReducerPatternEngine(**valid_contract_data)

        # Should not raise any exception
        contract.validate_node_specific_config()

    def test_pattern_configuration_validation(self):
        """Test pattern configuration validation."""
        # Test empty supported workflows - this should fail at the Pydantic validation level
        with pytest.raises(ValidationError):
            ModelPatternConfiguration(supported_workflows=[])

    def test_invalid_workflow_type_validation(self):
        """Test validation with invalid workflow type."""
        config = ModelPatternConfiguration(
            supported_workflows=["INVALID_WORKFLOW_TYPE"]
        )
        contract = ModelContractReducerPatternEngine(
            pattern_config=config, dependencies=["ProtocolContainer"]
        )
        with pytest.raises(ValueError, match="Unknown workflow type"):
            contract.validate_node_specific_config()

    def test_required_features_validation(self):
        """Test validation of required features."""
        # Test missing required feature
        config = ModelPatternConfiguration(
            supported_workflows=["DATA_ANALYSIS"],
            features={"instance_isolation": False, "state_management": True},
        )

        contract = ModelContractReducerPatternEngine(
            pattern_config=config, dependencies=["ProtocolContainer"]
        )
        with pytest.raises(
            ValueError, match="Required feature 'instance_isolation' must be enabled"
        ):
            contract.validate_node_specific_config()

    def test_component_specifications_validation(self):
        """Test component specifications validation."""
        # Test missing required component
        contract = ModelContractReducerPatternEngine(
            components={}, dependencies=["ProtocolContainer"]
        )

        with pytest.raises(
            ValueError, match="Required component 'engine' not specified"
        ):
            contract.validate_node_specific_config()

    def test_component_specification_fields(self):
        """Test component specification field validation."""
        # Test missing class_name - should fail at Pydantic validation level
        with pytest.raises(ValidationError):
            ModelComponentSpecification(
                class_name="", module="test.module", description="Test component"
            )

    def test_subreducer_specifications_validation(self):
        """Test subreducer specifications validation."""
        # Test no subreducers defined
        contract = ModelContractReducerPatternEngine(
            pattern_config=ModelPatternConfiguration(
                supported_workflows=["DATA_ANALYSIS"]
            ),
            subreducers={},
            dependencies=["ProtocolContainer"],
        )

        with pytest.raises(
            ValueError, match="Pattern must define at least one subreducer"
        ):
            contract.validate_node_specific_config()

    def test_workflow_coverage_validation(self):
        """Test validation of workflow type coverage by subreducers."""
        # Subreducer doesn't support all workflow types
        subreducer = ModelSubreducerSpecification(
            class_name="TestSubreducer",
            module="test.module",
            supported_workflows=["DATA_ANALYSIS"],
        )

        contract = ModelContractReducerPatternEngine(
            pattern_config=ModelPatternConfiguration(
                supported_workflows=["DATA_ANALYSIS", "REPORT_GENERATION"]
            ),
            subreducers={"test": subreducer},
            dependencies=["ProtocolContainer"],
        )

        with pytest.raises(ValueError, match="No subreducers defined for workflows"):
            contract.validate_node_specific_config()

    def test_state_management_validation(self):
        """Test state management configuration validation."""
        # Test no states defined
        state_config = ModelStateConfiguration(
            state_model="TestStateModel",
            validator="TestValidator",
            states=[],
            transitions=[],
        )

        contract = ModelContractReducerPatternEngine(
            state_management=state_config, dependencies=["ProtocolContainer"]
        )

        with pytest.raises(
            ValueError, match="State management must define at least one state"
        ):
            contract.validate_node_specific_config()

    def test_initial_state_validation(self):
        """Test initial state validation."""
        # Test no initial state
        state_config = ModelStateConfiguration(
            state_model="TestStateModel",
            validator="TestValidator",
            states=[
                {"name": "STATE1", "description": "Test state 1"},
                {"name": "STATE2", "description": "Test state 2"},
            ],
            transitions=[],
        )

        contract = ModelContractReducerPatternEngine(
            state_management=state_config, dependencies=["ProtocolContainer"]
        )

        with pytest.raises(
            ValueError, match="Exactly one initial state must be defined"
        ):
            contract.validate_node_specific_config()

    def test_final_state_validation(self):
        """Test final state validation."""
        # Test no final states
        state_config = ModelStateConfiguration(
            state_model="TestStateModel",
            validator="TestValidator",
            states=[
                {"name": "STATE1", "description": "Test state 1", "initial": True},
                {"name": "STATE2", "description": "Test state 2"},
            ],
            transitions=[],
        )

        contract = ModelContractReducerPatternEngine(
            state_management=state_config, dependencies=["ProtocolContainer"]
        )

        with pytest.raises(
            ValueError, match="At least one final state must be defined"
        ):
            contract.validate_node_specific_config()

    def test_dependency_validation(self):
        """Test dependency validation."""
        # Test missing required dependency
        deps = ModelDependencyCollection(
            structured_dependencies=[],
            simple_dependencies=["logger"],
            dict_dependencies=[],
        )

        contract = ModelContractReducerPatternEngine(
            enhanced_dependencies=deps, dependencies=["ProtocolContainer"]
        )

        with pytest.raises(ValueError, match="Required dependencies not found"):
            contract.validate_node_specific_config()

    def test_enhanced_dependency_collection_creation(self):
        """Test enhanced dependency collection creation."""
        # Test creating ModelDependencyCollection directly
        simple_deps = ["simple_dependency"]
        dict_deps = [{"name": "dict_dependency", "type": "service"}]
        structured_deps = [
            ModelDependencySpecification(
                name="structured_dependency",
                dependency_type=EnumDependencyType.PROTOCOL,
                class_name="TestClass",
                module="test.module",
            )
        ]

        deps_collection = ModelDependencyCollection(
            simple_dependencies=simple_deps,
            dict_dependencies=dict_deps,
            structured_dependencies=structured_deps,
        )

        assert isinstance(deps_collection, ModelDependencyCollection)
        assert len(deps_collection.simple_dependencies) == 1
        assert len(deps_collection.dict_dependencies) == 1
        assert len(deps_collection.structured_dependencies) == 1

        assert deps_collection.simple_dependencies[0] == "simple_dependency"
        assert deps_collection.dict_dependencies[0]["name"] == "dict_dependency"
        assert (
            deps_collection.structured_dependencies[0].name == "structured_dependency"
        )

    def test_dependency_specification_creation(self):
        """Test dependency specification creation."""
        dep_spec = ModelDependencySpecification(
            name="test_dependency",
            dependency_type=EnumDependencyType.PROTOCOL,
            class_name="TestClass",
            module="test.module",
        )

        assert dep_spec.name == "test_dependency"
        assert dep_spec.dependency_type == EnumDependencyType.PROTOCOL
        assert dep_spec.class_name == "TestClass"
        assert dep_spec.module == "test.module"

    def test_performance_requirements_override(self, valid_contract_data):
        """Test performance requirements override."""
        contract = ModelContractReducerPatternEngine(**valid_contract_data)

        # Should have pattern-specific performance requirements
        assert contract.performance.single_operation_max_ms == 30000
        assert contract.performance.batch_operation_max_s == 300
        assert contract.performance.memory_limit_mb == 2048
        assert contract.performance.cpu_limit_percent == 80
        assert contract.performance.throughput_min_ops_per_second == 10.0

    def test_lifecycle_configuration_override(self, valid_contract_data):
        """Test lifecycle configuration override."""
        contract = ModelContractReducerPatternEngine(**valid_contract_data)

        # Should have pattern-specific lifecycle configuration
        assert contract.lifecycle.initialization_timeout_s == 60
        assert contract.lifecycle.cleanup_timeout_s == 30
        assert contract.lifecycle.error_recovery_enabled is True
        assert contract.lifecycle.state_persistence_enabled is True
        assert contract.lifecycle.health_check_interval_s == 30

    def test_pattern_configuration_constraints(self):
        """Test pattern configuration constraints."""
        # Test max_concurrent_workflows constraints
        with pytest.raises(ValidationError):
            ModelPatternConfiguration(
                supported_workflows=["DATA_ANALYSIS"],
                max_concurrent_workflows=0,  # Should be >= 1
            )

        with pytest.raises(ValidationError):
            ModelPatternConfiguration(
                supported_workflows=["DATA_ANALYSIS"],
                max_concurrent_workflows=2000,  # Should be <= 1000
            )

    def test_subreducer_specification_constraints(self):
        """Test subreducer specification constraints."""
        # Test empty supported_workflows
        with pytest.raises(ValidationError):
            ModelSubreducerSpecification(
                class_name="TestSubreducer",
                module="test.module",
                supported_workflows=[],  # Should have at least 1
            )

    def test_component_specification_constraints(self):
        """Test component specification constraints."""
        # Test empty class_name
        with pytest.raises(ValidationError):
            ModelComponentSpecification(
                class_name="",  # Should have at least 1 character
                module="test.module",
                description="Test component",
            )

        # Test empty module
        with pytest.raises(ValidationError):
            ModelComponentSpecification(
                class_name="TestClass",
                module="",  # Should have at least 1 character
                description="Test component",
            )

    def test_dependency_specification_constraints(self):
        """Test dependency specification constraints."""
        # Test empty name
        with pytest.raises(ValidationError):
            ModelDependencySpecification(
                name="",  # Should have at least 1 character
                dependency_type=EnumDependencyType.SERVICE,
                class_name="TestClass",
                module="test.module",
            )

    def test_contract_model_config(self):
        """Test contract model configuration."""
        contract = ModelContractReducerPatternEngine(dependencies=["ProtocolContainer"])

        # Test model configuration - access it via model_config in Pydantic v2
        config = contract.model_config
        assert config["extra"] == "ignore"
        assert config["use_enum_values"] is False
        assert config["validate_assignment"] is True
        assert config["str_strip_whitespace"] is True
