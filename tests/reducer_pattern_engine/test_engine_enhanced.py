"""
Enhanced tests for ReducerPatternEngine Phase 2 features.

Tests comprehensive Phase 2 functionality including multi-workflow support,
enhanced metrics collection, registry integration, state management, and
comprehensive error handling with real subreducer integration.
"""

import asyncio
import pytest
import time
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from omnibase_core.core.model_onex_container import ModelONEXContainer
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine import ReducerPatternEngine
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.contracts import (
    WorkflowRequest,
    WorkflowResponse,
    WorkflowType,
    WorkflowStatus,
    BaseSubreducer,
    SubreducerResult
)
from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
    WorkflowState,
    WorkflowStateModel
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_data_analysis import (
    ReducerDataAnalysisSubreducer
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_report_generation import (
    ReducerReportGenerationSubreducer
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration import (
    ReducerDocumentRegenerationSubreducer
)


class TestEnhancedSubreducer(BaseSubreducer):
    """Enhanced test subreducer with configurable behavior for testing."""
    
    def __init__(self, name: str, supported_types: List[WorkflowType], 
                 processing_time: float = 0.1, success_rate: float = 1.0):
        super().__init__(name)
        self._supported_types = supported_types
        self._processing_time = processing_time
        self._success_rate = success_rate
        self._call_count = 0
        self._processed_requests = []
    
    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type in self._supported_types
    
    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        """Enhanced processing with configurable behavior."""
        self._call_count += 1
        self._processed_requests.append(request)
        
        # Simulate processing time
        await asyncio.sleep(self._processing_time)
        
        # Simulate success/failure based on success rate
        import random
        should_succeed = random.random() <= self._success_rate
        
        if should_succeed:
            return SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=True,
                result={
                    "enhanced_processing": True,
                    "call_number": self._call_count,
                    "workflow_type": request.workflow_type.value,
                    "instance_id": request.instance_id,
                    "processing_time_ms": self._processing_time * 1000,
                    "payload_summary": f"Processed {len(str(request.payload))} chars of payload"
                },
                processing_time_ms=self._processing_time * 1000
            )
        else:
            return SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=False,
                error_message=f"Simulated failure (call #{self._call_count})",
                error_details={
                    "call_number": self._call_count,
                    "failure_reason": "configured_failure",
                    "success_rate": self._success_rate
                }
            )
    
    @property
    def call_count(self) -> int:
        return self._call_count
    
    @property 
    def processed_requests(self) -> List[WorkflowRequest]:
        return self._processed_requests.copy()


