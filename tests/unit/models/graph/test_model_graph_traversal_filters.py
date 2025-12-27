"""Tests for ModelGraphTraversalFilters."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_traversal_filters import (
    ModelGraphTraversalFilters,
)


@pytest.mark.unit
class TestModelGraphTraversalFiltersBasics:
    """Test basic ModelGraphTraversalFilters functionality."""

    def test_default_initialization(self):
        """Test default initialization with empty values."""
        filters = ModelGraphTraversalFilters()

        assert filters.node_labels == []
        assert filters.node_properties == {}
        assert filters.relationship_types == []
        assert filters.relationship_properties == {}

    def test_initialization_with_node_labels(self):
        """Test initialization with node labels."""
        filters = ModelGraphTraversalFilters(
            node_labels=["Person", "Employee"],
        )

        assert len(filters.node_labels) == 2
        assert "Person" in filters.node_labels
        assert "Employee" in filters.node_labels

    def test_initialization_with_node_properties(self):
        """Test initialization with node properties."""
        filters = ModelGraphTraversalFilters(
            node_properties={"status": "active", "verified": True},
        )

        assert filters.node_properties["status"] == "active"
        assert filters.node_properties["verified"] is True

    def test_initialization_with_relationship_filters(self):
        """Test initialization with relationship filters."""
        filters = ModelGraphTraversalFilters(
            relationship_types=["KNOWS", "WORKS_WITH"],
            relationship_properties={"weight": 0.5},
        )

        assert len(filters.relationship_types) == 2
        assert "KNOWS" in filters.relationship_types
        assert filters.relationship_properties["weight"] == 0.5

    def test_full_initialization(self):
        """Test initialization with all fields."""
        filters = ModelGraphTraversalFilters(
            node_labels=["Person"],
            node_properties={"age": 30},
            relationship_types=["KNOWS"],
            relationship_properties={"since": "2020"},
        )

        assert filters.node_labels == ["Person"]
        assert filters.node_properties == {"age": 30}
        assert filters.relationship_types == ["KNOWS"]
        assert filters.relationship_properties == {"since": "2020"}


@pytest.mark.unit
class TestModelGraphTraversalFiltersValidation:
    """Test ModelGraphTraversalFilters validation."""

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphTraversalFilters(unknown_field="value")


@pytest.mark.unit
class TestModelGraphTraversalFiltersImmutability:
    """Test ModelGraphTraversalFilters immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        filters = ModelGraphTraversalFilters(
            node_labels=["Person"],
        )

        with pytest.raises(ValidationError):
            filters.node_labels = ["Employee"]


@pytest.mark.unit
class TestModelGraphTraversalFiltersSerialization:
    """Test ModelGraphTraversalFilters serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        filters = ModelGraphTraversalFilters(
            node_labels=["Person"],
            node_properties={"name": "John"},
            relationship_types=["KNOWS"],
            relationship_properties={"weight": 1.0},
        )

        data = filters.model_dump()

        assert data["node_labels"] == ["Person"]
        assert data["node_properties"] == {"name": "John"}
        assert data["relationship_types"] == ["KNOWS"]
        assert data["relationship_properties"] == {"weight": 1.0}
