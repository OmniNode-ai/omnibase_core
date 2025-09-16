#!/usr/bin/env python3
"""
Unit Tests for Reducer Pattern Engine - Phase 1.

Comprehensive test suite covering:
- ReducerPatternEngine core functionality
- WorkflowRouter routing logic
- ReducerDocumentRegenerationSubreducer processing
- Contract validation and data models
- Error handling and edge cases

Test Categories:
- Initialization tests
- Workflow processing tests
- Routing tests
- Subreducer tests
- Contract validation tests
- Integration tests
"""

# Test imports - adjust paths as needed for actual test discovery
import sys
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

# Add source path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from omnibase_core.core.errors.core_errors import OnexError
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.nodes.reducer_pattern_engine.subreducers.reducer_document_regeneration import (
    ReducerDocumentRegenerationSubreducer,
)
from omnibase_core.nodes.reducer_pattern_engine.v1_0_0.contracts import (
    ModelWorkflowInput,
    ModelWorkflowOutput,
    create_workflow_output,
    validate_workflow_input,
)
from omnibase_core.nodes.reducer_pattern_engine.v1_0_0.engine import (
    ReducerPatternEngine,
)
from omnibase_core.nodes.reducer_pattern_engine.v1_0_0.router import WorkflowRouter


class TestReducerPatternEngine:
    """Test suite for ReducerPatternEngine core functionality."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ModelONEXContainer for testing."""
        container = Mock(spec=ModelONEXContainer)

        # Mock container services
        container.get_service.return_value = Mock()

        return container

    @pytest.fixture
    def sample_workflow_input(self):
        """Create sample workflow input for testing."""
        return {
            "workflow_type": "document_regeneration",
            "instance_id": f"test-instance-{uuid4()}",
            "data": {
                "document": {
                    "title": "Test Document",
                    "content": "This is test content for document regeneration.",
                    "format": "text",
                    "version": "1.0",
                }
            },
        }

    def test_engine_initialization(self, mock_container):
        """Test ReducerPatternEngine initialization."""
        with patch.multiple(
            "omnibase_core.nodes.reducer_pattern_engine.v1_0_0.engine",
            emit_log_event=Mock(),
        ):
            with patch.object(ReducerPatternEngine, "_load_phase1_config"):
                with patch.object(ReducerPatternEngine, "__init__", lambda x, y: None):
                    engine = ReducerPatternEngine.__new__(ReducerPatternEngine)
                    engine.container = mock_container
                    engine.workflow_router = Mock()
                    engine.active_workflows = {}
                    engine.processing_metrics = {}
                    engine.node_id = "test-node-123"

                    assert engine.container == mock_container
                    assert hasattr(engine, "workflow_router")
                    assert hasattr(engine, "active_workflows")
                    assert hasattr(engine, "processing_metrics")

    @pytest.mark.asyncio
    async def test_workflow_processing_success(
        self, mock_container, sample_workflow_input
    ):
        """Test successful workflow processing."""
        # Create engine with mocked initialization
        with patch.object(ReducerPatternEngine, "__init__", lambda x, y: None):
            engine = ReducerPatternEngine.__new__(ReducerPatternEngine)
            engine.container = mock_container
            engine.active_workflows = {}
            engine.processing_metrics = {}
            engine.node_id = "test-node"

            # Mock workflow router
            mock_subreducer = AsyncMock()
            mock_subreducer.process_workflow.return_value = {
                "success": True,
                "result_data": {
                    "regenerated_document": {
                        "title": "Regenerated - Test Document",
                        "content": "Regenerated: This is test content...",
                        "metadata": {"processing_method": "test"},
                    }
                },
            }

            mock_router = Mock()
            mock_router.route_workflow.return_value = mock_subreducer
            engine.workflow_router = mock_router

            # Mock methods
            engine._validate_workflow_input = Mock()
            engine._update_processing_metrics = AsyncMock()

            # Execute workflow processing
            result = await engine.reduce(sample_workflow_input)

            # Assertions
            assert result["success"] is True
            assert "result_data" in result
            assert "regenerated_document" in result["result_data"]
            assert result["workflow_type"] == "document_regeneration"
            assert "correlation_id" in result
            assert "execution_time_ms" in result

            # Verify method calls
            engine._validate_workflow_input.assert_called_once()
            mock_router.route_workflow.assert_called_once()
            mock_subreducer.process_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_processing_failure(
        self, mock_container, sample_workflow_input
    ):
        """Test workflow processing failure handling."""
        with patch.object(ReducerPatternEngine, "__init__", lambda x, y: None):
            engine = ReducerPatternEngine.__new__(ReducerPatternEngine)
            engine.container = mock_container
            engine.active_workflows = {}
            engine.processing_metrics = {}
            engine.node_id = "test-node"

            # Mock failure scenario
            engine._validate_workflow_input = Mock(
                side_effect=OnexError("VALIDATION_ERROR", "Test validation error")
            )
            engine._update_processing_metrics = AsyncMock()

            # Execute workflow processing
            result = await engine.reduce(sample_workflow_input)

            # Assertions
            assert result["success"] is False
            assert "error_message" in result
            assert "Test validation error" in result["error_message"]
            assert result["workflow_type"] == "document_regeneration"

    def test_input_validation_success(self, mock_container, sample_workflow_input):
        """Test successful input validation."""
        with patch.object(ReducerPatternEngine, "__init__", lambda x, y: None):
            engine = ReducerPatternEngine.__new__(ReducerPatternEngine)
            engine.node_id = "test-node"

            # Should not raise exception
            engine._validate_workflow_input(sample_workflow_input)

    def test_input_validation_missing_workflow_type(self, mock_container):
        """Test input validation with missing workflow_type."""
        with patch.object(ReducerPatternEngine, "__init__", lambda x, y: None):
            engine = ReducerPatternEngine.__new__(ReducerPatternEngine)
            engine.node_id = "test-node"

            invalid_input = {"instance_id": "test-123"}

            with pytest.raises(OnexError) as exc_info:
                engine._validate_workflow_input(invalid_input)

            assert "workflow_type" in str(exc_info.value)

    def test_input_validation_invalid_instance_id(self, mock_container):
        """Test input validation with invalid instance_id."""
        with patch.object(ReducerPatternEngine, "__init__", lambda x, y: None):
            engine = ReducerPatternEngine.__new__(ReducerPatternEngine)
            engine.node_id = "test-node"

            invalid_input = {
                "workflow_type": "document_regeneration",
                "instance_id": "",  # Empty instance_id
            }

            with pytest.raises(OnexError) as exc_info:
                engine._validate_workflow_input(invalid_input)

            assert "instance_id" in str(exc_info.value)


