# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelGraphTraversalResult."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_database_node import ModelGraphDatabaseNode
from omnibase_core.models.graph.model_graph_relationship import ModelGraphRelationship
from omnibase_core.models.graph.model_graph_traversal_result import (
    ModelGraphTraversalResult,
)


@pytest.mark.unit
class TestModelGraphTraversalResultBasics:
    """Test basic ModelGraphTraversalResult functionality."""

    def test_default_initialization(self):
        """Test default initialization with empty values."""
        result = ModelGraphTraversalResult()

        assert result.nodes == []
        assert result.relationships == []
        assert result.paths == []
        assert result.depth_reached == 0
        assert result.execution_time_ms == 0.0

    def test_initialization_with_nodes(self):
        """Test initialization with nodes."""
        node1 = ModelGraphDatabaseNode(id="1", element_id="4:abc:1", labels=["Person"])
        node2 = ModelGraphDatabaseNode(id="2", element_id="4:abc:2", labels=["Person"])

        result = ModelGraphTraversalResult(
            nodes=[node1, node2],
            depth_reached=2,
            execution_time_ms=15.5,
        )

        assert len(result.nodes) == 2
        assert result.depth_reached == 2
        assert result.execution_time_ms == 15.5

    def test_initialization_with_relationships(self):
        """Test initialization with relationships."""
        rel = ModelGraphRelationship(
            id="rel-1",
            element_id="5:abc:1",
            type="KNOWS",
            start_node_id="4:abc:1",
            end_node_id="4:abc:2",
        )

        result = ModelGraphTraversalResult(
            relationships=[rel],
        )

        assert len(result.relationships) == 1
        assert result.relationships[0].type == "KNOWS"

    def test_initialization_with_paths(self):
        """Test initialization with paths."""
        result = ModelGraphTraversalResult(
            paths=[
                ["4:abc:1", "5:rel:1", "4:abc:2"],
                ["4:abc:1", "5:rel:2", "4:abc:3"],
            ],
        )

        assert len(result.paths) == 2
        assert len(result.paths[0]) == 3


@pytest.mark.unit
class TestModelGraphTraversalResultValidation:
    """Test ModelGraphTraversalResult validation."""

    def test_negative_depth_invalid(self):
        """Test that negative depth is invalid."""
        with pytest.raises(ValidationError):
            ModelGraphTraversalResult(depth_reached=-1)

    def test_negative_execution_time_invalid(self):
        """Test that negative execution time is invalid."""
        with pytest.raises(ValidationError):
            ModelGraphTraversalResult(execution_time_ms=-1.0)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphTraversalResult(unknown_field="value")


@pytest.mark.unit
class TestModelGraphTraversalResultImmutability:
    """Test ModelGraphTraversalResult immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        result = ModelGraphTraversalResult(depth_reached=5)

        with pytest.raises(ValidationError):
            result.depth_reached = 10


@pytest.mark.unit
class TestModelGraphTraversalResultSerialization:
    """Test ModelGraphTraversalResult serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        node = ModelGraphDatabaseNode(id="1", element_id="4:abc:1", labels=["Person"])

        result = ModelGraphTraversalResult(
            nodes=[node],
            depth_reached=3,
            execution_time_ms=25.0,
        )

        data = result.model_dump()

        assert len(data["nodes"]) == 1
        assert data["depth_reached"] == 3
        assert data["execution_time_ms"] == 25.0
