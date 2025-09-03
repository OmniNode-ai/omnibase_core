"""
Integration tests for multi-workflow processing in Reducer Pattern Engine Phase 2.

Tests comprehensive workflow processing across all three workflow types with 
instance isolation, concurrent processing, and comprehensive validation.
"""

import asyncio
import time
import pytest
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
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_data_analysis import (
    ReducerDataAnalysisSubreducer
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_report_generation import (
    ReducerReportGenerationSubreducer
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration import (
    ReducerDocumentRegenerationSubreducer
)
from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
    WorkflowState,
    WorkflowStateModel
)


class MockSubreducer(BaseSubreducer):
    """Mock subreducer for testing purposes."""
    
    def __init__(self, name: str, supported_type: WorkflowType, 
                 success: bool = True, processing_delay: float = 0.1):
        super().__init__(name)
        self._supported_type = supported_type
        self._success = success
        self._processing_delay = processing_delay
        self._call_count = 0
    
    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type == self._supported_type
    
    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        """Mock processing with configurable behavior."""
        self._call_count += 1
        
        # Simulate processing time
        await asyncio.sleep(self._processing_delay)
        
        if self._success:
            return SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=True,
                result={
                    "mock_result": f"Processed {request.workflow_type.value}",
                    "call_count": self._call_count,
                    "processing_time": self._processing_delay * 1000
                },
                processing_time_ms=self._processing_delay * 1000
            )
        else:
            return SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=False,
                error_message="Mock processing failure",
                error_details={"mock_error": True}
            )
    
    @property
    def call_count(self) -> int:
        return self._call_count