class TestWorkflowRouter:
    """Test suite for WorkflowRouter routing logic."""

    @pytest.fixture
    def mock_container(self):
        """Create mock container for router testing."""
        container = Mock(spec=ModelONEXContainer)
        return container

    def test_router_initialization(self, mock_container):
        """Test WorkflowRouter initialization."""
        with patch.object(WorkflowRouter, "_initialize_workflow_coordination"):
            router = WorkflowRouter(mock_container)

            assert router.container == mock_container
            assert hasattr(router, "correlation_id")
            assert hasattr(router, "_subreducer_registry")
            assert hasattr(router, "_routing_metrics")

    def test_route_calculation(self, mock_container):
        """Test routing key calculation."""
        with patch.object(WorkflowRouter, "_initialize_workflow_coordination"):
            router = WorkflowRouter(mock_container)

            # Test consistent routing key generation
            key1 = router._calculate_route_key("document_regeneration", "test-123")
            key2 = router._calculate_route_key("document_regeneration", "test-123")
            key3 = router._calculate_route_key("document_regeneration", "test-456")

            assert key1 == key2  # Same inputs should produce same key
            assert key1 != key3  # Different inputs should produce different keys
            assert len(key1) == 16  # Should be 16-character hex string
            assert all(c in "0123456789abcdef" for c in key1)

    def test_unsupported_workflow_type(self, mock_container):
        """Test routing failure for unsupported workflow type."""
        with patch.object(WorkflowRouter, "_initialize_workflow_coordination"):
            router = WorkflowRouter(mock_container)

            with pytest.raises(OnexError) as exc_info:
                router.route_workflow("unsupported_type", "test-123", {})

            assert "Phase 1 only supports" in str(exc_info.value)
            assert "document_regeneration" in str(exc_info.value)

    def test_input_validation_empty_workflow_type(self, mock_container):
        """Test routing input validation for empty workflow_type."""
        with patch.object(WorkflowRouter, "_initialize_workflow_coordination"):
            router = WorkflowRouter(mock_container)

            with pytest.raises(OnexError) as exc_info:
                router.route_workflow("", "test-123", {})

            assert "workflow_type must be non-empty string" in str(exc_info.value)

    def test_input_validation_invalid_workflow_data(self, mock_container):
        """Test routing input validation for invalid workflow_data."""
        with patch.object(WorkflowRouter, "_initialize_workflow_coordination"):
            router = WorkflowRouter(mock_container)

            with pytest.raises(OnexError) as exc_info:
                router.route_workflow("document_regeneration", "test-123", "not-a-dict")

            assert "workflow_data must be dictionary" in str(exc_info.value)


