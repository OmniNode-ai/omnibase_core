"""
Tests for ReducerSubreducerRegistry - Manual subreducer registration system.

Tests comprehensive subreducer registration, validation, health checks,
and runtime lookup capabilities for the Phase 2 implementation.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    BaseSubreducer,
    ModelSubreducerResult,
    ModelWorkflowRequest,
    WorkflowType,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.registry import (
    ReducerSubreducerRegistry,
    RegistryError,
)


class MockValidSubreducer(BaseSubreducer):
    """Valid mock subreducer for testing."""

    def __init__(self, name: str = "mock_valid_subreducer"):
        super().__init__(name)
        self._supported_types = [WorkflowType.DATA_ANALYSIS]

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type in self._supported_types

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        return ModelSubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=True,
            result={"mock": "success"},
        )


class MockMultiTypeSubreducer(BaseSubreducer):
    """Mock subreducer supporting multiple workflow types."""

    def __init__(self, name: str = "mock_multi_subreducer"):
        super().__init__(name)
        self._supported_types = [
            WorkflowType.DATA_ANALYSIS,
            WorkflowType.REPORT_GENERATION,
        ]

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type in self._supported_types

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        return ModelSubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=True,
            result={"supported_type": workflow_type.value},
        )


class MockFailingSubreducer(BaseSubreducer):
    """Mock subreducer that always fails during processing."""

    def __init__(self, name: str = "mock_failing_subreducer"):
        super().__init__(name)

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type == WorkflowType.DOCUMENT_REGENERATION

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        return ModelSubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=False,
            error_message="Mock failure",
        )


class MockInvalidSubreducer:
    """Invalid class that doesn't inherit from BaseSubreducer."""

    def __init__(self, name: str = "invalid"):
        self.name = name


class MockUninstantiableSubreducer(BaseSubreducer):
    """Subreducer that fails during instantiation."""

    def __init__(self, name: str):
        if name == "test_data_analysis_subreducer":
            raise ValueError("Mock instantiation failure")
        super().__init__(name)

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type == WorkflowType.DATA_ANALYSIS

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        return ModelSubreducerResult(
            workflow_id=uuid4(),
            subreducer_name=self.name,
            success=True,
            result={},
        )


