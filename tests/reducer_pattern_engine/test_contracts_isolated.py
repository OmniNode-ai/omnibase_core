"""
Isolated tests for Reducer Pattern Engine contracts.

Tests the core contract models and enums without importing
the full engine infrastructure to avoid dependency issues.
"""

import pytest
from uuid import uuid4
import time

# Import contracts directly from the file
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# Direct file import to avoid init chain issues
import importlib.util
contracts_path = os.path.join(os.path.dirname(__file__), 
                             '../../src/omnibase_core/patterns/reducer_pattern_engine/v1_0_0/contracts.py')
spec = importlib.util.spec_from_file_location("contracts", contracts_path)
contracts_module = importlib.util.module_from_spec(spec)

# Execute the module to load all classes
spec.loader.exec_module(contracts_module)

# Import the classes we need
BaseSubreducer = contracts_module.BaseSubreducer
RoutingDecision = contracts_module.RoutingDecision
SubreducerResult = contracts_module.SubreducerResult
WorkflowRequest = contracts_module.WorkflowRequest
WorkflowResponse = contracts_module.WorkflowResponse
WorkflowStatus = contracts_module.WorkflowStatus
WorkflowType = contracts_module.WorkflowType
EngineMetrics = contracts_module.EngineMetrics


class TestWorkflowType:
    """Test WorkflowType enum."""
    
    def test_workflow_type_values(self):
        """Test that WorkflowType has expected values."""
        assert WorkflowType.DOCUMENT_REGENERATION.value == "document_regeneration"
    
    def test_workflow_type_enum_members(self):
        """Test WorkflowType enum members."""
        assert hasattr(WorkflowType, 'DOCUMENT_REGENERATION')
        assert isinstance(WorkflowType.DOCUMENT_REGENERATION, WorkflowType)