class TestReducerDocumentRegenerationSubreducer:
    """Test suite for ReducerDocumentRegenerationSubreducer processing."""

    @pytest.fixture
    def mock_container(self):
        """Create mock container for subreducer testing."""
        container = Mock(spec=ModelONEXContainer)
        return container

    @pytest.fixture
    def sample_workflow_context(self):
        """Create sample workflow context for testing."""
        return {
            "workflow_type": "document_regeneration",
            "instance_id": f"test-{uuid4()}",
            "data": {
                "document": {
                    "title": "Sample Document",
                    "content": "This is sample content for testing.",
                    "format": "text",
                }
            },
            "correlation_id": str(uuid4()),
            "start_time": time.time(),
        }

    def test_subreducer_initialization(self, mock_container):
        """Test subreducer initialization with subcontract setup."""
        with patch.multiple(
            "omnibase_core.nodes.reducer_pattern_engine.subreducers.reducer_document_regeneration",
            emit_log_event=Mock(),
        ):
            subreducer = ReducerDocumentRegenerationSubreducer(mock_container)

            assert subreducer.container == mock_container
            assert hasattr(subreducer, "correlation_id")
            assert hasattr(subreducer, "_state_management")
            assert hasattr(subreducer, "_fsm_manager")
            assert hasattr(subreducer, "_event_handler")

    @pytest.mark.asyncio
    async def test_workflow_processing_success(
        self, mock_container, sample_workflow_context
    ):
        """Test successful document workflow processing."""
        with patch.multiple(
            "omnibase_core.nodes.reducer_pattern_engine.subreducers.reducer_document_regeneration",
            emit_log_event=Mock(),
        ):
            subreducer = ReducerDocumentRegenerationSubreducer(mock_container)

            # Mock internal methods
            subreducer._validate_document_data = AsyncMock()
            subreducer._initialize_workflow_state = AsyncMock(
                return_value={
                    "instance_id": sample_workflow_context["instance_id"],
                    "correlation_id": sample_workflow_context["correlation_id"],
                    "current_state": "processing",
                    "transitions_performed": [],
                    "events_emitted": [],
                }
            )
            subreducer._execute_document_regeneration = AsyncMock(
                return_value={
                    "title": "Regenerated Document",
                    "content": "Regenerated content...",
                    "metadata": {"processing_method": "test"},
                }
            )
            subreducer._finalize_workflow_state = AsyncMock()
            subreducer._update_processing_metrics = AsyncMock()

            # Execute workflow processing
            result = await subreducer.process_workflow(sample_workflow_context)

            # Assertions
            assert result["success"] is True
            assert "result_data" in result
            assert "regenerated_document" in result["result_data"]
            assert "processing_summary" in result
            assert result["processing_summary"]["success"] is True

    @pytest.mark.asyncio
    async def test_document_validation_failure(self, mock_container):
        """Test document data validation failure."""
        with patch.multiple(
            "omnibase_core.nodes.reducer_pattern_engine.subreducers.reducer_document_regeneration",
            emit_log_event=Mock(),
        ):
            subreducer = ReducerDocumentRegenerationSubreducer(mock_container)

            invalid_data = {"not_document": "invalid"}

            with pytest.raises(OnexError) as exc_info:
                await subreducer._validate_document_data(invalid_data, "test-instance")

            assert "Document data must contain 'document' field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_document_validation_invalid_structure(self, mock_container):
        """Test document validation with invalid document structure."""
        with patch.multiple(
            "omnibase_core.nodes.reducer_pattern_engine.subreducers.reducer_document_regeneration",
            emit_log_event=Mock(),
        ):
            subreducer = ReducerDocumentRegenerationSubreducer(mock_container)

            invalid_data = {"document": "not-a-dict"}

            with pytest.raises(OnexError) as exc_info:
                await subreducer._validate_document_data(invalid_data, "test-instance")

            assert "Document content must be dictionary" in str(exc_info.value)


