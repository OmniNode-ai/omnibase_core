"""
Tests for ReducerMetricsCollector - Enhanced metrics collection framework.

Tests comprehensive metrics collection, aggregation, performance monitoring,
and system-level metrics tracking for the Reducer Pattern Engine Phase 2.
"""

import pytest
import time
import threading
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID

from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.metrics import (
    ReducerMetricsCollector,
    WorkflowMetrics,
    AggregateMetrics
)


class TestWorkflowMetrics:
    """Test WorkflowMetrics dataclass functionality."""
    
    def test_workflow_metrics_creation(self):
        """Test basic WorkflowMetrics creation and attributes."""
        workflow_id = uuid4()
        
        metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            workflow_type="data_analysis",
            processing_time_ms=150.5,
            memory_usage_mb=25.6,
            success=True
        )
        
        assert metrics.workflow_id == workflow_id
        assert metrics.workflow_type == "data_analysis"
        assert metrics.processing_time_ms == 150.5
        assert metrics.memory_usage_mb == 25.6
        assert metrics.success is True
        assert metrics.error_type is None
        assert metrics.started_at is not None
        assert metrics.completed_at is None
    
    def test_workflow_metrics_with_error(self):
        """Test WorkflowMetrics with error information."""
        workflow_id = uuid4()
        
        metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            workflow_type="report_generation",
            processing_time_ms=75.0,
            memory_usage_mb=15.2,
            success=False,
            error_type="ValidationError"
        )
        
        assert metrics.success is False
        assert metrics.error_type == "ValidationError"


class TestAggregateMetrics:
    """Test AggregateMetrics dataclass functionality."""
    
    def test_aggregate_metrics_initialization(self):
        """Test AggregateMetrics initialization with default values."""
        aggregate = AggregateMetrics(workflow_type="document_regeneration")
        
        assert aggregate.workflow_type == "document_regeneration"
        assert aggregate.total_processed == 0
        assert aggregate.successful_count == 0
        assert aggregate.failed_count == 0
        assert aggregate.total_processing_time_ms == 0.0
        assert aggregate.total_memory_usage_mb == 0.0
        assert aggregate.min_processing_time_ms == float('inf')
        assert aggregate.max_processing_time_ms == 0.0
        assert len(aggregate.recent_processing_times) == 0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        aggregate = AggregateMetrics(workflow_type="test")
        
        # No workflows processed
        assert aggregate.success_rate == 0.0
        
        # Some workflows processed
        aggregate.total_processed = 10
        aggregate.successful_count = 7
        aggregate.failed_count = 3
        
        assert aggregate.success_rate == 70.0
        
        # All successful
        aggregate.successful_count = 10
        aggregate.failed_count = 0
        
        assert aggregate.success_rate == 100.0
    
    def test_average_processing_time_calculation(self):
        """Test average processing time calculation."""
        aggregate = AggregateMetrics(workflow_type="test")
        
        # No workflows processed
        assert aggregate.average_processing_time_ms == 0.0
        
        # Some workflows processed
        aggregate.total_processed = 4
        aggregate.total_processing_time_ms = 800.0
        
        assert aggregate.average_processing_time_ms == 200.0
    
    def test_average_memory_usage_calculation(self):
        """Test average memory usage calculation."""
        aggregate = AggregateMetrics(workflow_type="test")
        
        # No workflows processed
        assert aggregate.average_memory_usage_mb == 0.0
        
        # Some workflows processed
        aggregate.total_processed = 5
        aggregate.total_memory_usage_mb = 125.0
        
        assert aggregate.average_memory_usage_mb == 25.0
    
    def test_recent_average_processing_time(self):
        """Test recent average processing time calculation."""
        aggregate = AggregateMetrics(workflow_type="test")
        
        # No recent times
        assert aggregate.recent_average_processing_time_ms == 0.0
        
        # Some recent times
        aggregate.recent_processing_times.extend([100, 200, 300, 150, 250])
        
        assert aggregate.recent_average_processing_time_ms == 200.0
    
    def test_recent_processing_times_max_length(self):
        """Test that recent processing times respects max length."""
        aggregate = AggregateMetrics(workflow_type="test")
        
        # Add more than max length (100)
        for i in range(150):
            aggregate.recent_processing_times.append(i)
        
        # Should only keep the last 100
        assert len(aggregate.recent_processing_times) == 100
        assert list(aggregate.recent_processing_times) == list(range(50, 150))


