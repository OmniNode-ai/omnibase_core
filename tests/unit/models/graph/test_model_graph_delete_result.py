"""Tests for ModelGraphDeleteResult."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_delete_result import ModelGraphDeleteResult


@pytest.mark.unit
class TestModelGraphDeleteResultBasics:
    """Test basic ModelGraphDeleteResult functionality."""

    def test_default_initialization(self):
        """Test default initialization with default values."""
        result = ModelGraphDeleteResult()

        assert result.success is False
        assert result.node_id is None
        assert result.relationships_deleted == 0
        assert result.execution_time_ms == 0.0

    def test_initialization_with_success(self):
        """Test initialization for successful deletion."""
        result = ModelGraphDeleteResult(
            success=True,
            node_id="4:abc:123",
            relationships_deleted=5,
            execution_time_ms=12.5,
        )

        assert result.success is True
        assert result.node_id == "4:abc:123"
        assert result.relationships_deleted == 5
        assert result.execution_time_ms == 12.5

    def test_relationship_only_deletion(self):
        """Test deletion result for relationship-only deletion."""
        result = ModelGraphDeleteResult(
            success=True,
            node_id=None,
            relationships_deleted=3,
            execution_time_ms=5.0,
        )

        assert result.success is True
        assert result.node_id is None
        assert result.relationships_deleted == 3


@pytest.mark.unit
class TestModelGraphDeleteResultValidation:
    """Test ModelGraphDeleteResult validation."""

    def test_negative_relationships_deleted_invalid(self):
        """Test that negative relationships_deleted is invalid."""
        with pytest.raises(ValidationError):
            ModelGraphDeleteResult(relationships_deleted=-1)

    def test_negative_execution_time_invalid(self):
        """Test that negative execution time is invalid."""
        with pytest.raises(ValidationError):
            ModelGraphDeleteResult(execution_time_ms=-1.0)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphDeleteResult(unknown_field="value")


@pytest.mark.unit
class TestModelGraphDeleteResultImmutability:
    """Test ModelGraphDeleteResult immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        result = ModelGraphDeleteResult(success=True)

        with pytest.raises(ValidationError):
            result.success = False


@pytest.mark.unit
class TestModelGraphDeleteResultSerialization:
    """Test ModelGraphDeleteResult serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        result = ModelGraphDeleteResult(
            success=True,
            node_id="4:abc:123",
            relationships_deleted=2,
            execution_time_ms=8.0,
        )

        data = result.model_dump()

        assert data["success"] is True
        assert data["node_id"] == "4:abc:123"
        assert data["relationships_deleted"] == 2
        assert data["execution_time_ms"] == 8.0