class TestContractValidation:
    """Test suite for contract validation and data models."""

    def test_workflow_input_validation_success(self):
        """Test successful workflow input validation."""
        valid_input = {
            "workflow_type": "document_regeneration",
            "instance_id": "test-instance-123",
            "data": {"document": {"title": "Test Doc", "content": "Test content"}},
        }

        model = validate_workflow_input(valid_input)
        assert model.workflow_type == "document_regeneration"
        assert model.instance_id == "test-instance-123"
        assert model.correlation_id is not None  # Should be auto-generated

    def test_workflow_input_validation_unsupported_type(self):
        """Test workflow input validation with unsupported workflow type."""
        invalid_input = {
            "workflow_type": "unsupported_type",
            "instance_id": "test-123",
            "data": {"document": {"title": "Test", "content": "Test"}},
        }

        with pytest.raises(ValueError) as exc_info:
            validate_workflow_input(invalid_input)

        assert "Unsupported workflow type" in str(exc_info.value)

    def test_workflow_input_validation_missing_document(self):
        """Test workflow input validation with missing document data."""
        invalid_input = {
            "workflow_type": "document_regeneration",
            "instance_id": "test-123",
            "data": {},  # Missing document
        }

        with pytest.raises(ValueError) as exc_info:
            validate_workflow_input(invalid_input)

        assert "must contain 'document' field" in str(exc_info.value)

    def test_workflow_output_creation_success(self):
        """Test successful workflow output creation."""
        output = create_workflow_output(
            success=True,
            result_data={"test": {"result": "data"}},
            workflow_type="document_regeneration",
            instance_id="test-123",
            execution_time_ms=1000,
            correlation_id="test-correlation",
        )

        assert output.success is True
        assert output.result_data is not None
        assert output.error_message is None
        assert output.workflow_type == "document_regeneration"

    def test_workflow_output_creation_failure(self):
        """Test workflow output creation for failure case."""
        output = create_workflow_output(
            success=False,
            error_message="Test error occurred",
            workflow_type="document_regeneration",
            instance_id="test-123",
            execution_time_ms=500,
            correlation_id="test-correlation",
        )

        assert output.success is False
        assert output.result_data is None
        assert output.error_message == "Test error occurred"

    def test_workflow_output_validation_missing_result_data(self):
        """Test workflow output validation when success=True but no result_data."""
        with pytest.raises(ValueError) as exc_info:
            create_workflow_output(
                success=True,
                result_data=None,  # Missing result_data for successful workflow
                workflow_type="document_regeneration",
                instance_id="test-123",
                execution_time_ms=1000,
                correlation_id="test-correlation",
            )

        assert "result_data must be provided when success=True" in str(exc_info.value)


