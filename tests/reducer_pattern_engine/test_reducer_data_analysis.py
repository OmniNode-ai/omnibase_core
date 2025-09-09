"""
Unit tests for ReducerDataAnalysisSubreducer - Data analysis workflow subreducer.

Tests comprehensive data analysis functionality including statistical processing,
data validation, multiple analysis types, and error handling.
"""

import statistics
from unittest.mock import patch
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import OnexError
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_data_analysis import (
    ReducerDataAnalysisSubreducer,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    ModelWorkflowRequest,
    WorkflowType,
)


class TestReducerDataAnalysisSubreducer:
    """Test suite for ReducerDataAnalysisSubreducer functionality."""

    @pytest.fixture
    def subreducer(self) -> ReducerDataAnalysisSubreducer:
        """Create a ReducerDataAnalysisSubreducer instance for testing."""
        return ReducerDataAnalysisSubreducer("test_data_analysis")

    def test_subreducer_initialization(self, subreducer):
        """Test proper subreducer initialization."""
        assert subreducer.name == "test_data_analysis"
        assert subreducer._processing_metrics["total_processed"] == 0
        assert subreducer._processing_metrics["successful_analyses"] == 0
        assert subreducer._processing_metrics["failed_analyses"] == 0
        assert len(subreducer._supported_analyses) == 4

        # Check supported analysis types
        expected_analyses = {"descriptive", "correlation", "trend", "distribution"}
        assert set(subreducer._supported_analyses.keys()) == expected_analyses

    def test_supports_workflow_type(self, subreducer):
        """Test workflow type support validation."""
        # Should support DATA_ANALYSIS
        assert subreducer.supports_workflow_type(WorkflowType.DATA_ANALYSIS) is True
        assert subreducer.supports_workflow_type("data_analysis") is True

        # Should not support other types
        assert (
            subreducer.supports_workflow_type(WorkflowType.DOCUMENT_REGENERATION)
            is False
        )
        assert (
            subreducer.supports_workflow_type(WorkflowType.REPORT_GENERATION) is False
        )
        assert subreducer.supports_workflow_type("invalid_type") is False

    @pytest.mark.asyncio
    async def test_process_successful_descriptive_analysis(self, subreducer):
        """Test successful descriptive statistical analysis."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-descriptive-001",
            correlation_id=uuid4(),
            payload={
                "data": [10, 20, 30, 40, 50, 25, 35, 45],
                "analysis_types": ["descriptive"],
                "data_validation": {"remove_outliers": False},
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True
        assert result.error_message is None
        assert result.subreducer_name == "test_data_analysis"
        assert result.processing_time_ms > 0

        # Verify result structure
        assert "analysis_results" in result.result
        assert "analysis_summary" in result.result
        assert "data_statistics" in result.result

        # Verify descriptive analysis results
        descriptive = result.result["analysis_results"]["descriptive"]
        assert descriptive["count"] == 8
        assert descriptive["mean"] == statistics.mean([10, 20, 30, 40, 50, 25, 35, 45])
        assert descriptive["median"] == statistics.median(
            [10, 20, 30, 40, 50, 25, 35, 45],
        )
        assert "std_dev" in descriptive
        assert "variance" in descriptive
        assert "min" in descriptive
        assert "max" in descriptive
        assert "quartiles" in descriptive

        # Verify data statistics
        data_stats = result.result["data_statistics"]
        assert data_stats["original_data_points"] == 8
        assert data_stats["cleaned_data_points"] == 8
        assert data_stats["analysis_types_performed"] == ["descriptive"]

    @pytest.mark.asyncio
    async def test_process_multiple_analysis_types(self, subreducer):
        """Test processing with multiple analysis types."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-multi-001",
            correlation_id=uuid4(),
            payload={
                "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "analysis_types": ["descriptive", "trend", "distribution"],
                "data_validation": {"remove_outliers": False},
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True

        # Verify all analysis types were performed
        analysis_results = result.result["analysis_results"]
        assert "descriptive" in analysis_results
        assert "trend" in analysis_results
        assert "distribution" in analysis_results

        # Verify descriptive analysis
        descriptive = analysis_results["descriptive"]
        assert descriptive["count"] == 10
        assert descriptive["mean"] == 5.5

        # Verify trend analysis
        trend = analysis_results["trend"]
        assert "slope" in trend
        assert "intercept" in trend
        assert "r_squared" in trend
        assert "trend_direction" in trend
        assert trend["slope"] > 0  # Should be positive slope for 1-10

        # Verify distribution analysis
        distribution = analysis_results["distribution"]
        assert "distribution_type" in distribution
        assert "skewness" in distribution
        assert "kurtosis" in distribution
        assert "normality_indicators" in distribution

    @pytest.mark.asyncio
    async def test_process_correlation_analysis(self, subreducer):
        """Test correlation analysis functionality."""
        # Create data with some autocorrelation
        data = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]

        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-correlation-001",
            correlation_id=uuid4(),
            payload={"data": data, "analysis_types": ["correlation"]},
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True

        # Verify correlation analysis
        correlation = result.result["analysis_results"]["correlation"]
        assert "autocorrelation_lag1" in correlation
        assert "data_points_used" in correlation
        assert "interpretation" in correlation

        # Should detect strong positive correlation
        assert correlation["autocorrelation_lag1"] > 0.8
        assert "strong positive correlation" in correlation["interpretation"]

    @pytest.mark.asyncio
    async def test_process_with_data_cleaning(self, subreducer):
        """Test data validation and cleaning functionality."""
        # Data with mixed types, None values, and outliers
        messy_data = [1, 2, None, "invalid", 3, 4, 5, 100, 6, 7, 8]

        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-cleaning-001",
            correlation_id=uuid4(),
            payload={
                "data": messy_data,
                "analysis_types": ["descriptive"],
                "data_validation": {"remove_outliers": True, "handle_missing": True},
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing despite messy data
        assert result.success is True

        # Verify data was cleaned
        data_stats = result.result["data_statistics"]
        assert data_stats["original_data_points"] == len(messy_data)
        assert data_stats["cleaned_data_points"] < len(
            messy_data,
        )  # Some data should be removed

        # Outlier (100) should be removed
        descriptive = result.result["analysis_results"]["descriptive"]
        assert descriptive["max"] < 100  # Outlier should be filtered out

        # Should have reasonable data quality score
        assert data_stats["data_quality_score"] > 0.5

    @pytest.mark.asyncio
    async def test_process_insufficient_data_for_analysis(self, subreducer):
        """Test handling of insufficient data scenarios."""
        # Single data point
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-insufficient-001",
            correlation_id=uuid4(),
            payload={"data": [42], "analysis_types": ["trend", "correlation"]},
        )

        result = await subreducer.process(request)

        # Should still succeed but with limited analysis
        assert result.success is True

        analysis_results = result.result["analysis_results"]

        # Trend analysis should indicate insufficient data
        trend = analysis_results.get("trend", {})
        if "error" in trend:
            assert "Insufficient data" in trend["error"]

        # Correlation analysis should indicate insufficient data
        correlation = analysis_results.get("correlation", {})
        if "error" in correlation:
            assert "Insufficient data" in correlation["error"]

    @pytest.mark.asyncio
    async def test_process_invalid_request_payload(self, subreducer):
        """Test handling of invalid request payloads."""
        # Missing data field
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-invalid-001",
            correlation_id=uuid4(),
            payload={"analysis_types": ["descriptive"]},  # Missing 'data'
        )

        result = await subreducer.process(request)

        # Should fail gracefully
        assert result.success is False
        assert result.error_message is not None
        assert "Data field is required" in result.error_message
        assert result.error_details["error_type"] == "OnexError"

    @pytest.mark.asyncio
    async def test_process_empty_data_list(self, subreducer):
        """Test handling of empty data list."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-empty-001",
            correlation_id=uuid4(),
            payload={"data": [], "analysis_types": ["descriptive"]},
        )

        result = await subreducer.process(request)

        # Should fail due to empty data
        assert result.success is False
        assert result.error_message is not None
        assert "non-empty list" in result.error_message

    @pytest.mark.asyncio
    async def test_process_no_valid_numeric_data(self, subreducer):
        """Test handling of data with no valid numeric values."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-no-numeric-001",
            correlation_id=uuid4(),
            payload={
                "data": ["string", None, "another_string", {}],
                "analysis_types": ["descriptive"],
                "data_validation": {"handle_missing": True},
            },
        )

        result = await subreducer.process(request)

        # Should fail due to no valid numeric data
        assert result.success is False
        assert result.error_message is not None
        assert "No valid numeric data points found" in result.error_message

    @pytest.mark.asyncio
    async def test_process_unsupported_analysis_types(self, subreducer):
        """Test handling of unsupported analysis types."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-unsupported-001",
            correlation_id=uuid4(),
            payload={
                "data": [1, 2, 3, 4, 5],
                "analysis_types": [
                    "unsupported_type",
                    "another_invalid_type",
                    "descriptive",
                ],
            },
        )

        result = await subreducer.process(request)

        # Should succeed with supported types only
        assert result.success is True

        # Should only have performed descriptive analysis
        analysis_results = result.result["analysis_results"]
        assert "descriptive" in analysis_results
        assert "unsupported_type" not in analysis_results
        assert "another_invalid_type" not in analysis_results

        # Should have performed only the valid analysis type
        data_stats = result.result["data_statistics"]
        assert data_stats["analysis_types_performed"] == ["descriptive"]

    @pytest.mark.asyncio
    async def test_process_edge_case_single_value_repeated(self, subreducer):
        """Test analysis of data with single repeated value."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-repeated-001",
            correlation_id=uuid4(),
            payload={
                "data": [5, 5, 5, 5, 5, 5, 5],
                "analysis_types": ["descriptive", "trend", "distribution"],
            },
        )

        result = await subreducer.process(request)

        # Should succeed
        assert result.success is True

        analysis_results = result.result["analysis_results"]

        # Descriptive analysis should handle zero variance
        descriptive = analysis_results["descriptive"]
        assert descriptive["mean"] == 5.0
        assert descriptive["std_dev"] == 0.0
        assert descriptive["variance"] == 0.0
        assert descriptive["min"] == descriptive["max"] == 5.0

        # Trend analysis should show flat line
        trend = analysis_results["trend"]
        assert trend["slope"] == 0.0  # Flat line
        assert trend["trend_direction"] == "flat"

    @pytest.mark.asyncio
    async def test_process_large_dataset_performance(self, subreducer):
        """Test performance with larger dataset."""
        # Generate larger dataset (1000 points)
        import random

        random.seed(42)  # For reproducible results
        large_data = [random.gauss(50, 10) for _ in range(1000)]

        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-large-001",
            correlation_id=uuid4(),
            payload={
                "data": large_data,
                "analysis_types": ["descriptive", "trend", "distribution"],
                "data_validation": {"remove_outliers": False},
            },
        )

        result = await subreducer.process(request)

        # Should succeed and complete reasonably quickly
        assert result.success is True
        assert result.processing_time_ms < 5000  # Should complete within 5 seconds

        # Verify all analyses completed
        analysis_results = result.result["analysis_results"]
        assert len(analysis_results) == 3

        # Verify data statistics
        data_stats = result.result["data_statistics"]
        assert data_stats["original_data_points"] == 1000
        assert data_stats["cleaned_data_points"] == 1000  # No outlier removal

    @pytest.mark.asyncio
    async def test_processing_metrics_tracking(self, subreducer):
        """Test that processing metrics are properly tracked."""
        initial_metrics = subreducer.get_processing_metrics()
        assert initial_metrics["total_processed"] == 0

        # Process successful request
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-metrics-001",
            correlation_id=uuid4(),
            payload={"data": [1, 2, 3, 4, 5], "analysis_types": ["descriptive"]},
        )

        result = await subreducer.process(request)
        assert result.success is True

        # Check metrics after success
        success_metrics = subreducer.get_processing_metrics()
        assert success_metrics["total_processed"] == 1
        assert success_metrics["successful_analyses"] == 1
        assert success_metrics["failed_analyses"] == 0
        assert success_metrics["total_data_points_analyzed"] == 5
        assert success_metrics["average_processing_time_ms"] > 0
        assert "descriptive" in success_metrics["analysis_types_used"]
        assert success_metrics["analysis_types_used"]["descriptive"] == 1

        # Process failing request
        failing_request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-metrics-002",
            correlation_id=uuid4(),
            payload={"invalid": "payload"},  # Missing required fields
        )

        failing_result = await subreducer.process(failing_request)
        assert failing_result.success is False

        # Check metrics after failure
        failure_metrics = subreducer.get_processing_metrics()
        assert failure_metrics["total_processed"] == 2
        assert failure_metrics["successful_analyses"] == 1
        assert failure_metrics["failed_analyses"] == 1

    def test_data_quality_score_calculation(self, subreducer):
        """Test data quality score calculation."""
        # Perfect data (all valid)
        perfect_score = subreducer._calculate_data_quality_score(
            [1, 2, 3, 4, 5],
            [1, 2, 3, 4, 5],
        )
        assert perfect_score == 1.0

        # Good data (some data removed but high retention)
        good_score = subreducer._calculate_data_quality_score(
            [1, 2, 3, 4, 5],
            [1, 2, 3, 4],
        )
        assert 0.8 <= good_score <= 1.0

        # Poor data (low retention)
        poor_score = subreducer._calculate_data_quality_score(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            [1, 2],
        )
        assert poor_score < 0.5

        # Empty original data
        empty_score = subreducer._calculate_data_quality_score([], [])
        assert empty_score == 0.0

    def test_outlier_removal(self, subreducer):
        """Test outlier removal functionality."""
        # Data with clear outliers
        data_with_outliers = [1, 2, 3, 4, 5, 100, 6, 7, 8, 9, 10]
        cleaned_data = subreducer._remove_outliers(data_with_outliers)

        # Outlier (100) should be removed
        assert 100 not in cleaned_data
        assert len(cleaned_data) < len(data_with_outliers)

        # Test with insufficient data points
        small_data = [1, 2, 3]
        cleaned_small = subreducer._remove_outliers(small_data)
        assert cleaned_small == small_data  # Should return unchanged

    def test_statistical_analysis_methods(self, subreducer):
        """Test individual statistical analysis methods."""
        test_data = [10, 20, 30, 40, 50]
        config = {"confidence_level": 0.95}

        # Test descriptive analysis
        descriptive = subreducer._perform_descriptive_analysis(test_data, config)
        assert "error" not in descriptive
        assert descriptive["count"] == 5
        assert descriptive["mean"] == 30.0
        assert descriptive["median"] == 30.0

        # Test trend analysis
        trend = subreducer._perform_trend_analysis(test_data, config)
        assert "error" not in trend
        assert trend["slope"] == 10.0  # Perfect linear trend
        assert trend["r_squared"] == 1.0  # Perfect fit
        assert trend["trend_direction"] == "increasing"

        # Test distribution analysis
        distribution = subreducer._perform_distribution_analysis(test_data, config)
        assert "error" not in distribution
        assert "skewness" in distribution
        assert "kurtosis" in distribution
        assert "distribution_type" in distribution

    def test_analysis_with_different_configurations(self, subreducer):
        """Test analysis behavior with different configuration options."""
        test_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        # Test with outlier removal enabled
        config_with_outlier_removal = {
            "data": test_data,
            "analysis_types": ["descriptive"],
            "data_validation": {"remove_outliers": True, "handle_missing": True},
        }
        cleaned_with_removal = subreducer._validate_and_clean_data(
            config_with_outlier_removal["data"],
            config_with_outlier_removal,
        )

        # Test with outlier removal disabled
        config_without_outlier_removal = {
            "data": test_data,
            "analysis_types": ["descriptive"],
            "data_validation": {"remove_outliers": False, "handle_missing": True},
        }
        cleaned_without_removal = subreducer._validate_and_clean_data(
            config_without_outlier_removal["data"],
            config_without_outlier_removal,
        )

        # Both should be the same for this clean data
        assert len(cleaned_with_removal) == len(cleaned_without_removal)

        # Test with missing data handling disabled
        messy_data = [1, 2, None, 4, 5]
        config_strict = {
            "data": messy_data,
            "data_validation": {"handle_missing": False},
        }

        # Should raise error when encountering None with handle_missing=False
        with pytest.raises(OnexError):
            subreducer._validate_and_clean_data(config_strict["data"], config_strict)

    def test_interpretation_methods(self, subreducer):
        """Test interpretation and classification methods."""
        # Test correlation interpretation
        assert "strong positive" in subreducer._interpret_correlation(0.9)
        assert "strong negative" in subreducer._interpret_correlation(-0.9)
        assert "moderate positive" in subreducer._interpret_correlation(0.6)
        assert "weak" in subreducer._interpret_correlation(0.2)
        assert "very weak" in subreducer._interpret_correlation(0.1)

        # Test trend strength classification
        assert subreducer._classify_trend_strength(0.2, 1.0) == "strong"
        assert subreducer._classify_trend_strength(0.07, 1.0) == "moderate"
        assert subreducer._classify_trend_strength(0.02, 1.0) == "weak"
        assert subreducer._classify_trend_strength(0.005, 1.0) == "very weak"

        # Test distribution classification
        assert "approximately normal" in subreducer._classify_distribution(0.1, 0.1)
        assert "right-skewed" in subreducer._classify_distribution(1.5, 0.1)
        assert "left-skewed" in subreducer._classify_distribution(-1.5, 0.1)
        assert "heavy-tailed" in subreducer._classify_distribution(0.1, 4.0)

    @pytest.mark.asyncio
    async def test_error_handling_during_analysis(self, subreducer):
        """Test error handling during statistical analysis operations."""
        # Mock statistics functions to raise errors
        with patch(
            "statistics.stdev",
            side_effect=statistics.StatisticsError("Mock statistics error"),
        ):
            request = ModelWorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id="test-stats-error-001",
                correlation_id=uuid4(),
                payload={"data": [1, 2, 3], "analysis_types": ["descriptive"]},
            )

            result = await subreducer.process(request)

            # Should still succeed but with error in specific analysis
            assert result.success is True
            descriptive = result.result["analysis_results"]["descriptive"]
            # Should have some values but may have defaults or errors for problematic calculations
            assert "count" in descriptive  # Basic counts should still work

    @pytest.mark.asyncio
    async def test_concurrent_processing_safety(self, subreducer):
        """Test thread safety during concurrent processing."""
        import asyncio

        # Create multiple requests to process concurrently
        requests = []
        for i in range(10):
            request = ModelWorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id=f"concurrent-{i}",
                correlation_id=uuid4(),
                payload={
                    "data": list(range(i + 1, i + 11)),  # Different data for each
                    "analysis_types": ["descriptive"],
                    "metadata": {"thread_id": i},
                },
            )
            requests.append(request)

        # Process all concurrently
        results = await asyncio.gather(*[subreducer.process(req) for req in requests])

        # All should succeed
        assert all(result.success for result in results)
        assert len(results) == 10

        # Verify metrics are consistent
        final_metrics = subreducer.get_processing_metrics()
        assert final_metrics["total_processed"] == 10
        assert final_metrics["successful_analyses"] == 10
        assert final_metrics["failed_analyses"] == 0