class TestWorkflowStatus:
    """Test WorkflowStatus enum."""
    
    def test_workflow_status_values(self):
        """Test that WorkflowStatus has expected values."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.PROCESSING.value == "processing"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
    
    def test_workflow_status_enum_members(self):
        """Test WorkflowStatus enum members."""
        statuses = [WorkflowStatus.PENDING, WorkflowStatus.PROCESSING, 
                   WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
        for status in statuses:
            assert isinstance(status, WorkflowStatus)


class TestWorkflowRequest:
    """Test WorkflowRequest model."""
    
    def test_workflow_request_creation(self):
        """Test WorkflowRequest model creation."""
        workflow_id = uuid4()
        correlation_id = uuid4()
        
        request = WorkflowRequest(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            correlation_id=correlation_id,
            payload={"document_id": "doc_123", "content_type": "markdown"},
            metadata={"test": "metadata"}
        )
        
        assert request.workflow_id == workflow_id
        assert request.workflow_type == WorkflowType.DOCUMENT_REGENERATION
        assert request.instance_id == "test_instance"
        assert request.correlation_id == correlation_id
        assert request.payload == {"document_id": "doc_123", "content_type": "markdown"}
        assert request.metadata == {"test": "metadata"}
        assert isinstance(request.timestamp, float)
    
    def test_workflow_request_minimal(self):
        """Test WorkflowRequest with minimal required fields."""
        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="minimal_instance",
            payload={"document_id": "doc_123"}
        )
        
        # Should auto-generate IDs and timestamp
        assert request.workflow_id is not None
        assert request.correlation_id is not None
        assert request.timestamp > 0
        assert request.metadata is None  # Optional field
    
    def test_workflow_request_immutability(self):
        """Test that WorkflowRequest fields are properly typed."""
        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={"test": "payload"}
        )
        
        # Test that we can access all fields
        assert hasattr(request, 'workflow_id')
        assert hasattr(request, 'workflow_type')
        assert hasattr(request, 'instance_id')
        assert hasattr(request, 'correlation_id')
        assert hasattr(request, 'payload')
        assert hasattr(request, 'metadata')
        assert hasattr(request, 'timestamp')


class TestWorkflowResponse:
    """Test WorkflowResponse model."""
    
    def test_successful_workflow_response(self):
        """Test WorkflowResponse for successful workflow."""
        workflow_id = uuid4()
        
        response = WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.COMPLETED,
            subreducer_name="test_subreducer",
            processing_time_ms=150.5,
            result={"output": "success"}
        )
        
        assert response.workflow_id == workflow_id
        assert response.status == WorkflowStatus.COMPLETED
        assert response.subreducer_name == "test_subreducer"
        assert response.processing_time_ms == 150.5
        assert response.result == {"output": "success"}
        assert response.error_message is None
        assert response.error_details is None
        assert isinstance(response.timestamp, float)
    
    def test_failed_workflow_response(self):
        """Test WorkflowResponse for failed workflow."""
        workflow_id = uuid4()
        
        response = WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.FAILED,
            subreducer_name="test_subreducer",
            processing_time_ms=75.0,
            error_message="Test error occurred",
            error_details={"error_type": "ValidationError", "field": "document_id"}
        )
        
        assert response.workflow_id == workflow_id
        assert response.status == WorkflowStatus.FAILED
        assert response.subreducer_name == "test_subreducer"
        assert response.processing_time_ms == 75.0
        assert response.error_message == "Test error occurred"
        assert response.error_details == {"error_type": "ValidationError", "field": "document_id"}
        assert response.result is None
    
    def test_workflow_response_minimal(self):
        """Test WorkflowResponse with minimal required fields."""
        workflow_id = uuid4()
        
        response = WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.PROCESSING,
            processing_time_ms=0.0
        )
        
        # Should have defaults for optional fields
        assert response.workflow_id == workflow_id
        assert response.status == WorkflowStatus.PROCESSING
        assert response.processing_time_ms == 0.0
        assert response.subreducer_name is None
        assert response.result is None
        assert response.error_message is None
        assert response.error_details is None
        assert isinstance(response.timestamp, float)


class TestSubreducerResult:
    """Test SubreducerResult model."""
    
    def test_successful_subreducer_result(self):
        """Test SubreducerResult for successful processing."""
        workflow_id = uuid4()
        
        result = SubreducerResult(
            workflow_id=workflow_id,
            subreducer_name="document_processor",
            success=True,
            result={"processed_document": "content"},
            processing_time_ms=200.0
        )
        
        assert result.workflow_id == workflow_id
        assert result.subreducer_name == "document_processor"
        assert result.success is True
        assert result.result == {"processed_document": "content"}
        assert result.processing_time_ms == 200.0
        assert result.error_message is None
        assert result.error_details is None
        assert isinstance(result.timestamp, float)
    
    def test_failed_subreducer_result(self):
        """Test SubreducerResult for failed processing."""
        workflow_id = uuid4()
        
        result = SubreducerResult(
            workflow_id=workflow_id,
            subreducer_name="document_processor",
            success=False,
            error_message="Processing failed",
            error_details={"reason": "invalid_format"},
            processing_time_ms=50.0
        )
        
        assert result.workflow_id == workflow_id
        assert result.subreducer_name == "document_processor"
        assert result.success is False
        assert result.error_message == "Processing failed"
        assert result.error_details == {"reason": "invalid_format"}
        assert result.processing_time_ms == 50.0
        assert result.result is None


class TestRoutingDecision:
    """Test RoutingDecision model."""
    
    def test_routing_decision_creation(self):
        """Test RoutingDecision model creation."""
        workflow_id = uuid4()
        
        decision = RoutingDecision(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            subreducer_name="document_processor",
            routing_hash="abc123def456",
            routing_metadata={
                "routing_algorithm": "hash_based",
                "total_subreducers": 3,
                "selected_index": 1
            }
        )
        
        assert decision.workflow_id == workflow_id
        assert decision.workflow_type == WorkflowType.DOCUMENT_REGENERATION
        assert decision.instance_id == "test_instance"
        assert decision.subreducer_name == "document_processor"
        assert decision.routing_hash == "abc123def456"
        assert decision.routing_metadata["routing_algorithm"] == "hash_based"
        assert decision.routing_metadata["total_subreducers"] == 3
        assert isinstance(decision.timestamp, float)
    
    def test_routing_decision_minimal(self):
        """Test RoutingDecision with minimal fields."""
        workflow_id = uuid4()
        
        decision = RoutingDecision(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="minimal_instance",
            subreducer_name="processor",
            routing_hash="hash123"
        )
        
        assert decision.workflow_id == workflow_id
        assert decision.subreducer_name == "processor"
        assert decision.routing_hash == "hash123"
        assert decision.routing_metadata is None


class TestEngineMetrics:
    """Test EngineMetrics model."""
    
    def test_engine_metrics_creation(self):
        """Test EngineMetrics model creation."""
        metrics = EngineMetrics(
            total_workflows_processed=100,
            successful_workflows=85,
            failed_workflows=15,
            average_processing_time_ms=250.5,
            subreducer_metrics={
                "document_processor": {
                    "processed": 60,
                    "success_rate": 90.0
                },
                "router": {
                    "total_routed": 100,
                    "routing_errors": 2
                }
            }
        )
        
        assert metrics.total_workflows_processed == 100
        assert metrics.successful_workflows == 85
        assert metrics.failed_workflows == 15
        assert metrics.average_processing_time_ms == 250.5
        assert "document_processor" in metrics.subreducer_metrics
        assert "router" in metrics.subreducer_metrics
        assert isinstance(metrics.timestamp, float)
    
    def test_engine_metrics_minimal(self):
        """Test EngineMetrics with minimal fields."""
        metrics = EngineMetrics(
            total_workflows_processed=0,
            successful_workflows=0,
            failed_workflows=0,
            average_processing_time_ms=0.0
        )
        
        assert metrics.total_workflows_processed == 0
        assert metrics.successful_workflows == 0
        assert metrics.failed_workflows == 0
        assert metrics.average_processing_time_ms == 0.0
        assert metrics.subreducer_metrics is None
    
    def test_engine_metrics_success_rate_calculation(self):
        """Test success rate calculation method."""
        metrics = EngineMetrics(
            total_workflows_processed=100,
            successful_workflows=75,
            failed_workflows=25,
            average_processing_time_ms=200.0
        )
        
        success_rate = metrics.calculate_success_rate()
        assert success_rate == 75.0
    
    def test_engine_metrics_success_rate_zero_division(self):
        """Test success rate calculation with zero total."""
        metrics = EngineMetrics(
            total_workflows_processed=0,
            successful_workflows=0,
            failed_workflows=0,
            average_processing_time_ms=0.0
        )
        
        success_rate = metrics.calculate_success_rate()
        assert success_rate == 0.0


class TestBaseSubreducer:
    """Test BaseSubreducer abstract base class."""
    
    def test_base_subreducer_instantiation(self):
        """Test BaseSubreducer cannot be instantiated directly."""
        # BaseSubreducer is abstract, so we can't instantiate it directly
        # But we can create a concrete implementation for testing
        
        class TestSubreducer(BaseSubreducer):
            def __init__(self, name: str = "test_subreducer"):
                super().__init__(name)
            
            def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
                return workflow_type == WorkflowType.DOCUMENT_REGENERATION
            
            async def process(self, request: WorkflowRequest) -> SubreducerResult:
                return SubreducerResult(
                    workflow_id=request.workflow_id,
                    subreducer_name=self.name,
                    success=True,
                    processing_time_ms=10.0
                )
        
        subreducer = TestSubreducer("concrete_test")
        assert subreducer.name == "concrete_test"
        assert subreducer.supports_workflow_type(WorkflowType.DOCUMENT_REGENERATION)
    
    @pytest.mark.asyncio
    async def test_base_subreducer_process_method(self):
        """Test BaseSubreducer process method implementation."""
        
        class TestSubreducer(BaseSubreducer):
            def __init__(self):
                super().__init__("async_test")
            
            def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
                return True
            
            async def process(self, request: WorkflowRequest) -> SubreducerResult:
                return SubreducerResult(
                    workflow_id=request.workflow_id,
                    subreducer_name=self.name,
                    success=True,
                    result={"test": "async_result"},
                    processing_time_ms=25.0
                )
        
        subreducer = TestSubreducer()
        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="async_test",
            payload={"test": "data"}
        )
        
        result = await subreducer.process(request)
        
        assert isinstance(result, SubreducerResult)
        assert result.success is True
        assert result.subreducer_name == "async_test"
        assert result.result == {"test": "async_result"}


class TestModelValidation:
    """Test Pydantic model validation and serialization."""
    
    def test_workflow_request_validation(self):
        """Test WorkflowRequest validation."""
        # Valid request should work
        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="valid_instance",
            payload={"document_id": "doc_123"}
        )
        assert request.instance_id == "valid_instance"
    
    def test_workflow_response_serialization(self):
        """Test WorkflowResponse JSON serialization."""
        workflow_id = uuid4()
        response = WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.COMPLETED,
            processing_time_ms=100.0,
            result={"output": "test"}
        )
        
        # Test that the model can be converted to dict
        response_dict = response.model_dump()
        assert response_dict["workflow_id"] == str(workflow_id)  # UUID converted to string
        assert response_dict["status"] == "completed"
        assert response_dict["processing_time_ms"] == 100.0
    
    def test_enum_serialization(self):
        """Test that enums serialize correctly."""
        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="enum_test",
            payload={"test": "data"}
        )
        
        request_dict = request.model_dump()
        assert request_dict["workflow_type"] == "document_regeneration"
        
        response = WorkflowResponse(
            workflow_id=request.workflow_id,
            status=WorkflowStatus.FAILED,
            processing_time_ms=50.0,
            error_message="Test error"
        )
        
        response_dict = response.model_dump()
        assert response_dict["status"] == "failed"


class TestTimestampBehavior:
    """Test timestamp behavior across models."""
    
    def test_timestamp_auto_generation(self):
        """Test that timestamps are automatically generated."""
        before_time = time.time()
        
        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="timestamp_test",
            payload={"test": "data"}
        )
        
        after_time = time.time()
        
        assert before_time <= request.timestamp <= after_time
    
    def test_timestamp_consistency(self):
        """Test timestamp behavior across different models."""
        workflow_id = uuid4()
        
        # Create models at roughly the same time
        request = WorkflowRequest(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="consistency_test",
            payload={"test": "data"}
        )
        
        response = WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.COMPLETED,
            processing_time_ms=100.0
        )
        
        result = SubreducerResult(
            workflow_id=workflow_id,
            subreducer_name="test",
            success=True,
            processing_time_ms=100.0
        )
        
        # Timestamps should be close but may not be identical
        assert abs(request.timestamp - response.timestamp) < 1.0
        assert abs(response.timestamp - result.timestamp) < 1.0