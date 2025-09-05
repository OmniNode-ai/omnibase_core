"""
Unit tests for ReducerReportGenerationSubreducer - Report generation workflow subreducer.

Tests comprehensive report generation functionality including template processing,
output formatting, data aggregation, and validation capabilities.
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_report_generation import (
    ReducerReportGenerationSubreducer,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    ModelSubreducerResult,
    ModelWorkflowRequest,
    WorkflowType,
)


class TestReducerReportGenerationSubreducer:
    """Test suite for ReducerReportGenerationSubreducer functionality."""

    @pytest.fixture
    def subreducer(self) -> ReducerReportGenerationSubreducer:
        """Create a ReducerReportGenerationSubreducer instance for testing."""
        return ReducerReportGenerationSubreducer("test_report_generation")

    def test_subreducer_initialization(self, subreducer):
        """Test proper subreducer initialization."""
        assert subreducer.name == "test_report_generation"
        assert subreducer._processing_metrics["total_processed"] == 0
        assert subreducer._processing_metrics["successful_reports"] == 0
        assert subreducer._processing_metrics["failed_reports"] == 0

        # Check supported formats
        expected_formats = {"json", "html", "csv", "txt", "markdown"}
        assert set(subreducer._supported_formats.keys()) == expected_formats

        # Check supported templates
        expected_templates = {"summary", "detailed", "dashboard", "custom"}
        assert set(subreducer._template_processors.keys()) == expected_templates

    def test_supports_workflow_type(self, subreducer):
        """Test workflow type support validation."""
        # Should support REPORT_GENERATION
        assert subreducer.supports_workflow_type(WorkflowType.REPORT_GENERATION) is True
        assert subreducer.supports_workflow_type("report_generation") is True

        # Should not support other types
        assert subreducer.supports_workflow_type(WorkflowType.DATA_ANALYSIS) is False
        assert (
            subreducer.supports_workflow_type(WorkflowType.DOCUMENT_REGENERATION)
            is False
        )
        assert subreducer.supports_workflow_type("invalid_type") is False

    @pytest.mark.asyncio
    async def test_process_successful_summary_report_json(self, subreducer):
        """Test successful summary report generation in JSON format."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-summary-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "summary",
                "output_format": "json",
                "report_title": "Test Summary Report",
                "report_description": "A test summary report for validation",
                "data": {
                    "metrics": [10, 20, 30, 40, 50],
                    "categories": {"A": 25, "B": 35, "C": 40},
                    "status": "completed",
                },
                "template_config": {"include_aggregations": True},
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True
        assert result.error_message is None
        assert result.subreducer_name == "test_report_generation"
        assert result.processing_time_ms > 0

        # Verify result structure
        assert "report_content" in result.result
        assert "report_metadata" in result.result
        assert "validation_results" in result.result
        assert "generation_statistics" in result.result

        # Verify report content structure
        report_content = result.result["report_content"]["report"]
        assert report_content["title"] == "Test Summary Report"
        assert report_content["template_type"] == "summary"
        assert "sections" in report_content
        assert (
            len(report_content["sections"]) >= 2
        )  # At least executive summary and data overview

        # Verify generation statistics
        gen_stats = result.result["generation_statistics"]
        assert gen_stats["template_type"] == "summary"
        assert gen_stats["output_format"] == "json"
        assert gen_stats["sections_generated"] > 0
        assert gen_stats["data_points_processed"] == 3  # metrics, categories, status

        # Verify validation passed
        validation = result.result["validation_results"]
        assert validation["is_valid"] is True
        assert "JSON format validation: PASSED" in validation["validation_checks"]

    @pytest.mark.asyncio
    async def test_process_detailed_report_html(self, subreducer):
        """Test detailed report generation in HTML format."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-detailed-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "detailed",
                "output_format": "html",
                "report_title": "Detailed Analysis Report",
                "data": {
                    "performance_metrics": [85, 90, 88, 92, 87],
                    "user_feedback": {"positive": 45, "neutral": 30, "negative": 25},
                    "system_health": {"cpu_usage": 65.5, "memory_usage": 78.2},
                },
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True

        # Verify HTML output
        html_content = result.result["report_content"]
        assert isinstance(html_content, str)
        assert html_content.startswith("<!DOCTYPE html>")
        assert "Detailed Analysis Report" in html_content
        assert "</html>" in html_content

        # Verify sections are present in HTML
        assert "Introduction" in html_content
        assert "Analysis:" in html_content  # Data analysis sections
        assert "Conclusions" in html_content

    @pytest.mark.asyncio
    async def test_process_dashboard_report_markdown(self, subreducer):
        """Test dashboard report generation in Markdown format."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-dashboard-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "dashboard",
                "output_format": "markdown",
                "report_title": "Performance Dashboard",
                "data": {
                    "kpis": {"revenue": 150000, "users": 2500, "conversion": 3.2},
                    "trends": [1.2, 1.5, 1.8, 2.1, 2.3],
                    "alerts": ["High CPU usage", "Memory threshold exceeded"],
                },
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True

        # Verify Markdown output
        md_content = result.result["report_content"]
        assert isinstance(md_content, str)
        assert md_content.startswith("# Performance Dashboard")
        assert "## Key Performance Indicators" in md_content
        assert "## Data Visualization" in md_content
        assert "## Quick Insights" in md_content
        assert "*Generated at:" in md_content  # Timestamp footer

    @pytest.mark.asyncio
    async def test_process_custom_template_csv(self, subreducer):
        """Test custom template report generation in CSV format."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-custom-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "custom",
                "output_format": "csv",
                "report_title": "Custom Data Report",
                "data": {
                    "sales_data": [100, 150, 200, 175, 225],
                    "regions": {"North": 500, "South": 400, "East": 300, "West": 350},
                },
                "template_config": {
                    "sections": [
                        {"title": "Sales Overview", "type": "summary"},
                        {"title": "Regional Performance", "type": "regional"},
                    ]
                },
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True

        # Verify CSV output
        csv_content = result.result["report_content"]
        assert isinstance(csv_content, str)
        assert "Report Title,Custom Data Report" in csv_content
        assert "Generated At," in csv_content
        assert "Section,Sales Overview" in csv_content
        assert "Section,Regional Performance" in csv_content

    @pytest.mark.asyncio
    async def test_process_text_output_format(self, subreducer):
        """Test plain text output format."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-text-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "summary",
                "output_format": "txt",
                "report_title": "Plain Text Report",
                "data": {"test_data": [1, 2, 3, 4, 5]},
            },
        )

        result = await subreducer.process(request)

        # Verify successful processing
        assert result.success is True

        # Verify text output
        text_content = result.result["report_content"]
        assert isinstance(text_content, str)
        assert "Plain Text Report" in text_content
        assert "=" * 50 in text_content  # Title separator
        assert "-" * 30 in text_content  # Section separator
        assert "Generated at:" in text_content

    @pytest.mark.asyncio
    async def test_process_invalid_request_missing_template_type(self, subreducer):
        """Test handling of request missing template_type."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-invalid-001",
            correlation_id=uuid4(),
            payload={
                "output_format": "json",
                "data": {"test": "data"},
                # Missing template_type
            },
        )

        result = await subreducer.process(request)

        # Should fail due to missing template_type
        assert result.success is False
        assert result.error_message is not None
        assert "template_type is required" in result.error_message
        assert result.error_details["error_type"] == "OnexError"

    @pytest.mark.asyncio
    async def test_process_invalid_request_missing_output_format(self, subreducer):
        """Test handling of request missing output_format."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-invalid-002",
            correlation_id=uuid4(),
            payload={
                "template_type": "summary",
                "data": {"test": "data"},
                # Missing output_format
            },
        )

        result = await subreducer.process(request)

        # Should fail due to missing output_format
        assert result.success is False
        assert result.error_message is not None
        assert "output_format is required" in result.error_message

    @pytest.mark.asyncio
    async def test_process_empty_payload(self, subreducer):
        """Test handling of empty payload."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-empty-001",
            correlation_id=uuid4(),
            payload={},
        )

        result = await subreducer.process(request)

        # Should fail due to empty payload
        assert result.success is False
        assert result.error_message is not None
        assert "template_type is required" in result.error_message

    @pytest.mark.asyncio
    async def test_process_unsupported_template_type(self, subreducer):
        """Test handling of unsupported template type (should use custom fallback)."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-unsupported-template-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "nonexistent_template",
                "output_format": "json",
                "report_title": "Fallback Test Report",
                "data": {"test_data": "value"},
            },
        )

        result = await subreducer.process(request)

        # Should succeed using custom template processor
        assert result.success is True

        # Verify it used custom processing
        report_content = result.result["report_content"]["report"]
        assert report_content["template_type"] == "custom"
        assert "sections" in report_content

    @pytest.mark.asyncio
    async def test_process_unsupported_output_format(self, subreducer):
        """Test handling of unsupported output format (should default to JSON)."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-unsupported-format-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "summary",
                "output_format": "unsupported_format",
                "report_title": "Format Fallback Test",
                "data": {"test_data": "value"},
            },
        )

        result = await subreducer.process(request)

        # Should succeed using JSON fallback
        assert result.success is True

        # Should be JSON format
        report_content = result.result["report_content"]
        assert isinstance(report_content, dict)
        assert "report" in report_content
        assert "metadata" in report_content
        assert report_content["metadata"]["format"] == "json"

    @pytest.mark.asyncio
    async def test_process_complex_data_structures(self, subreducer):
        """Test processing with complex nested data structures."""
        complex_data = {
            "nested_dict": {
                "level1": {
                    "level2": {
                        "values": [1, 2, 3, 4, 5],
                        "metadata": {"type": "test", "created": "2023-01-01"},
                    }
                }
            },
            "mixed_list": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"},
            ],
            "numeric_data": 42.5,
            "text_data": "Sample text content",
        }

        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-complex-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "detailed",
                "output_format": "json",
                "report_title": "Complex Data Report",
                "data": complex_data,
            },
        )

        result = await subreducer.process(request)

        # Should succeed with complex data
        assert result.success is True

        # Verify all data types were processed
        gen_stats = result.result["generation_statistics"]
        assert (
            gen_stats["data_points_processed"] == 4
        )  # nested_dict, mixed_list, numeric_data, text_data
        assert (
            gen_stats["sections_generated"] >= 4
        )  # Introduction + data sections + conclusions

    @pytest.mark.asyncio
    async def test_data_processing_methods(self, subreducer):
        """Test individual data processing methods."""
        # Test list data processing
        list_data = [10, 20, 30, 40, 50]
        processed_list = subreducer._process_list_data(list_data, "test_list")
        assert processed_list["values"] == list_data
        assert processed_list["count"] == 5
        assert processed_list["first"] == 10
        assert processed_list["last"] == 50
        assert processed_list["unique_count"] == 5

        # Test dict data processing
        dict_data = {"key1": "value1", "key2": {"nested": "data"}, "key3": [1, 2, 3]}
        processed_dict = subreducer._process_dict_data(dict_data, "test_dict")
        assert processed_dict["data"] == dict_data
        assert processed_dict["keys"] == ["key1", "key2", "key3"]
        assert processed_dict["key_count"] == 3
        assert processed_dict["has_nested"] is True

        # Test numeric data processing
        processed_int = subreducer._process_numeric_data(1234, "test_int")
        assert processed_int["value"] == 1234
        assert processed_int["formatted"] == "1,234"
        assert processed_int["type"] == "integer"

        processed_float = subreducer._process_numeric_data(1234.56, "test_float")
        assert processed_float["value"] == 1234.56
        assert processed_float["formatted"] == "1,234.56"
        assert processed_float["type"] == "float"

    @pytest.mark.asyncio
    async def test_aggregations_computation(self, subreducer):
        """Test data aggregations computation."""
        test_data = {
            "list_data": {"values": [1, 2, 3, 4, 5], "count": 5},
            "dict_data": {"data": {"key": "value"}, "keys": ["key"]},
            "numeric_data": {"value": 42.5, "type": "float"},
        }

        aggregations = subreducer._compute_data_aggregations(test_data)

        assert aggregations["total_data_keys"] == 3
        assert aggregations["has_lists"] is True
        assert aggregations["has_dicts"] is True
        assert aggregations["total_list_items"] == 5
        assert "list" in aggregations["data_types_present"]
        assert "dict" in aggregations["data_types_present"]
        assert "float" in aggregations["data_types_present"]

    @pytest.mark.asyncio
    async def test_processing_metrics_tracking(self, subreducer):
        """Test that processing metrics are properly tracked."""
        initial_metrics = subreducer.get_processing_metrics()
        assert initial_metrics["total_processed"] == 0

        # Process successful request
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-metrics-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "summary",
                "output_format": "json",
                "data": {"test": [1, 2, 3]},
            },
        )

        result = await subreducer.process(request)
        assert result.success is True

        # Check metrics after success
        success_metrics = subreducer.get_processing_metrics()
        assert success_metrics["total_processed"] == 1
        assert success_metrics["successful_reports"] == 1
        assert success_metrics["failed_reports"] == 0
        assert success_metrics["total_sections_generated"] > 0
        assert success_metrics["average_processing_time_ms"] > 0
        assert "json" in success_metrics["output_formats_used"]
        assert success_metrics["output_formats_used"]["json"] == 1
        assert "summary" in success_metrics["template_types_used"]
        assert success_metrics["template_types_used"]["summary"] == 1

        # Process failing request
        failing_request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-metrics-002",
            correlation_id=uuid4(),
            payload={"invalid": "payload"},  # Missing required fields
        )

        failing_result = await subreducer.process(failing_request)
        assert failing_result.success is False

        # Check metrics after failure
        failure_metrics = subreducer.get_processing_metrics()
        assert failure_metrics["total_processed"] == 2
        assert failure_metrics["successful_reports"] == 1
        assert failure_metrics["failed_reports"] == 1

    def test_format_validation(self, subreducer):
        """Test output format validation."""
        test_content = {
            "title": "Test Report",
            "sections": [{"title": "Section 1", "content": "Test content"}],
            "generation_timestamp": "2023-01-01T12:00:00",
        }

        config = {"output_format": "json", "include_metadata": True}

        # Test JSON validation
        json_output = subreducer._generate_json_output(test_content, config)
        validation_results = subreducer._validate_generated_report(json_output, config)

        assert validation_results["is_valid"] is True
        assert any(
            "JSON format validation: PASSED" in check
            for check in validation_results["validation_checks"]
        )

        # Test empty output validation
        empty_validation = subreducer._validate_generated_report(None, config)
        assert empty_validation["is_valid"] is False
        assert "Generated output is empty" in empty_validation["errors"]

    @pytest.mark.asyncio
    async def test_template_configuration_options(self, subreducer):
        """Test various template configuration options."""
        # Test with include_aggregations enabled
        request_with_agg = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-config-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "summary",
                "output_format": "json",
                "data": {"metrics": [1, 2, 3], "stats": {"avg": 2.0}},
                "template_config": {"include_aggregations": True},
            },
        )

        result = await subreducer.process(request_with_agg)
        assert result.success is True

        # Should have aggregations in processed data
        report = result.result["report_content"]["report"]
        # Aggregations should influence the content structure
        assert len(report["sections"]) >= 2

        # Test with custom metadata and formatting options
        request_with_options = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-config-002",
            correlation_id=uuid4(),
            payload={
                "template_type": "detailed",
                "output_format": "json",
                "data": {"test": "data"},
                "metadata": {"author": "test_user", "version": "1.0"},
                "include_timestamp": True,
                "include_metadata": True,
                "formatting_options": {"compact": False},
            },
        )

        result = await subreducer.process(request_with_options)
        assert result.success is True

        # Verify metadata is included
        metadata = result.result["report_content"]["metadata"]
        assert "author" in metadata
        assert metadata["author"] == "test_user"
        assert metadata["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_report_metadata_generation(self, subreducer):
        """Test comprehensive report metadata generation."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-metadata-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "dashboard",
                "output_format": "html",
                "data": {"test1": [1, 2], "test2": {"key": "value"}},
            },
        )

        result = await subreducer.process(request)
        assert result.success is True

        # Verify report metadata
        metadata = result.result["report_metadata"]
        assert "report_id" in metadata
        assert metadata["template_type"] == "dashboard"
        assert metadata["output_format"] == "html"
        assert metadata["generator"] == "test_report_generation"
        assert metadata["data_points_processed"] == 2
        assert metadata["sections_generated"] >= 2
        assert "generated_at" in metadata
        assert "content_size_estimate" in metadata
        assert "generation_config" in metadata

    @pytest.mark.asyncio
    async def test_error_handling_during_processing(self, subreducer):
        """Test error handling during various processing stages."""
        # Mock a processing function to raise an error
        with patch.object(
            subreducer,
            "_process_report_data",
            side_effect=ValueError("Mock processing error"),
        ):
            request = ModelWorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id="test-error-001",
                correlation_id=uuid4(),
                payload={
                    "template_type": "summary",
                    "output_format": "json",
                    "data": {"test": "data"},
                },
            )

            result = await subreducer.process(request)

            # Should fail gracefully
            assert result.success is False
            assert "Mock processing error" in result.error_message
            assert result.error_details["error_type"] == "ValueError"
            assert (
                result.error_details["failed_at_step"] == "report_generation_processing"
            )

    @pytest.mark.asyncio
    async def test_concurrent_processing_safety(self, subreducer):
        """Test thread safety during concurrent processing."""
        import asyncio

        # Create multiple requests to process concurrently
        requests = []
        for i in range(10):
            request = ModelWorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id=f"concurrent-{i}",
                correlation_id=uuid4(),
                payload={
                    "template_type": "summary",
                    "output_format": "json",
                    "report_title": f"Concurrent Report {i}",
                    "data": {
                        f"data_{i}": list(range(i + 1, i + 6))
                    },  # Different data for each
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
        assert final_metrics["successful_reports"] == 10
        assert final_metrics["failed_reports"] == 0

        # Verify each report has unique content
        report_titles = [
            result.result["report_content"]["report"]["title"] for result in results
        ]
        assert len(set(report_titles)) == 10  # All unique titles

    def test_content_formatting_methods(self, subreducer):
        """Test content formatting for different output formats."""
        test_content = {"key": "value", "number": 42, "list": [1, 2, 3]}

        # Test HTML formatting
        html_formatted = subreducer._format_content_for_html(test_content)
        assert html_formatted.startswith("<pre>")
        assert html_formatted.endswith("</pre>")
        assert str(test_content) in html_formatted

        # Test CSV formatting
        csv_formatted = subreducer._format_content_for_csv(test_content)
        assert isinstance(csv_formatted, list)
        assert len(csv_formatted) == 1
        assert csv_formatted[0].startswith("Content,")

        # Test plain text formatting
        text_formatted = subreducer._format_content_for_text(test_content)
        assert isinstance(text_formatted, str)
        assert str(test_content) == text_formatted

        # Test Markdown formatting
        md_formatted = subreducer._format_content_for_markdown(test_content)
        assert md_formatted.startswith("```")
        assert md_formatted.endswith("```")
        assert str(test_content) in md_formatted

    @pytest.mark.asyncio
    async def test_large_data_performance(self, subreducer):
        """Test performance with large data sets."""
        # Generate large dataset
        large_data = {
            f"dataset_{i}": {
                "values": list(range(i * 100, (i + 1) * 100)),
                "metadata": {"category": f"cat_{i}", "weight": i * 0.1},
            }
            for i in range(50)  # 50 datasets with 100 values each
        }

        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="test-large-001",
            correlation_id=uuid4(),
            payload={
                "template_type": "detailed",
                "output_format": "json",
                "report_title": "Large Data Report",
                "data": large_data,
            },
        )

        result = await subreducer.process(request)

        # Should succeed and complete reasonably quickly
        assert result.success is True
        assert result.processing_time_ms < 10000  # Should complete within 10 seconds

        # Verify all data was processed
        gen_stats = result.result["generation_statistics"]
        assert gen_stats["data_points_processed"] == 50
        assert (
            gen_stats["sections_generated"] >= 50
        )  # At least one section per dataset + intro/conclusion

    @pytest.mark.asyncio
    async def test_all_output_formats_consistency(self, subreducer):
        """Test that all supported output formats work consistently."""
        base_request_payload = {
            "template_type": "summary",
            "report_title": "Format Consistency Test",
            "data": {"test_metrics": [10, 20, 30], "status": "active"},
        }

        formats_to_test = ["json", "html", "csv", "txt", "markdown"]
        results = {}

        for output_format in formats_to_test:
            request = ModelWorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id=f"test-format-{output_format}",
                correlation_id=uuid4(),
                payload={**base_request_payload, "output_format": output_format},
            )

            result = await subreducer.process(request)
            results[output_format] = result

        # All formats should succeed
        for output_format, result in results.items():
            assert result.success is True, f"{output_format} format failed"
            assert (
                result.result["generation_statistics"]["output_format"] == output_format
            )

        # Verify different output types
        assert isinstance(results["json"]["result"]["report_content"], dict)
        assert isinstance(results["html"]["result"]["report_content"], str)
        assert isinstance(results["csv"]["result"]["report_content"], str)
        assert isinstance(results["txt"]["result"]["report_content"], str)
        assert isinstance(results["markdown"]["result"]["report_content"], str)

        # Verify common content elements
        for output_format, result in results.items():
            gen_stats = result.result["generation_statistics"]
            assert gen_stats["template_type"] == "summary"
            assert gen_stats["data_points_processed"] == 2  # test_metrics and status