class TestReducerPatternEngineEnhanced:
    """Enhanced test suite for ReducerPatternEngine Phase 2 functionality."""
    
    @pytest.fixture
    def mock_container(self) -> ModelONEXContainer:
        """Create a mock ONEX container for testing."""
        container = MagicMock(spec=ModelONEXContainer)
        return container
    
    @pytest.fixture
    def engine(self, mock_container) -> ReducerPatternEngine:
        """Create a ReducerPatternEngine instance for testing."""
        return ReducerPatternEngine(mock_container)
    
    @pytest.fixture
    def sample_requests(self) -> Dict[str, WorkflowRequest]:
        """Create comprehensive sample workflow requests."""
        base_correlation_id = uuid4()
        
        return {
            "data_analysis": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id="enhanced-data-001",
                correlation_id=base_correlation_id,
                payload={
                    "data": [10, 15, 20, 25, 30, 35, 40, 45, 50],
                    "analysis_types": ["descriptive", "trend"],
                    "data_validation": {"remove_outliers": False},
                    "test_scenario": "enhanced_testing"
                },
                metadata={"priority": "high", "enhanced_test": True}
            ),
            "report_generation": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id="enhanced-report-001",
                correlation_id=base_correlation_id,
                payload={
                    "template_type": "summary",
                    "output_format": "json",
                    "data": {"metrics": [85, 90, 92], "status": "complete"},
                    "report_title": "Enhanced Test Report",
                    "test_scenario": "enhanced_testing"
                },
                metadata={"department": "testing", "enhanced_test": True}
            ),
            "document_regeneration": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="enhanced-doc-001",
                correlation_id=base_correlation_id,
                payload={
                    "document_id": "enhanced-test-doc-123",
                    "regeneration_mode": "full",
                    "template": "standard",
                    "test_scenario": "enhanced_testing"
                },
                metadata={"user": "enhanced_test", "enhanced_test": True}
            )
        }
    
    def test_enhanced_engine_initialization(self, engine):
        """Test enhanced engine initialization with Phase 2 components."""
        # Verify Phase 2 components are initialized
        assert hasattr(engine, '_registry')
        assert hasattr(engine, '_metrics_collector')
        assert hasattr(engine, '_workflow_states')
        assert hasattr(engine, '_active_workflows')
        
        # Verify initial state
        assert len(engine._active_workflows) == 0
        assert len(engine._workflow_states) == 0
        
        # Verify methods are available
        assert hasattr(engine, 'get_comprehensive_metrics')
        assert hasattr(engine, 'get_registry_summary')
        assert hasattr(engine, 'get_workflow_state')
        assert hasattr(engine, 'list_supported_workflow_types')
    
    @pytest.mark.asyncio
    async def test_enhanced_workflow_processing_with_state_tracking(self, engine, sample_requests):
        """Test enhanced workflow processing with comprehensive state tracking."""
        
        # Register enhanced test subreducers
        for workflow_name, request in sample_requests.items():
            enhanced_subreducer = TestEnhancedSubreducer(
                name=f"enhanced_{workflow_name}",
                supported_types=[request.workflow_type],
                processing_time=0.1,
                success_rate=1.0
            )
            engine.register_subreducer(enhanced_subreducer, [request.workflow_type])
        
        # Process a workflow and track state changes
        request = sample_requests["data_analysis"]
        
        # Start processing in background to observe state changes
        processing_task = asyncio.create_task(engine.process_workflow(request))
        
        # Give it a moment to start
        await asyncio.sleep(0.05)
        
        # Check intermediate state
        workflow_state = engine.get_workflow_state(str(request.workflow_id))
        assert workflow_state is not None
        assert workflow_state.workflow_id == request.workflow_id
        assert workflow_state.current_state in [WorkflowState.PENDING, WorkflowState.PROCESSING]
        
        # Check active workflows
        active_workflows = engine.get_active_workflows()
        assert str(request.workflow_id) in active_workflows
        
        # Wait for completion
        response = await processing_task
        
        # Verify successful completion
        assert response.status == WorkflowStatus.COMPLETED
        assert response.result is not None
        assert response.result["enhanced_processing"] is True
        
        # Verify final state
        final_state = engine.get_workflow_state(str(request.workflow_id))
        assert final_state.current_state == WorkflowState.COMPLETED
        assert final_state.is_terminal_state() is True
        
        # Verify no longer active
        final_active = engine.get_active_workflows()
        assert str(request.workflow_id) not in final_active
    
    @pytest.mark.asyncio
    async def test_comprehensive_metrics_collection_integration(self, engine, sample_requests):
        """Test integration with comprehensive metrics collection system."""
        
        # Register enhanced subreducers with different characteristics
        subreducer_configs = [
            ("data_analysis", 0.15, 1.0),     # Slow, always succeeds
            ("report_generation", 0.08, 0.9),  # Fast, mostly succeeds
            ("document_regeneration", 0.12, 0.8)  # Medium, sometimes fails
        ]
        
        enhanced_subreducers = {}
        for workflow_name, processing_time, success_rate in subreducer_configs:
            request = sample_requests[workflow_name]
            enhanced_subreducer = TestEnhancedSubreducer(
                name=f"metrics_{workflow_name}",
                supported_types=[request.workflow_type],
                processing_time=processing_time,
                success_rate=success_rate
            )
            enhanced_subreducers[workflow_name] = enhanced_subreducer
            engine.register_subreducer(enhanced_subreducer, [request.workflow_type])
        
        # Process multiple rounds of workflows
        total_processed = 0
        for round_num in range(3):
            round_tasks = []
            for workflow_name, request in sample_requests.items():
                # Create unique request for this round
                round_request = WorkflowRequest(
                    workflow_id=uuid4(),
                    workflow_type=request.workflow_type,
                    instance_id=f"{request.instance_id}-round-{round_num}",
                    correlation_id=uuid4(),
                    payload={**request.payload, "round": round_num},
                    metadata={**request.metadata, "round": round_num}
                )
                
                task = asyncio.create_task(engine.process_workflow(round_request))
                round_tasks.append((workflow_name, task))
                total_processed += 1
            
            # Wait for round completion
            for workflow_name, task in round_tasks:
                response = await task
                # Some may fail based on success rate, that's expected
        
        # Verify comprehensive metrics
        comprehensive_metrics = engine.get_comprehensive_metrics()
        
        # Check legacy metrics
        legacy_metrics = comprehensive_metrics["legacy_metrics"]
        assert legacy_metrics["total_workflows_processed"] == total_processed
        
        # Check enhanced metrics
        enhanced_metrics = comprehensive_metrics["enhanced_metrics"]
        assert enhanced_metrics["total_workflows_processed"] == total_processed
        assert "overall_success_rate" in enhanced_metrics
        assert enhanced_metrics["uptime_seconds"] > 0
        
        # Check registry status
        registry_status = comprehensive_metrics["registry_status"]
        assert registry_status["total_registered"] == 3
        assert len(registry_status["workflow_types"]) == 3
        
        # Check workflow type specific metrics
        for workflow_name in sample_requests.keys():
            workflow_type = sample_requests[workflow_name].workflow_type.value
            type_metrics = engine.get_workflow_type_metrics(workflow_type)
            assert type_metrics is not None
            assert type_metrics["total_processed"] == 3  # 3 rounds
    
    @pytest.mark.asyncio
    async def test_registry_integration_and_management(self, engine):
        """Test comprehensive registry integration and management."""
        
        # Test initial empty registry
        registry_summary = engine.get_registry_summary()
        assert registry_summary["total_registered"] == 0
        assert registry_summary["active_instances"] == 0
        
        # Test multiple subreducer registration
        subreducers_to_register = [
            TestEnhancedSubreducer("registry_test_1", [WorkflowType.DATA_ANALYSIS]),
            TestEnhancedSubreducer("registry_test_2", [WorkflowType.REPORT_GENERATION]),
            TestEnhancedSubreducer("registry_test_3", [WorkflowType.DOCUMENT_REGENERATION])
        ]
        
        for subreducer in subreducers_to_register:
            workflow_types = subreducer._supported_types
            engine.register_subreducer(subreducer, workflow_types)
        
        # Test registry state after registration
        updated_summary = engine.get_registry_summary()
        assert updated_summary["total_registered"] == 3
        assert len(updated_summary["workflow_types"]) == 3
        
        # Test supported workflow types listing
        supported_types = engine.list_supported_workflow_types()
        expected_types = {"data_analysis", "report_generation", "document_regeneration"}
        assert set(supported_types) == expected_types
        
        # Test health checks
        health_status = engine.health_check_subreducers()
        assert len(health_status) == 3
        assert all(health_status.values())  # All should be healthy
        
        # Test bulk registration
        bulk_configs = [
            {
                'subreducer': TestEnhancedSubreducer("bulk_test_1", [WorkflowType.DATA_ANALYSIS]),
                'workflow_types': [WorkflowType.DATA_ANALYSIS]
            }
        ]
        
        bulk_results = engine.register_multiple_subreducers(bulk_configs)
        assert len(bulk_results) == 1
        assert all(bulk_results.values())  # Should succeed
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_scenarios(self, engine, sample_requests):
        """Test comprehensive error handling and recovery scenarios."""
        
        # Register subreducers with different failure modes
        failing_subreducer = TestEnhancedSubreducer(
            name="failing_subreducer",
            supported_types=[WorkflowType.DATA_ANALYSIS],
            success_rate=0.0  # Always fails
        )
        
        intermittent_subreducer = TestEnhancedSubreducer(
            name="intermittent_subreducer", 
            supported_types=[WorkflowType.REPORT_GENERATION],
            success_rate=0.5  # 50% failure rate
        )
        
        reliable_subreducer = TestEnhancedSubreducer(
            name="reliable_subreducer",
            supported_types=[WorkflowType.DOCUMENT_REGENERATION],
            success_rate=1.0  # Always succeeds
        )
        
        engine.register_subreducer(failing_subreducer, [WorkflowType.DATA_ANALYSIS])
        engine.register_subreducer(intermittent_subreducer, [WorkflowType.REPORT_GENERATION])
        engine.register_subreducer(reliable_subreducer, [WorkflowType.DOCUMENT_REGENERATION])
        
        # Test processing with guaranteed failure
        failing_request = sample_requests["data_analysis"]
        failing_response = await engine.process_workflow(failing_request)
        
        assert failing_response.status == WorkflowStatus.FAILED
        assert failing_response.error_message is not None
        assert "Simulated failure" in failing_response.error_message
        
        # Verify state tracking for failed workflow
        failed_state = engine.get_workflow_state(str(failing_request.workflow_id))
        assert failed_state.current_state == WorkflowState.FAILED
        assert failed_state.error_message is not None
        
        # Test processing with reliable subreducer
        reliable_request = sample_requests["document_regeneration"]
        reliable_response = await engine.process_workflow(reliable_request)
        
        assert reliable_response.status == WorkflowStatus.COMPLETED
        assert reliable_response.result is not None
        
        # Test processing with intermittent subreducer (multiple attempts)
        intermittent_results = []
        for i in range(10):  # Multiple attempts to hit both success and failure
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id=f"intermittent-{i}",
                correlation_id=uuid4(),
                payload=sample_requests["report_generation"].payload
            )
            result = await engine.process_workflow(request)
            intermittent_results.append(result.status)
        
        # Should have mix of successes and failures
        success_count = sum(1 for status in intermittent_results if status == WorkflowStatus.COMPLETED)
        failure_count = sum(1 for status in intermittent_results if status == WorkflowStatus.FAILED)
        
        assert success_count > 0  # Should have some successes
        assert failure_count > 0  # Should have some failures
        
        # Verify comprehensive metrics reflect mixed results
        final_metrics = engine.get_comprehensive_metrics()
        legacy_metrics = final_metrics["legacy_metrics"]
        assert legacy_metrics["successful_workflows"] > 0
        assert legacy_metrics["failed_workflows"] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_multi_workflow_processing(self, engine, sample_requests):
        """Test concurrent processing across multiple workflow types."""
        
        # Register high-performance subreducers
        for workflow_name, request in sample_requests.items():
            concurrent_subreducer = TestEnhancedSubreducer(
                name=f"concurrent_{workflow_name}",
                supported_types=[request.workflow_type],
                processing_time=0.1,  # Fast processing
                success_rate=1.0      # Reliable
            )
            engine.register_subreducer(concurrent_subreducer, [request.workflow_type])
        
        # Create many concurrent requests across all workflow types
        concurrent_tasks = []
        request_mapping = {}
        
        for batch in range(5):  # 5 batches
            for workflow_name, base_request in sample_requests.items():
                for instance in range(3):  # 3 instances per type per batch
                    request = WorkflowRequest(
                        workflow_id=uuid4(),
                        workflow_type=base_request.workflow_type,
                        instance_id=f"concurrent-{workflow_name}-b{batch}-i{instance}",
                        correlation_id=uuid4(),
                        payload={**base_request.payload, "batch": batch, "instance": instance}
                    )
                    
                    task = asyncio.create_task(engine.process_workflow(request))
                    concurrent_tasks.append(task)
                    request_mapping[task] = (workflow_name, request)
        
        # Process all concurrently
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify all completed successfully
        successful_results = [r for r in results if isinstance(r, WorkflowResponse) and r.status == WorkflowStatus.COMPLETED]
        assert len(successful_results) == len(concurrent_tasks)  # All should succeed
        
        # Verify performance (concurrent should be much faster than sequential)
        expected_sequential_time = len(concurrent_tasks) * 0.1  # 0.1s per request
        assert total_time < expected_sequential_time * 0.3  # Should be much faster
        
        print(f"Processed {len(concurrent_tasks)} workflows concurrently in {total_time:.2f}s")
        
        # Verify comprehensive metrics
        final_metrics = engine.get_comprehensive_metrics()
        assert final_metrics["legacy_metrics"]["total_workflows_processed"] == len(concurrent_tasks)
        assert final_metrics["legacy_metrics"]["successful_workflows"] == len(concurrent_tasks)
        assert final_metrics["enhanced_metrics"]["overall_success_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_workflow_lifecycle_management(self, engine):
        """Test complete workflow lifecycle management."""
        
        # Register a controllable subreducer
        lifecycle_subreducer = TestEnhancedSubreducer(
            name="lifecycle_test",
            supported_types=[WorkflowType.DATA_ANALYSIS],
            processing_time=0.2,  # Longer processing to observe states
            success_rate=1.0
        )
        engine.register_subreducer(lifecycle_subreducer, [WorkflowType.DATA_ANALYSIS])
        
        request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="lifecycle-test-001",
            correlation_id=uuid4(),
            payload={"data": [1, 2, 3, 4, 5], "test": "lifecycle"}
        )
        
        # Start processing
        processing_task = asyncio.create_task(engine.process_workflow(request))
        
        # Track state changes throughout lifecycle
        state_changes = []
        
        # Initial state should be pending/processing
        await asyncio.sleep(0.05)
        initial_state = engine.get_workflow_state(str(request.workflow_id))
        if initial_state:
            state_changes.append(initial_state.current_state)
        
        # Check active workflows
        active = engine.get_active_workflows()
        assert str(request.workflow_id) in active
        
        # Mid-processing state
        await asyncio.sleep(0.1)
        mid_state = engine.get_workflow_state(str(request.workflow_id))
        if mid_state and mid_state.current_state not in state_changes:
            state_changes.append(mid_state.current_state)
        
        # Wait for completion
        response = await processing_task
        
        # Final state
        final_state = engine.get_workflow_state(str(request.workflow_id))
        if final_state:
            state_changes.append(final_state.current_state)
        
        # Verify lifecycle progression
        assert response.status == WorkflowStatus.COMPLETED
        assert final_state.current_state == WorkflowState.COMPLETED
        assert final_state.is_terminal_state() is True
        assert final_state.processing_time_ms is not None
        assert final_state.processing_time_ms > 0
        
        # Verify transition history
        assert len(final_state.transition_history) > 0
        transitions = [t.to_state for t in final_state.transition_history]
        assert WorkflowState.COMPLETED in transitions
        
        # Verify no longer active
        final_active = engine.get_active_workflows()
        assert str(request.workflow_id) not in final_active
    
    @pytest.mark.asyncio
    async def test_real_subreducer_integration(self, engine):
        """Test integration with real subreducers (not mocks)."""
        
        # Register real subreducers
        data_analysis = ReducerDataAnalysisSubreducer("real_data_analysis")
        report_generation = ReducerReportGenerationSubreducer("real_report_generation") 
        
        engine.register_subreducer(data_analysis, [WorkflowType.DATA_ANALYSIS])
        engine.register_subreducer(report_generation, [WorkflowType.REPORT_GENERATION])
        
        # Test real data analysis workflow
        analysis_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="real-analysis-001",
            correlation_id=uuid4(),
            payload={
                "data": [10, 20, 30, 40, 50, 25, 35, 45, 55, 65],
                "analysis_types": ["descriptive", "trend"],
                "data_validation": {"remove_outliers": False}
            }
        )
        
        analysis_response = await engine.process_workflow(analysis_request)
        
        assert analysis_response.status == WorkflowStatus.COMPLETED
        assert analysis_response.subreducer_name == "real_data_analysis"
        
        # Verify analysis results structure
        results = analysis_response.result
        assert "analysis_results" in results
        assert "descriptive" in results["analysis_results"]
        assert "trend" in results["analysis_results"]
        
        # Test real report generation workflow
        report_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="real-report-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "summary",
                "output_format": "json",
                "report_title": "Real Integration Test Report",
                "data": {"metrics": [85, 90, 92, 88], "status": "completed"}
            }
        )
        
        report_response = await engine.process_workflow(report_request)
        
        assert report_response.status == WorkflowStatus.COMPLETED
        assert report_response.subreducer_name == "real_report_generation"
        
        # Verify report results structure
        report_results = report_response.result
        assert "report_content" in report_results
        assert "report_metadata" in report_results
        assert "validation_results" in report_results
        
        # Verify both workflows tracked properly in comprehensive metrics
        comprehensive_metrics = engine.get_comprehensive_metrics()
        assert comprehensive_metrics["legacy_metrics"]["total_workflows_processed"] == 2
        assert comprehensive_metrics["legacy_metrics"]["successful_workflows"] == 2
        
        # Verify workflow type specific metrics
        data_metrics = engine.get_workflow_type_metrics("data_analysis")
        assert data_metrics["total_processed"] == 1
        assert data_metrics["success_rate_percent"] == 100.0
        
        report_metrics = engine.get_workflow_type_metrics("report_generation")  
        assert report_metrics["total_processed"] == 1
        assert report_metrics["success_rate_percent"] == 100.0
    
    @pytest.mark.asyncio
    async def test_metrics_reset_and_state_management(self, engine):
        """Test metrics reset functionality and state management."""
        
        # Register subreducer and process some workflows
        test_subreducer = TestEnhancedSubreducer(
            name="reset_test",
            supported_types=[WorkflowType.DATA_ANALYSIS],
            processing_time=0.05,
            success_rate=1.0
        )
        engine.register_subreducer(test_subreducer, [WorkflowType.DATA_ANALYSIS])
        
        # Process several workflows
        for i in range(3):
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id=f"reset-test-{i}",
                correlation_id=uuid4(),
                payload={"data": [i, i+1, i+2]}
            )
            
            response = await engine.process_workflow(request)
            assert response.status == WorkflowStatus.COMPLETED
        
        # Verify metrics exist
        metrics_before = engine.get_comprehensive_metrics()
        assert metrics_before["legacy_metrics"]["total_workflows_processed"] == 3
        
        # Reset metrics
        engine.reset_metrics()
        
        # Verify metrics are reset
        metrics_after = engine.get_comprehensive_metrics()
        assert metrics_after["legacy_metrics"]["total_workflows_processed"] == 0
        assert metrics_after["legacy_metrics"]["successful_workflows"] == 0
        assert metrics_after["legacy_metrics"]["failed_workflows"] == 0
        
        # Process another workflow to ensure system still works
        post_reset_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="post-reset-001",
            correlation_id=uuid4(),
            payload={"data": [100, 200, 300]}
        )
        
        post_reset_response = await engine.process_workflow(post_reset_request)
        assert post_reset_response.status == WorkflowStatus.COMPLETED
        
        # Verify new metrics start from 1
        final_metrics = engine.get_comprehensive_metrics()
        assert final_metrics["legacy_metrics"]["total_workflows_processed"] == 1
        assert final_metrics["legacy_metrics"]["successful_workflows"] == 1
    
    @pytest.mark.asyncio
    async def test_edge_cases_and_boundary_conditions(self, engine):
        """Test various edge cases and boundary conditions."""
        
        # Test processing workflow with no registered subreducer
        unregistered_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="unregistered-001",
            correlation_id=uuid4(),
            payload={"data": [1, 2, 3]}
        )
        
        unregistered_response = await engine.process_workflow(unregistered_request)
        assert unregistered_response.status == WorkflowStatus.FAILED
        assert "No subreducer registered" in unregistered_response.error_message
        
        # Register subreducer and test edge case payloads
        edge_case_subreducer = TestEnhancedSubreducer(
            name="edge_case_test",
            supported_types=[WorkflowType.DATA_ANALYSIS],
            processing_time=0.01,
            success_rate=1.0
        )
        engine.register_subreducer(edge_case_subreducer, [WorkflowType.DATA_ANALYSIS])
        
        # Test with empty payload
        empty_payload_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="empty-payload-001",
            correlation_id=uuid4(),
            payload={}
        )
        
        empty_response = await engine.process_workflow(empty_payload_request)
        assert empty_response.status == WorkflowStatus.COMPLETED  # Enhanced subreducer handles this
        
        # Test with very large payload
        large_payload = {"data": list(range(10000)), "metadata": {"size": "large"}}
        large_payload_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="large-payload-001",
            correlation_id=uuid4(),
            payload=large_payload
        )
        
        large_response = await engine.process_workflow(large_payload_request)
        assert large_response.status == WorkflowStatus.COMPLETED
        assert "10000" in large_response.result["payload_summary"]  # Subreducer processed large payload
        
        # Test workflow state retrieval for non-existent workflow
        non_existent_state = engine.get_workflow_state("non-existent-id")
        assert non_existent_state is None
        
        # Test metrics for non-existent workflow type
        non_existent_metrics = engine.get_workflow_type_metrics("non_existent_type")
        assert non_existent_metrics is None