class TestMultiWorkflowProcessing:
    """Test suite for multi-workflow processing integration."""
    
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
    def sample_workflows(self) -> Dict[str, WorkflowRequest]:
        """Create sample workflow requests for all supported types."""
        base_correlation_id = uuid4()
        
        workflows = {
            "document_regeneration": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="doc-001",
                correlation_id=base_correlation_id,
                payload={
                    "document_id": "test-doc-123",
                    "template_id": "standard-template",
                    "data": {"title": "Test Document", "content": "Sample content"}
                },
                metadata={"priority": "high", "user_id": "test-user"}
            ),
            "data_analysis": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id="analysis-001",
                correlation_id=base_correlation_id,
                payload={
                    "data": [1, 2, 3, 4, 5, 10, 15, 20, 25, 30],
                    "analysis_types": ["descriptive", "trend"],
                    "data_validation": {"remove_outliers": True}
                },
                metadata={"dataset": "test-data", "source": "unit-test"}
            ),
            "report_generation": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id="report-001",
                correlation_id=base_correlation_id,
                payload={
                    "report_type": "summary",
                    "data_sources": ["analytics", "metrics"],
                    "template": "executive-summary",
                    "parameters": {"period": "monthly", "format": "pdf"}
                },
                metadata={"department": "engineering", "requestor": "test-user"}
            )
        }
        
        return workflows
    
    @pytest.mark.asyncio
    async def test_single_workflow_processing_all_types(self, engine, sample_workflows):
        """Test successful processing of each workflow type individually."""
        
        # Register mock subreducers for each workflow type
        mock_subreducers = {}
        for workflow_name, request in sample_workflows.items():
            mock_subreducer = MockSubreducer(
                name=f"mock_{workflow_name}",
                supported_type=request.workflow_type,
                success=True,
                processing_delay=0.05
            )
            mock_subreducers[workflow_name] = mock_subreducer
            engine.register_subreducer(mock_subreducer, [request.workflow_type])
        
        # Process each workflow type
        results = {}
        for workflow_name, request in sample_workflows.items():
            response = await engine.process_workflow(request)
            results[workflow_name] = response
        
        # Validate all workflows processed successfully
        for workflow_name, response in results.items():
            assert response.status == WorkflowStatus.COMPLETED
            assert response.error_message is None
            assert response.result is not None
            assert response.processing_time_ms > 0
            assert response.subreducer_name == f"mock_{workflow_name}"
            
            # Verify subreducer was called
            assert mock_subreducers[workflow_name].call_count == 1
        
        # Verify metrics
        metrics = engine.get_metrics()
        assert metrics.total_workflows_processed == len(sample_workflows)
        assert metrics.successful_workflows == len(sample_workflows)
        assert metrics.failed_workflows == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_processing(self, engine, sample_workflows):
        """Test concurrent processing of multiple workflows with instance isolation."""
        
        # Register subreducers with different processing delays
        processing_delays = {"document_regeneration": 0.1, "data_analysis": 0.15, "report_generation": 0.2}
        mock_subreducers = {}
        
        for workflow_name, request in sample_workflows.items():
            mock_subreducer = MockSubreducer(
                name=f"concurrent_{workflow_name}",
                supported_type=request.workflow_type,
                success=True,
                processing_delay=processing_delays[workflow_name]
            )
            mock_subreducers[workflow_name] = mock_subreducer
            engine.register_subreducer(mock_subreducer, [request.workflow_type])
        
        # Process all workflows concurrently
        start_time = time.time()
        tasks = [
            engine.process_workflow(request) 
            for request in sample_workflows.values()
        ]
        
        responses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify concurrent processing was faster than sequential
        sequential_time = sum(processing_delays.values())
        assert total_time < sequential_time, f"Concurrent processing ({total_time:.3f}s) should be faster than sequential ({sequential_time:.3f}s)"
        
        # Verify all workflows completed successfully
        assert len(responses) == len(sample_workflows)
        for response in responses:
            assert response.status == WorkflowStatus.COMPLETED
            assert response.error_message is None
            assert response.result is not None
        
        # Verify instance isolation - each subreducer called exactly once
        for mock_subreducer in mock_subreducers.values():
            assert mock_subreducer.call_count == 1
    
    @pytest.mark.asyncio
    async def test_workflow_instance_isolation(self, engine):
        """Test that workflow instances are properly isolated."""
        
        # Create multiple requests of the same type with different instances
        correlation_id = uuid4()
        requests = []
        
        for i in range(3):
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id=f"isolation-test-{i}",
                correlation_id=correlation_id,
                payload={
                    "data": [i * 10, i * 20, i * 30],
                    "analysis_types": ["descriptive"],
                    "instance_marker": i
                }
            )
            requests.append(request)
        
        # Register subreducer
        mock_subreducer = MockSubreducer(
            name="isolation_test_subreducer",
            supported_type=WorkflowType.DATA_ANALYSIS,
            success=True,
            processing_delay=0.1
        )
        engine.register_subreducer(mock_subreducer, [WorkflowType.DATA_ANALYSIS])
        
        # Process requests concurrently
        tasks = [engine.process_workflow(request) for request in requests]
        responses = await asyncio.gather(*tasks)
        
        # Verify all instances processed successfully
        assert len(responses) == 3
        processed_instance_ids = {response.instance_id for response in responses}
        expected_instance_ids = {f"isolation-test-{i}" for i in range(3)}
        assert processed_instance_ids == expected_instance_ids
        
        # Verify all have unique workflow IDs
        processed_workflow_ids = {response.workflow_id for response in responses}
        assert len(processed_workflow_ids) == 3
        
        # Verify subreducer called for each instance
        assert mock_subreducer.call_count == 3
    
    @pytest.mark.asyncio
    async def test_mixed_success_failure_scenarios(self, engine, sample_workflows):
        """Test processing with mixed success and failure scenarios."""
        
        # Create subreducers with different success rates
        subreducer_configs = [
            ("document_regeneration", True),   # Success
            ("data_analysis", False),          # Failure
            ("report_generation", True),       # Success
        ]
        
        mock_subreducers = {}
        for workflow_name, should_succeed in subreducer_configs:
            request = sample_workflows[workflow_name]
            mock_subreducer = MockSubreducer(
                name=f"mixed_{workflow_name}",
                supported_type=request.workflow_type,
                success=should_succeed,
                processing_delay=0.05
            )
            mock_subreducers[workflow_name] = mock_subreducer
            engine.register_subreducer(mock_subreducer, [request.workflow_type])
        
        # Process all workflows
        responses = []
        for workflow_name, request in sample_workflows.items():
            response = await engine.process_workflow(request)
            responses.append((workflow_name, response))
        
        # Verify mixed results
        success_count = 0
        failure_count = 0
        
        for workflow_name, response in responses:
            expected_success = dict(subreducer_configs)[workflow_name]
            
            if expected_success:
                assert response.status == WorkflowStatus.COMPLETED
                assert response.error_message is None
                assert response.result is not None
                success_count += 1
            else:
                assert response.status == WorkflowStatus.FAILED
                assert response.error_message is not None
                assert "Mock processing failure" in response.error_message
                failure_count += 1
        
        assert success_count == 2
        assert failure_count == 1
        
        # Verify metrics reflect mixed results
        metrics = engine.get_metrics()
        assert metrics.total_workflows_processed == 3
        assert metrics.successful_workflows == 2
        assert metrics.failed_workflows == 1
    
    @pytest.mark.asyncio
    async def test_state_transition_tracking(self, engine):
        """Test workflow state transitions are properly tracked."""
        
        # Create workflow request
        request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="state-test-001",
            correlation_id=uuid4(),
            payload={"data": [1, 2, 3], "analysis_types": ["descriptive"]}
        )
        
        # Register subreducer with longer processing time to observe state changes
        mock_subreducer = MockSubreducer(
            name="state_tracking_subreducer",
            supported_type=WorkflowType.DATA_ANALYSIS,
            success=True,
            processing_delay=0.2
        )
        engine.register_subreducer(mock_subreducer, [WorkflowType.DATA_ANALYSIS])
        
        # Start processing
        task = asyncio.create_task(engine.process_workflow(request))
        
        # Give it a moment to start processing
        await asyncio.sleep(0.05)
        
        # Check active workflows
        active_workflows = engine.get_active_workflows()
        assert str(request.workflow_id) in active_workflows
        
        # Check workflow state
        workflow_state = engine.get_workflow_state(str(request.workflow_id))
        assert workflow_state is not None
        assert workflow_state.workflow_id == request.workflow_id
        assert workflow_state.current_state in [WorkflowState.PENDING, WorkflowState.PROCESSING]
        
        # Wait for completion
        response = await task
        
        # Verify final state
        assert response.status == WorkflowStatus.COMPLETED
        final_workflow_state = engine.get_workflow_state(str(request.workflow_id))
        assert final_workflow_state is not None
        assert final_workflow_state.current_state == WorkflowState.COMPLETED
        
        # Verify no longer in active workflows
        active_workflows_after = engine.get_active_workflows()
        assert str(request.workflow_id) not in active_workflows_after
    
    @pytest.mark.asyncio
    async def test_comprehensive_metrics_collection(self, engine, sample_workflows):
        """Test comprehensive metrics collection across all workflow types."""
        
        # Register all subreducers
        for workflow_name, request in sample_workflows.items():
            mock_subreducer = MockSubreducer(
                name=f"metrics_{workflow_name}",
                supported_type=request.workflow_type,
                success=True,
                processing_delay=0.1
            )
            engine.register_subreducer(mock_subreducer, [request.workflow_type])
        
        # Process multiple rounds of workflows
        rounds = 3
        all_responses = []
        
        for round_num in range(rounds):
            round_responses = []
            for workflow_name, base_request in sample_workflows.items():
                # Create new request for this round
                request = WorkflowRequest(
                    workflow_id=uuid4(),
                    workflow_type=base_request.workflow_type,
                    instance_id=f"{base_request.instance_id}-round-{round_num}",
                    correlation_id=uuid4(),
                    payload=base_request.payload,
                    metadata={**base_request.metadata, "round": round_num}
                )
                
                response = await engine.process_workflow(request)
                round_responses.append(response)
            
            all_responses.extend(round_responses)
        
        # Verify comprehensive metrics
        comprehensive_metrics = engine.get_comprehensive_metrics()
        
        # Check legacy metrics
        legacy_metrics = comprehensive_metrics["legacy_metrics"]
        assert legacy_metrics["total_workflows_processed"] == rounds * len(sample_workflows)
        assert legacy_metrics["successful_workflows"] == rounds * len(sample_workflows)
        assert legacy_metrics["failed_workflows"] == 0
        
        # Check enhanced metrics
        enhanced_metrics = comprehensive_metrics["enhanced_metrics"]
        assert enhanced_metrics["total_workflows_processed"] == rounds * len(sample_workflows)
        assert enhanced_metrics["overall_success_rate"] == 100.0
        
        # Check workflow type metrics
        for workflow_name, request in sample_workflows.items():
            workflow_type_str = request.workflow_type.value
            type_metrics = engine.get_workflow_type_metrics(workflow_type_str)
            assert type_metrics is not None
            assert type_metrics["total_processed"] == rounds
            assert type_metrics["successful_count"] == rounds
            assert type_metrics["failed_count"] == 0
            assert type_metrics["success_rate_percent"] == 100.0
        
        # Check registry status
        registry_status = comprehensive_metrics["registry_status"]
        assert registry_status["total_registered"] == len(sample_workflows)
        assert len(registry_status["workflow_types"]) == len(sample_workflows)
        assert registry_status["active_instances"] == len(sample_workflows)
        
        # Verify health checks pass
        health_status = registry_status["health_status"]
        for workflow_type in health_status.values():
            assert workflow_type is True
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, engine):
        """Test error handling and recovery mechanisms."""
        
        # Register failing subreducer
        failing_subreducer = MockSubreducer(
            name="failing_subreducer",
            supported_type=WorkflowType.DATA_ANALYSIS,
            success=False,
            processing_delay=0.1
        )
        engine.register_subreducer(failing_subreducer, [WorkflowType.DATA_ANALYSIS])
        
        # Create workflow request
        request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="error-test-001",
            correlation_id=uuid4(),
            payload={"data": [1, 2, 3]}
        )
        
        # Process workflow
        response = await engine.process_workflow(request)
        
        # Verify error response
        assert response.status == WorkflowStatus.FAILED
        assert response.error_message == "Mock processing failure"
        assert response.error_details == {"mock_error": True}
        assert response.result is None
        assert response.processing_time_ms > 0
        
        # Verify state tracking for failed workflow
        workflow_state = engine.get_workflow_state(str(request.workflow_id))
        assert workflow_state is not None
        assert workflow_state.current_state == WorkflowState.FAILED
        assert workflow_state.error_message is not None
        
        # Verify metrics reflect failure
        metrics = engine.get_metrics()
        assert metrics.failed_workflows == 1
        assert metrics.successful_workflows == 0
    
    @pytest.mark.asyncio
    async def test_real_subreducer_integration(self, engine):
        """Test integration with real subreducers (not mocks)."""
        
        # Create real data analysis subreducer
        data_analysis_subreducer = ReducerDataAnalysisSubreducer("real_data_analysis")
        engine.register_subreducer(data_analysis_subreducer, [WorkflowType.DATA_ANALYSIS])
        
        # Create realistic data analysis request
        request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="real-analysis-001",
            correlation_id=uuid4(),
            payload={
                "data": [10, 20, 30, 40, 50, 25, 35, 45, 55, 65],
                "analysis_types": ["descriptive", "trend", "distribution"],
                "data_validation": {"remove_outliers": False, "handle_missing": True},
                "output_format": "detailed"
            },
            metadata={"test": "real_subreducer_integration"}
        )
        
        # Process workflow
        response = await engine.process_workflow(request)
        
        # Verify successful processing
        assert response.status == WorkflowStatus.COMPLETED
        assert response.error_message is None
        assert response.result is not None
        
        # Verify analysis results structure
        analysis_results = response.result.get("analysis_results", {})
        assert "descriptive" in analysis_results
        assert "trend" in analysis_results
        assert "distribution" in analysis_results
        
        # Verify descriptive statistics
        descriptive = analysis_results["descriptive"]
        assert "mean" in descriptive
        assert "median" in descriptive
        assert "std_dev" in descriptive
        assert descriptive["count"] == 10
        
        # Verify processing metrics
        assert response.processing_time_ms > 0
        assert response.subreducer_name == "real_data_analysis"
    
    @pytest.mark.asyncio
    async def test_workflow_type_validation(self, engine):
        """Test validation of workflow types and proper routing."""
        
        # Register subreducers for specific types
        doc_subreducer = MockSubreducer(
            name="doc_only_subreducer",
            supported_type=WorkflowType.DOCUMENT_REGENERATION,
            success=True
        )
        engine.register_subreducer(doc_subreducer, [WorkflowType.DOCUMENT_REGENERATION])
        
        # Try to process workflow of unregistered type
        unsupported_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,  # Not registered
            instance_id="validation-test-001",
            correlation_id=uuid4(),
            payload={"data": [1, 2, 3]}
        )
        
        response = await engine.process_workflow(unsupported_request)
        
        # Verify failure due to missing subreducer
        assert response.status == WorkflowStatus.FAILED
        assert "No subreducer registered" in response.error_message
        assert response.result is None
        
        # Verify successful processing of supported type
        supported_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,  # Registered
            instance_id="validation-test-002",
            correlation_id=uuid4(),
            payload={"document_id": "test-doc"}
        )
        
        response = await engine.process_workflow(supported_request)
        
        # Verify successful processing
        assert response.status == WorkflowStatus.COMPLETED
        assert response.error_message is None
        assert response.result is not None

    @pytest.mark.asyncio 
    async def test_bulk_subreducer_registration(self, engine, sample_workflows):
        """Test bulk registration of multiple subreducers."""
        
        # Create subreducer configurations
        subreducer_configs = []
        for workflow_name, request in sample_workflows.items():
            mock_subreducer = MockSubreducer(
                name=f"bulk_{workflow_name}",
                supported_type=request.workflow_type,
                success=True
            )
            subreducer_configs.append({
                'subreducer': mock_subreducer,
                'workflow_types': [request.workflow_type]
            })
        
        # Register all subreducers at once
        registration_results = engine.register_multiple_subreducers(subreducer_configs)
        
        # Verify all registrations succeeded
        assert len(registration_results) == len(sample_workflows)
        for success in registration_results.values():
            assert success is True
        
        # Verify all workflow types are now supported
        supported_types = engine.list_supported_workflow_types()
        expected_types = {request.workflow_type.value for request in sample_workflows.values()}
        assert set(supported_types) == expected_types
        
        # Test processing one workflow of each type
        for workflow_name, request in sample_workflows.items():
            response = await engine.process_workflow(request)
            assert response.status == WorkflowStatus.COMPLETED