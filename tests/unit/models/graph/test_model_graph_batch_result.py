"""Tests for ModelGraphBatchResult."""

from uuid import uuid4

import pytest
from omnibase_core.models.graph.model_graph_batch_result import ModelGraphBatchResult
from omnibase_core.models.graph.model_graph_query_result import ModelGraphQueryResult
from pydantic import ValidationError


@pytest.mark.unit
class TestModelGraphBatchResultBasics:
    """Test basic ModelGraphBatchResult functionality."""

    def test_default_initialization(self):
        """Test default initialization with empty values."""
        result = ModelGraphBatchResult()

        assert result.results == []
        assert result.success is False
        assert result.transaction_id is None
        assert result.rollback_occurred is False

    def test_initialization_with_results(self):
        """Test initialization with query results."""
        query_result1 = ModelGraphQueryResult(
            records=[{"id": 1}],
            execution_time_ms=5.0,
        )
        query_result2 = ModelGraphQueryResult(
            records=[{"id": 2}],
            execution_time_ms=3.0,
        )

        tx_id = uuid4()
        batch = ModelGraphBatchResult(
            results=[query_result1, query_result2],
            success=True,
            transaction_id=tx_id,
        )

        assert len(batch.results) == 2
        assert batch.success is True
        assert batch.transaction_id == tx_id
        assert batch.rollback_occurred is False

    def test_initialization_with_rollback(self):
        """Test initialization with rollback."""
        tx_id = uuid4()
        batch = ModelGraphBatchResult(
            results=[],
            success=False,
            transaction_id=tx_id,
            rollback_occurred=True,
        )

        assert batch.success is False
        assert batch.rollback_occurred is True


@pytest.mark.unit
class TestModelGraphBatchResultValidation:
    """Test ModelGraphBatchResult validation."""

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphBatchResult(unknown_field="value")


@pytest.mark.unit
class TestModelGraphBatchResultImmutability:
    """Test ModelGraphBatchResult immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        batch = ModelGraphBatchResult(success=True)

        with pytest.raises(ValidationError):
            batch.success = False


@pytest.mark.unit
class TestModelGraphBatchResultSerialization:
    """Test ModelGraphBatchResult serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        query_result = ModelGraphQueryResult(
            records=[{"x": 1}],
            execution_time_ms=5.0,
        )

        tx_id = uuid4()
        batch = ModelGraphBatchResult(
            results=[query_result],
            success=True,
            transaction_id=tx_id,
        )

        data = batch.model_dump()

        assert len(data["results"]) == 1
        assert data["success"] is True
        assert data["transaction_id"] == tx_id
        assert data["rollback_occurred"] is False