class TestReducerSubreducerRegistry:
    """Test suite for ReducerSubreducerRegistry functionality."""

    @pytest.fixture
    def registry(self) -> ReducerSubreducerRegistry:
        """Create a fresh registry instance for testing."""
        return ReducerSubreducerRegistry()

    def test_registry_initialization(self, registry):
        """Test proper registry initialization."""
        assert len(registry._subreducers) == 0
        assert len(registry._subreducer_instances) == 0
        assert len(registry._registration_metadata) == 0
        assert registry.list_registered_workflows() == []

    def test_register_valid_subreducer(self, registry):
        """Test registering a valid subreducer."""
        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS
        metadata = {"test": "registration", "version": "1.0"}

        # Register subreducer
        registry.register_subreducer(workflow_type, subreducer_class, metadata)

        # Verify registration
        assert workflow_type.value in registry._subreducers
        assert registry._subreducers[workflow_type.value] == subreducer_class

        # Verify metadata
        reg_metadata = registry._registration_metadata[workflow_type.value]
        assert reg_metadata["class_name"] == "MockValidSubreducer"
        assert reg_metadata["metadata"] == metadata
        assert "registered_at" in reg_metadata

        # Verify it's listed
        registered_workflows = registry.list_registered_workflows()
        assert workflow_type.value in registered_workflows

    def test_register_multiple_workflow_types(self, registry):
        """Test registering subreducer for multiple workflow types."""
        subreducer_class = MockMultiTypeSubreducer
        workflow_types = [WorkflowType.DATA_ANALYSIS, WorkflowType.REPORT_GENERATION]

        # Register for multiple types
        for workflow_type in workflow_types:
            registry.register_subreducer(workflow_type, subreducer_class)

        # Verify all types are registered
        registered_workflows = registry.list_registered_workflows()
        for workflow_type in workflow_types:
            assert workflow_type.value in registered_workflows
            assert registry._subreducers[workflow_type.value] == subreducer_class

    def test_register_invalid_subreducer_class(self, registry):
        """Test registering invalid subreducer class raises error."""
        invalid_class = MockInvalidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS

        with pytest.raises(RegistryError) as exc_info:
            registry.register_subreducer(workflow_type, invalid_class)

        assert "must inherit from BaseSubreducer" in str(exc_info.value)

        # Verify nothing was registered
        assert len(registry._subreducers) == 0

    def test_register_uninstantiable_subreducer(self, registry):
        """Test registering subreducer that fails instantiation."""
        uninstantiable_class = MockUninstantiableSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS

        with pytest.raises(RegistryError) as exc_info:
            registry.register_subreducer(workflow_type, uninstantiable_class)

        assert "Failed to instantiate subreducer" in str(exc_info.value)
        assert "Mock instantiation failure" in str(exc_info.value)

        # Verify nothing was registered
        assert len(registry._subreducers) == 0

    def test_register_subreducer_with_unsupported_type(self, registry):
        """Test registering subreducer for workflow type it doesn't support."""
        subreducer_class = MockValidSubreducer  # Only supports DATA_ANALYSIS
        workflow_type = WorkflowType.REPORT_GENERATION  # Not supported

        with pytest.raises(RegistryError) as exc_info:
            registry.register_subreducer(workflow_type, subreducer_class)

        assert "does not support workflow type" in str(exc_info.value)

        # Verify nothing was registered
        assert len(registry._subreducers) == 0

    def test_overwrite_existing_registration(self, registry):
        """Test overwriting existing subreducer registration."""
        workflow_type = WorkflowType.DATA_ANALYSIS

        # Register first subreducer
        registry.register_subreducer(workflow_type, MockValidSubreducer)
        assert registry._subreducers[workflow_type.value] == MockValidSubreducer

        # Register different subreducer for same type (should overwrite)
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.registry.emit_log_event",
        ):
            registry.register_subreducer(workflow_type, MockMultiTypeSubreducer)

        # Verify overwrite
        assert registry._subreducers[workflow_type.value] == MockMultiTypeSubreducer

        # Should still be only one registered workflow type
        assert len(registry.list_registered_workflows()) == 1

    def test_get_subreducer(self, registry):
        """Test getting registered subreducer class."""
        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS

        # Should return None for unregistered type
        assert registry.get_subreducer(WorkflowType.REPORT_GENERATION) is None

        # Register subreducer
        registry.register_subreducer(workflow_type, subreducer_class)

        # Should return the registered class
        retrieved_class = registry.get_subreducer(workflow_type)
        assert retrieved_class == subreducer_class

        # Test with string workflow type
        retrieved_class_str = registry.get_subreducer(workflow_type.value)
        assert retrieved_class_str == subreducer_class

    def test_get_subreducer_instance(self, registry):
        """Test getting subreducer instance with caching."""
        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS

        # Should return None for unregistered type
        assert registry.get_subreducer_instance(WorkflowType.REPORT_GENERATION) is None

        # Register subreducer
        registry.register_subreducer(workflow_type, subreducer_class)

        # Get instance (should create new one)
        instance1 = registry.get_subreducer_instance(workflow_type)
        assert instance1 is not None
        assert isinstance(instance1, MockValidSubreducer)
        assert instance1.name == "data_analysis_subreducer"

        # Get instance again (should return cached one)
        instance2 = registry.get_subreducer_instance(workflow_type)
        assert instance2 is instance1  # Same object

        # Verify instance is cached
        assert workflow_type.value in registry._subreducer_instances
        assert registry._subreducer_instances[workflow_type.value] is instance1

    def test_get_subreducer_instance_creation_failure(self, registry):
        """Test handling instance creation failure."""

        # Register a subreducer class that will fail during instance creation
        # but only when creating actual instances (not during validation)
        class FailingInstanceSubreducer(BaseSubreducer):
            def __init__(self, name: str):
                if "subreducer" in name and name != "test_data_analysis_subreducer":
                    raise RuntimeError("Instance creation failed")
                super().__init__(name)

            def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
                return workflow_type == WorkflowType.DATA_ANALYSIS

            async def process(
                self,
                request: ModelWorkflowRequest,
            ) -> ModelSubreducerResult:
                return ModelSubreducerResult(uuid4(), self.name, True, {})

        workflow_type = WorkflowType.DATA_ANALYSIS
        registry.register_subreducer(workflow_type, FailingInstanceSubreducer)

        # Try to get instance (should fail and return None)
        instance = registry.get_subreducer_instance(workflow_type)
        assert instance is None

        # Verify no instance was cached
        assert workflow_type.value not in registry._subreducer_instances

    def test_unregister_subreducer(self, registry):
        """Test unregistering subreducers."""
        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS

        # Register subreducer and get instance to cache it
        registry.register_subreducer(workflow_type, subreducer_class)
        instance = registry.get_subreducer_instance(workflow_type)
        assert instance is not None

        # Unregister
        result = registry.unregister_subreducer(workflow_type)
        assert result is True

        # Verify removal
        assert workflow_type.value not in registry._subreducers
        assert workflow_type.value not in registry._subreducer_instances
        assert workflow_type.value not in registry._registration_metadata
        assert len(registry.list_registered_workflows()) == 0

        # Try to unregister non-existent (should return False)
        result = registry.unregister_subreducer(WorkflowType.REPORT_GENERATION)
        assert result is False

    def test_validate_registration(self, registry):
        """Test registration validation."""
        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS

        # Should return False for unregistered type
        assert registry.validate_registration(workflow_type) is False

        # Register subreducer
        registry.register_subreducer(workflow_type, subreducer_class)

        # Should return True for valid registration
        assert registry.validate_registration(workflow_type) is True

        # Should return False for registered type that doesn't support the workflow
        wrong_type = WorkflowType.REPORT_GENERATION
        assert registry.validate_registration(wrong_type) is False

    def test_validate_registration_with_instantiation_failure(self, registry):
        """Test validation when instance creation fails during validation."""

        # Create a subreducer class that will fail during validation instantiation
        class ValidationFailingSubreducer(BaseSubreducer):
            def __init__(self, name: str):
                if "validation_" in name:
                    raise RuntimeError("Validation instantiation failed")
                super().__init__(name)

            def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
                return workflow_type == WorkflowType.DATA_ANALYSIS

            async def process(
                self,
                request: ModelWorkflowRequest,
            ) -> ModelSubreducerResult:
                return ModelSubreducerResult(uuid4(), self.name, True, {})

        # This should succeed during registration (uses "test_" prefix)
        workflow_type = WorkflowType.DATA_ANALYSIS
        registry.register_subreducer(workflow_type, ValidationFailingSubreducer)

        # But validation should fail (uses "validation_" prefix)
        assert registry.validate_registration(workflow_type) is False

    def test_health_check_subreducers(self, registry):
        """Test health checks on registered subreducers."""
        # Empty registry should return empty health status
        health_status = registry.health_check_subreducers()
        assert health_status == {}

        # Register multiple subreducers
        subreducers = [
            (WorkflowType.DATA_ANALYSIS, MockValidSubreducer),
            (WorkflowType.REPORT_GENERATION, MockMultiTypeSubreducer),
            (WorkflowType.DOCUMENT_REGENERATION, MockFailingSubreducer),
        ]

        for workflow_type, subreducer_class in subreducers:
            registry.register_subreducer(workflow_type, subreducer_class)

        # Run health checks
        health_status = registry.health_check_subreducers()

        # Verify health status
        assert len(health_status) == 3
        assert health_status[WorkflowType.DATA_ANALYSIS.value] is True
        assert health_status[WorkflowType.REPORT_GENERATION.value] is True
        assert health_status[WorkflowType.DOCUMENT_REGENERATION.value] is True

        # All should be healthy since they support their registered types
        assert all(health_status.values())

    def test_health_check_with_invalid_workflow_type(self, registry):
        """Test health check handling of invalid workflow types."""
        # Manually add invalid entry to registry
        registry._subreducers["invalid_workflow_type"] = MockValidSubreducer

        # Health check should handle invalid workflow type gracefully
        health_status = registry.health_check_subreducers()
        assert "invalid_workflow_type" in health_status
        assert health_status["invalid_workflow_type"] is False

    def test_health_check_with_instance_creation_failure(self, registry):
        """Test health check when instance creation fails."""

        # Register subreducer that will fail during instance creation
        class HealthCheckFailingSubreducer(BaseSubreducer):
            def __init__(self, name: str):
                if "subreducer" in name and name != "test_data_analysis_subreducer":
                    raise RuntimeError("Health check instance creation failed")
                super().__init__(name)

            def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
                return workflow_type == WorkflowType.DATA_ANALYSIS

            async def process(
                self,
                request: ModelWorkflowRequest,
            ) -> ModelSubreducerResult:
                return ModelSubreducerResult(uuid4(), self.name, True, {})

        workflow_type = WorkflowType.DATA_ANALYSIS
        registry.register_subreducer(workflow_type, HealthCheckFailingSubreducer)

        # Health check should fail gracefully
        health_status = registry.health_check_subreducers()
        assert health_status[workflow_type.value] is False

    def test_get_registration_metadata(self, registry):
        """Test getting registration metadata."""
        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS
        test_metadata = {"version": "2.0", "author": "test"}

        # Should return None for unregistered type
        assert registry.get_registration_metadata(workflow_type) is None

        # Register with metadata
        registry.register_subreducer(workflow_type, subreducer_class, test_metadata)

        # Get metadata
        metadata = registry.get_registration_metadata(workflow_type)
        assert metadata is not None
        assert metadata["class_name"] == "MockValidSubreducer"
        assert metadata["metadata"] == test_metadata
        assert "registered_at" in metadata
        assert isinstance(metadata["registered_at"], float)

    def test_get_registry_summary(self, registry):
        """Test comprehensive registry summary."""
        # Empty registry summary
        summary = registry.get_registry_summary()
        assert summary["total_registered"] == 0
        assert summary["workflow_types"] == []
        assert summary["active_instances"] == 0
        assert summary["health_status"] == {}
        assert summary["registration_metadata"] == {}

        # Register multiple subreducers
        subreducers_config = [
            (WorkflowType.DATA_ANALYSIS, MockValidSubreducer, {"version": "1.0"}),
            (
                WorkflowType.REPORT_GENERATION,
                MockMultiTypeSubreducer,
                {"version": "1.1"},
            ),
        ]

        for workflow_type, subreducer_class, metadata in subreducers_config:
            registry.register_subreducer(workflow_type, subreducer_class, metadata)

        # Create instance for one type
        registry.get_subreducer_instance(WorkflowType.DATA_ANALYSIS)

        # Get updated summary
        summary = registry.get_registry_summary()

        # Verify summary
        assert summary["total_registered"] == 2
        assert len(summary["workflow_types"]) == 2
        assert WorkflowType.DATA_ANALYSIS.value in summary["workflow_types"]
        assert WorkflowType.REPORT_GENERATION.value in summary["workflow_types"]
        assert summary["active_instances"] == 1  # Only one instance created

        # Verify health status
        health_status = summary["health_status"]
        assert len(health_status) == 2
        assert all(health_status.values())  # All should be healthy

        # Verify metadata
        reg_metadata = summary["registration_metadata"]
        assert len(reg_metadata) == 2
        assert (
            reg_metadata[WorkflowType.DATA_ANALYSIS.value]["metadata"]["version"]
            == "1.0"
        )
        assert (
            reg_metadata[WorkflowType.REPORT_GENERATION.value]["metadata"]["version"]
            == "1.1"
        )

    def test_clear_registry(self, registry):
        """Test clearing the entire registry."""
        # Register some subreducers
        registry.register_subreducer(WorkflowType.DATA_ANALYSIS, MockValidSubreducer)
        registry.register_subreducer(
            WorkflowType.REPORT_GENERATION,
            MockMultiTypeSubreducer,
        )

        # Create instances
        registry.get_subreducer_instance(WorkflowType.DATA_ANALYSIS)
        registry.get_subreducer_instance(WorkflowType.REPORT_GENERATION)

        # Verify registry has content
        assert len(registry._subreducers) == 2
        assert len(registry._subreducer_instances) == 2
        assert len(registry._registration_metadata) == 2

        # Clear registry
        registry.clear_registry()

        # Verify everything is cleared
        assert len(registry._subreducers) == 0
        assert len(registry._subreducer_instances) == 0
        assert len(registry._registration_metadata) == 0
        assert registry.list_registered_workflows() == []

        # Summary should reflect cleared state
        summary = registry.get_registry_summary()
        assert summary["total_registered"] == 0
        assert summary["active_instances"] == 0

    def test_string_workflow_type_handling(self, registry):
        """Test handling of string workflow types versus enum."""
        subreducer_class = MockValidSubreducer
        workflow_type_enum = WorkflowType.DATA_ANALYSIS
        workflow_type_str = "data_analysis"

        # Register with enum
        registry.register_subreducer(workflow_type_enum, subreducer_class)

        # Should be retrievable with both enum and string
        assert registry.get_subreducer(workflow_type_enum) == subreducer_class
        assert registry.get_subreducer(workflow_type_str) == subreducer_class

        # Instance retrieval should work with both
        instance1 = registry.get_subreducer_instance(workflow_type_enum)
        instance2 = registry.get_subreducer_instance(workflow_type_str)
        assert instance1 is instance2  # Same cached instance

        # Validation should work with both
        assert registry.validate_registration(workflow_type_enum) is True
        assert registry.validate_registration(workflow_type_str) is True

        # Metadata retrieval should work with both
        metadata1 = registry.get_registration_metadata(workflow_type_enum)
        metadata2 = registry.get_registration_metadata(workflow_type_str)
        assert metadata1 == metadata2

        # Unregistration should work with both
        registry.register_subreducer(
            WorkflowType.REPORT_GENERATION,
            MockMultiTypeSubreducer,
        )
        assert registry.unregister_subreducer(WorkflowType.REPORT_GENERATION) is True
        assert WorkflowType.REPORT_GENERATION.value not in registry._subreducers

    def test_concurrent_access_safety(self, registry):
        """Test registry behavior under concurrent access patterns."""
        import threading

        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS
        results = {"success": 0, "failure": 0}

        def register_and_get_instance(thread_id: int):
            try:
                # Each thread tries to register (later ones should overwrite)
                registry.register_subreducer(
                    workflow_type,
                    subreducer_class,
                    {"thread_id": thread_id},
                )

                # Each thread tries to get instance
                instance = registry.get_subreducer_instance(workflow_type)
                if instance is not None:
                    results["success"] += 1
                else:
                    results["failure"] += 1

            except Exception:
                results["failure"] += 1

        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_and_get_instance, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert results["success"] > 0
        assert results["failure"] == 0  # Should not have any failures

        # Verify final state consistency
        summary = registry.get_registry_summary()
        assert summary["total_registered"] == 1  # Only one type registered
        assert summary["active_instances"] == 1  # Only one instance
        assert len(summary["workflow_types"]) == 1

    def test_edge_case_empty_name_subreducer(self, registry):
        """Test registration with subreducer having empty name."""

        class EmptyNameSubreducer(BaseSubreducer):
            def __init__(self, name: str = ""):
                super().__init__(name)

            def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
                return workflow_type == WorkflowType.DATA_ANALYSIS

            async def process(
                self,
                request: ModelWorkflowRequest,
            ) -> ModelSubreducerResult:
                return ModelSubreducerResult(uuid4(), self.name, True, {})

        # Should be able to register subreducer with empty name
        workflow_type = WorkflowType.DATA_ANALYSIS
        registry.register_subreducer(workflow_type, EmptyNameSubreducer)

        # Should be able to get instance
        instance = registry.get_subreducer_instance(workflow_type)
        assert instance is not None
        assert instance.name == "data_analysis_subreducer"  # Auto-generated name

    def test_metadata_immutability(self, registry):
        """Test that returned metadata cannot be modified to affect registry."""
        subreducer_class = MockValidSubreducer
        workflow_type = WorkflowType.DATA_ANALYSIS
        original_metadata = {"version": "1.0", "mutable": "original"}

        # Register with metadata
        registry.register_subreducer(workflow_type, subreducer_class, original_metadata)

        # Get metadata and modify it
        retrieved_metadata = registry.get_registration_metadata(workflow_type)
        retrieved_metadata["metadata"]["mutable"] = "modified"
        retrieved_metadata["metadata"]["new_key"] = "new_value"

        # Get fresh copy of metadata
        fresh_metadata = registry.get_registration_metadata(workflow_type)

        # Original metadata should be unchanged
        assert fresh_metadata["metadata"]["mutable"] == "original"
        assert "new_key" not in fresh_metadata["metadata"]

        # Same test for registry summary
        summary = registry.get_registry_summary()
        summary["registration_metadata"][workflow_type.value]["metadata"][
            "another_modification"
        ] = "test"

        fresh_summary = registry.get_registry_summary()
        assert (
            "another_modification"
            not in fresh_summary["registration_metadata"][workflow_type.value][
                "metadata"
            ]
        )