class TestReducerMetricsCollector:
    """Test ReducerMetricsCollector comprehensive functionality."""
    
    @pytest.fixture
    def metrics_collector(self) -> ReducerMetricsCollector:
        """Create a ReducerMetricsCollector instance for testing."""
        return ReducerMetricsCollector(max_workflow_history=50)
    
    @patch('omnibase_core.patterns.reducer_pattern_engine.v1_0_0.metrics.psutil')
    def test_metrics_collector_initialization(self, mock_psutil, metrics_collector):
        """Test proper initialization of metrics collector."""
        
        # Mock psutil process
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 15.5
        mock_process.memory_info.return_value.rss = 128 * 1024 * 1024  # 128 MB
        mock_process.memory_percent.return_value = 5.2
        mock_process.num_threads.return_value = 8
        mock_process.num_fds.return_value = 42
        mock_process.create_time.return_value = time.time() - 3600
        mock_process.status.return_value = "running"
        mock_psutil.Process.return_value = mock_process
        
        # Test that initialization sets up system metrics
        assert len(metrics_collector._workflow_metrics) == 0
        assert len(metrics_collector._aggregate_metrics) == 0
        assert metrics_collector._start_time is not None
        assert isinstance(metrics_collector._system_metrics, dict)
    
    def test_record_workflow_start(self, metrics_collector):
        """Test recording workflow start."""
        workflow_id = uuid4()
        workflow_type = "data_analysis"
        
        with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0):
            metrics_collector.record_workflow_start(workflow_id, workflow_type)
        
        # Verify workflow start is recorded (though minimal until completion)
        summary = metrics_collector.get_metrics_summary()
        assert summary["total_workflows_processed"] == 0  # Not completed yet
    
    def test_record_workflow_completion_success(self, metrics_collector):
        """Test recording successful workflow completion."""
        workflow_id = uuid4()
        workflow_type = "report_generation"
        processing_time = 125.5
        
        with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=75.0):
            metrics_collector.record_workflow_completion(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                success=True,
                processing_time_ms=processing_time
            )
        
        # Verify metrics are updated
        summary = metrics_collector.get_metrics_summary()
        assert summary["total_workflows_processed"] == 1
        assert summary["overall_success_rate"] == 100.0
        
        # Check workflow type specific metrics
        type_metrics = metrics_collector.get_workflow_type_metrics(workflow_type)
        assert type_metrics is not None
        assert type_metrics["total_processed"] == 1
        assert type_metrics["successful_count"] == 1
        assert type_metrics["failed_count"] == 0
        assert type_metrics["success_rate_percent"] == 100.0
        assert type_metrics["average_processing_time_ms"] == processing_time
    
    def test_record_workflow_completion_failure(self, metrics_collector):
        """Test recording failed workflow completion."""
        workflow_id = uuid4()
        workflow_type = "document_regeneration"
        processing_time = 85.2
        error_type = "ValidationError"
        
        with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=60.0):
            metrics_collector.record_workflow_completion(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                success=False,
                processing_time_ms=processing_time,
                error_type=error_type
            )
        
        # Verify metrics are updated
        summary = metrics_collector.get_metrics_summary()
        assert summary["total_workflows_processed"] == 1
        assert summary["overall_success_rate"] == 0.0
        
        # Check workflow type specific metrics
        type_metrics = metrics_collector.get_workflow_type_metrics(workflow_type)
        assert type_metrics is not None
        assert type_metrics["total_processed"] == 1
        assert type_metrics["successful_count"] == 0
        assert type_metrics["failed_count"] == 1
        assert type_metrics["success_rate_percent"] == 0.0
    
    def test_record_processing_time(self, metrics_collector):
        """Test recording processing time directly."""
        workflow_type = "data_analysis"
        duration_ms = 200.5
        
        metrics_collector.record_processing_time(workflow_type, duration_ms)
        
        # Verify aggregate metrics are updated
        aggregate = metrics_collector._aggregate_metrics[workflow_type]
        assert aggregate.total_processing_time_ms == duration_ms
        assert aggregate.min_processing_time_ms == duration_ms
        assert aggregate.max_processing_time_ms == duration_ms
        assert list(aggregate.recent_processing_times) == [duration_ms]
    
    def test_increment_success_count(self, metrics_collector):
        """Test incrementing success count."""
        workflow_type = "report_generation"
        
        metrics_collector.increment_success_count(workflow_type)
        
        # Verify metrics are updated
        aggregate = metrics_collector._aggregate_metrics[workflow_type]
        assert aggregate.successful_count == 1
        assert aggregate.total_processed == 1
        assert aggregate.workflow_type == workflow_type
    
    def test_increment_error_count(self, metrics_collector):
        """Test incrementing error count."""
        workflow_type = "document_regeneration"
        error_type = "NetworkError"
        
        metrics_collector.increment_error_count(workflow_type, error_type)
        
        # Verify metrics are updated
        aggregate = metrics_collector._aggregate_metrics[workflow_type]
        assert aggregate.failed_count == 1
        assert aggregate.total_processed == 1
        
        # Verify error tracking
        error_key = f"{workflow_type}_errors"
        assert error_key in metrics_collector._system_metrics
        assert metrics_collector._system_metrics[error_key][error_type] == 1
    
    def test_track_memory_usage(self, metrics_collector):
        """Test memory usage tracking."""
        workflow_type = "data_analysis"
        memory_mb = 45.8
        
        metrics_collector.track_memory_usage(workflow_type, memory_mb)
        
        # Verify memory tracking
        aggregate = metrics_collector._aggregate_metrics[workflow_type]
        assert aggregate.total_memory_usage_mb == memory_mb
        assert aggregate.workflow_type == workflow_type
    
    @patch('omnibase_core.patterns.reducer_pattern_engine.v1_0_0.metrics.psutil')
    def test_get_metrics_summary(self, mock_psutil, metrics_collector):
        """Test comprehensive metrics summary generation."""
        
        # Mock psutil
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 25.0
        mock_process.memory_info.return_value.rss = 256 * 1024 * 1024  # 256 MB
        mock_process.memory_percent.return_value = 10.5
        mock_process.num_threads.return_value = 12
        mock_process.num_fds.return_value = 85
        mock_process.create_time.return_value = time.time() - 7200
        mock_process.status.return_value = "running"
        mock_psutil.Process.return_value = mock_process
        
        # Add some test data
        workflow_types = ["data_analysis", "report_generation", "document_regeneration"]
        for i, workflow_type in enumerate(workflow_types):
            workflow_id = uuid4()
            processing_time = 100 + i * 50
            success = i % 2 == 0  # Alternate success/failure
            
            with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0 + i * 10):
                metrics_collector.record_workflow_completion(
                    workflow_id=workflow_id,
                    workflow_type=workflow_type,
                    success=success,
                    processing_time_ms=processing_time,
                    error_type="TestError" if not success else None
                )
        
        # Get summary
        summary = metrics_collector.get_metrics_summary()
        
        # Verify summary structure
        assert "system_metrics" in summary
        assert "aggregate_metrics" in summary
        assert "workflow_types" in summary
        assert "total_workflows_processed" in summary
        assert "overall_success_rate" in summary
        assert "uptime_seconds" in summary
        assert "collection_timestamp" in summary
        
        # Verify counts
        assert summary["total_workflows_processed"] == 3
        assert len(summary["workflow_types"]) == 3
        assert summary["overall_success_rate"] == 200/3  # 2 successes out of 3
        
        # Verify system metrics
        system_metrics = summary["system_metrics"]
        assert system_metrics["cpu_percent"] == 25.0
        assert system_metrics["memory_usage_mb"] == 256.0
        assert system_metrics["num_threads"] == 12
        
        # Verify aggregate metrics structure
        aggregate_metrics = summary["aggregate_metrics"]
        assert len(aggregate_metrics) == 3
        
        for workflow_type in workflow_types:
            assert workflow_type in aggregate_metrics
            type_metrics = aggregate_metrics[workflow_type]
            assert "total_processed" in type_metrics
            assert "successful_count" in type_metrics
            assert "failed_count" in type_metrics
            assert "success_rate_percent" in type_metrics
            assert "average_processing_time_ms" in type_metrics
    
    def test_get_workflow_type_metrics(self, metrics_collector):
        """Test getting metrics for specific workflow type."""
        workflow_type = "data_analysis"
        
        # Should return None for non-existent type
        assert metrics_collector.get_workflow_type_metrics("nonexistent") is None
        
        # Add some data
        for i in range(5):
            workflow_id = uuid4()
            processing_time = 100 + i * 20
            success = i < 3  # 3 successes, 2 failures
            
            with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=40.0 + i * 5):
                metrics_collector.record_workflow_completion(
                    workflow_id=workflow_id,
                    workflow_type=workflow_type,
                    success=success,
                    processing_time_ms=processing_time
                )
        
        # Get metrics for the type
        type_metrics = metrics_collector.get_workflow_type_metrics(workflow_type)
        
        assert type_metrics is not None
        assert type_metrics["workflow_type"] == workflow_type
        assert type_metrics["total_processed"] == 5
        assert type_metrics["successful_count"] == 3
        assert type_metrics["failed_count"] == 2
        assert type_metrics["success_rate_percent"] == 60.0
        assert type_metrics["min_processing_time_ms"] == 100.0
        assert type_metrics["max_processing_time_ms"] == 180.0
        assert len(type_metrics["recent_processing_times"]) == 5
    
    def test_get_recent_workflows(self, metrics_collector):
        """Test getting recent workflow metrics."""
        
        # Add multiple workflows
        workflow_data = [
            ("data_analysis", True, 150.0),
            ("report_generation", False, 200.0),
            ("document_regeneration", True, 175.0),
            ("data_analysis", True, 125.0),
            ("report_generation", True, 225.0),
        ]
        
        for workflow_type, success, processing_time in workflow_data:
            workflow_id = uuid4()
            with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0):
                metrics_collector.record_workflow_completion(
                    workflow_id=workflow_id,
                    workflow_type=workflow_type,
                    success=success,
                    processing_time_ms=processing_time
                )
        
        # Get recent workflows (default limit = 10)
        recent_workflows = metrics_collector.get_recent_workflows()
        
        assert len(recent_workflows) == 5
        
        # Verify structure of recent workflow data
        for workflow in recent_workflows:
            assert "workflow_id" in workflow
            assert "workflow_type" in workflow
            assert "processing_time_ms" in workflow
            assert "memory_usage_mb" in workflow
            assert "success" in workflow
            assert "started_at" in workflow
            assert "completed_at" in workflow
        
        # Test with custom limit
        recent_workflows_limited = metrics_collector.get_recent_workflows(limit=3)
        assert len(recent_workflows_limited) == 3
        
        # Should be the most recent 3
        expected_times = [225.0, 125.0, 175.0]
        actual_times = [wf["processing_time_ms"] for wf in recent_workflows_limited]
        assert actual_times == expected_times
    
    def test_reset_metrics(self, metrics_collector):
        """Test resetting all collected metrics."""
        
        # Add some data
        workflow_id = uuid4()
        with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0):
            metrics_collector.record_workflow_completion(
                workflow_id=workflow_id,
                workflow_type="test_type",
                success=True,
                processing_time_ms=150.0
            )
        
        # Verify data exists
        summary_before = metrics_collector.get_metrics_summary()
        assert summary_before["total_workflows_processed"] == 1
        
        # Reset metrics
        metrics_collector.reset_metrics()
        
        # Verify reset
        summary_after = metrics_collector.get_metrics_summary()
        assert summary_after["total_workflows_processed"] == 0
        assert len(metrics_collector._workflow_metrics) == 0
        assert len(metrics_collector._aggregate_metrics) == 0
        assert len(metrics_collector._system_metrics) > 0  # System metrics should be re-initialized
    
    def test_workflow_history_max_length(self, metrics_collector):
        """Test that workflow history respects max length."""
        
        # Collector was initialized with max_workflow_history=50
        # Add more workflows than the limit
        for i in range(75):
            workflow_id = uuid4()
            with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0):
                metrics_collector.record_workflow_completion(
                    workflow_id=workflow_id,
                    workflow_type="test_type",
                    success=True,
                    processing_time_ms=100.0 + i
                )
        
        # Should only keep the last 50
        assert len(metrics_collector._workflow_metrics) == 50
        
        # Verify it kept the most recent ones
        recent_workflows = metrics_collector.get_recent_workflows(limit=50)
        assert len(recent_workflows) == 50
        
        # The oldest should have processing_time_ms = 125.0 (100 + 25)
        # The newest should have processing_time_ms = 174.0 (100 + 74)
        processing_times = [wf["processing_time_ms"] for wf in recent_workflows]
        assert min(processing_times) == 125.0
        assert max(processing_times) == 174.0
    
    def test_thread_safety(self, metrics_collector):
        """Test thread safety of metrics collector."""
        
        def worker_function(thread_id: int, iterations: int):
            """Worker function for threading test."""
            for i in range(iterations):
                workflow_id = uuid4()
                workflow_type = f"thread_{thread_id}_type"
                
                with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0):
                    metrics_collector.record_workflow_completion(
                        workflow_id=workflow_id,
                        workflow_type=workflow_type,
                        success=i % 3 != 0,  # ~66% success rate
                        processing_time_ms=100.0 + i,
                        error_type="ThreadTestError" if i % 3 == 0 else None
                    )
        
        # Start multiple threads
        threads = []
        iterations_per_thread = 20
        num_threads = 5
        
        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=worker_function,
                args=(thread_id, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify total workflows processed
        summary = metrics_collector.get_metrics_summary()
        expected_total = num_threads * iterations_per_thread
        assert summary["total_workflows_processed"] == expected_total
        
        # Verify workflow types
        assert len(summary["workflow_types"]) == num_threads
        
        # Verify aggregate metrics consistency
        total_from_aggregates = sum(
            summary["aggregate_metrics"][wt]["total_processed"]
            for wt in summary["workflow_types"]
        )
        assert total_from_aggregates == expected_total
    
    @patch('omnibase_core.patterns.reducer_pattern_engine.v1_0_0.metrics.psutil')
    def test_system_metrics_error_handling(self, mock_psutil, metrics_collector):
        """Test error handling in system metrics collection."""
        
        # Mock psutil to raise an exception
        mock_psutil.Process.side_effect = Exception("Mock psutil error")
        
        # This should not raise an exception
        metrics_collector._update_system_metrics()
        
        # System metrics should still be available (may be empty or default)
        summary = metrics_collector.get_metrics_summary()
        assert "system_metrics" in summary
    
    def test_memory_usage_error_handling(self, metrics_collector):
        """Test error handling in memory usage collection."""
        
        # Mock _get_memory_usage_mb to raise an exception
        with patch.object(metrics_collector, '_get_memory_usage_mb', side_effect=Exception("Memory error")):
            # This should not raise an exception
            workflow_id = uuid4()
            metrics_collector.record_workflow_completion(
                workflow_id=workflow_id,
                workflow_type="error_test",
                success=True,
                processing_time_ms=100.0
            )
        
        # Should still record the workflow
        summary = metrics_collector.get_metrics_summary()
        assert summary["total_workflows_processed"] == 1
    
    def test_aggregate_metrics_edge_cases(self, metrics_collector):
        """Test edge cases in aggregate metrics calculations."""
        
        # Test single workflow
        workflow_id = uuid4()
        with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0):
            metrics_collector.record_workflow_completion(
                workflow_id=workflow_id,
                workflow_type="edge_case_test",
                success=True,
                processing_time_ms=100.0
            )
        
        type_metrics = metrics_collector.get_workflow_type_metrics("edge_case_test")
        assert type_metrics["success_rate_percent"] == 100.0
        assert type_metrics["average_processing_time_ms"] == 100.0
        assert type_metrics["min_processing_time_ms"] == 100.0
        assert type_metrics["max_processing_time_ms"] == 100.0
        
        # Test zero processing time
        workflow_id2 = uuid4()
        with patch.object(metrics_collector, '_get_memory_usage_mb', return_value=50.0):
            metrics_collector.record_workflow_completion(
                workflow_id=workflow_id2,
                workflow_type="zero_time_test",
                success=True,
                processing_time_ms=0.0
            )
        
        zero_time_metrics = metrics_collector.get_workflow_type_metrics("zero_time_test")
        assert zero_time_metrics["average_processing_time_ms"] == 0.0
        assert zero_time_metrics["min_processing_time_ms"] == 0.0