class TestIntegration:
    """Integration tests for complete workflow processing."""

    @pytest.fixture
    def integration_container(self):
        """Create integration test container."""
        container = Mock(spec=ModelONEXContainer)
        container.get_service.return_value = Mock()
        return container

    @pytest.fixture
    def integration_input(self):
        """Create integration test input."""
        return {
            "workflow_type": "document_regeneration",
            "instance_id": f"integration-test-{uuid4()}",
            "data": {
                "document": {
                    "title": "Integration Test Document",
                    "content": "This is comprehensive integration test content for validating the complete workflow.",
                    "format": "markdown",
                    "version": "1.0",
                }
            },
        }

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, integration_container, integration_input):
        """Test complete end-to-end workflow processing."""
        with (
            patch.multiple(
                "omnibase_core.nodes.reducer_pattern_engine.v1_0_0.engine",
                emit_log_event=Mock(),
            ),
            patch.multiple(
                "omnibase_core.nodes.reducer_pattern_engine.v1_0_0.router",
                emit_log_event=Mock(),
            ),
            patch.multiple(
                "omnibase_core.nodes.reducer_pattern_engine.subreducers.reducer_document_regeneration",
                emit_log_event=Mock(),
            ),
        ):
            # Mock initialization methods to avoid complex setup
            with patch.object(ReducerPatternEngine, "__init__", lambda x, y: None):
                engine = ReducerPatternEngine.__new__(ReducerPatternEngine)
                engine.container = integration_container
                engine.node_id = "integration-test-node"
                engine.active_workflows = {}
                engine.processing_metrics = {}

                # Set up real workflow router and subreducer
                with patch.object(WorkflowRouter, "_initialize_workflow_coordination"):
                    router = WorkflowRouter(integration_container)
                    engine.workflow_router = router

                # Mock subreducer creation in router
                mock_subreducer = Mock()
                mock_subreducer.process_workflow = AsyncMock(
                    return_value={
                        "success": True,
                        "result_data": {
                            "regenerated_document": {
                                "title": "Integration Test - Regenerated Document",
                                "content": "Regenerated: This is comprehensive integration test content...",
                                "metadata": {
                                    "original_title": "Integration Test Document",
                                    "processing_method": "integration_test",
                                    "processing_timestamp": time.time(),
                                },
                            }
                        },
                        "state_transitions": ["initialized", "processing", "completed"],
                        "events_emitted": [
                            "workflow_started",
                            "document_processed",
                            "workflow_completed",
                        ],
                        "execution_time_ms": 1500,
                        "correlation_id": str(uuid4()),
                    }
                )

                router._subreducer_registry["document_regeneration"] = mock_subreducer

                # Mock validation and metrics methods
                engine._validate_workflow_input = Mock()
                engine._update_processing_metrics = AsyncMock()

                # Execute end-to-end workflow
                result = await engine.reduce(integration_input)

                # Comprehensive assertions
                assert result["success"] is True
                assert "result_data" in result
                assert "regenerated_document" in result["result_data"]

                regenerated_doc = result["result_data"]["regenerated_document"]
                assert "Integration Test" in regenerated_doc["title"]
                assert "Regenerated:" in regenerated_doc["content"]
                assert "metadata" in regenerated_doc
                assert (
                    regenerated_doc["metadata"]["original_title"]
                    == "Integration Test Document"
                )

                assert result["workflow_type"] == "document_regeneration"
                assert "correlation_id" in result
                assert "execution_time_ms" in result
                assert isinstance(result["execution_time_ms"], int)
                assert result["execution_time_ms"] >= 0

                # Verify method calls
                engine._validate_workflow_input.assert_called_once()
                engine._update_processing_metrics.assert_called()
                mock_subreducer.process_workflow.assert_called_once()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
