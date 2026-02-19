# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelGraphDatabaseNode."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_database_node import ModelGraphDatabaseNode


@pytest.mark.unit
class TestModelGraphDatabaseNodeBasics:
    """Test basic ModelGraphDatabaseNode functionality."""

    def test_basic_initialization(self):
        """Test basic node initialization with required fields."""
        node = ModelGraphDatabaseNode(
            id="123",
            element_id="4:abc:123",
        )

        assert node.id == "123"
        assert node.element_id == "4:abc:123"
        assert node.labels == []
        assert node.properties == {}

    def test_initialization_with_labels(self):
        """Test initialization with labels."""
        node = ModelGraphDatabaseNode(
            id="123",
            element_id="4:abc:123",
            labels=["Person", "Employee"],
        )

        assert len(node.labels) == 2
        assert "Person" in node.labels
        assert "Employee" in node.labels

    def test_initialization_with_properties(self):
        """Test initialization with properties."""
        node = ModelGraphDatabaseNode(
            id="123",
            element_id="4:abc:123",
            properties={"name": "John", "age": 30},
        )

        assert node.properties["name"] == "John"
        assert node.properties["age"] == 30

    def test_full_initialization(self):
        """Test full initialization with all fields."""
        node = ModelGraphDatabaseNode(
            id="node-456",
            element_id="4:db:456",
            labels=["Document", "Indexed"],
            properties={"title": "Test Doc", "created": "2024-01-01"},
        )

        assert node.id == "node-456"
        assert node.element_id == "4:db:456"
        assert node.labels == ["Document", "Indexed"]
        assert node.properties["title"] == "Test Doc"


@pytest.mark.unit
class TestModelGraphDatabaseNodeValidation:
    """Test ModelGraphDatabaseNode validation."""

    def test_missing_required_id(self):
        """Test that id is required."""
        with pytest.raises(ValidationError):
            ModelGraphDatabaseNode(element_id="4:abc:123")

    def test_missing_required_element_id(self):
        """Test that element_id is required."""
        with pytest.raises(ValidationError):
            ModelGraphDatabaseNode(id="123")

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphDatabaseNode(
                id="123",
                element_id="4:abc:123",
                unknown_field="value",
            )


@pytest.mark.unit
class TestModelGraphDatabaseNodeImmutability:
    """Test ModelGraphDatabaseNode immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        node = ModelGraphDatabaseNode(
            id="123",
            element_id="4:abc:123",
            labels=["Person"],
        )

        with pytest.raises(ValidationError):
            node.id = "456"

    def test_model_copy(self):
        """Test that model can be copied with updates."""
        node = ModelGraphDatabaseNode(
            id="123",
            element_id="4:abc:123",
            labels=["Person"],
        )

        new_node = node.model_copy(update={"labels": ["Employee"]})

        assert node.labels == ["Person"]
        assert new_node.labels == ["Employee"]


@pytest.mark.unit
class TestModelGraphDatabaseNodeSerialization:
    """Test ModelGraphDatabaseNode serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        node = ModelGraphDatabaseNode(
            id="123",
            element_id="4:abc:123",
            labels=["Person"],
            properties={"name": "John"},
        )

        data = node.model_dump()

        assert data["id"] == "123"
        assert data["element_id"] == "4:abc:123"
        assert data["labels"] == ["Person"]
        assert data["properties"] == {"name": "John"}

    def test_model_json(self):
        """Test model serialization to JSON."""
        node = ModelGraphDatabaseNode(
            id="123",
            element_id="4:abc:123",
            labels=["Person"],
        )

        json_str = node.model_dump_json()

        assert '"id":"123"' in json_str
        assert '"element_id":"4:abc:123"' in json_str

    def test_from_dict(self):
        """Test model construction from dict."""
        data = {
            "id": "123",
            "element_id": "4:abc:123",
            "labels": ["Person"],
            "properties": {"name": "John"},
        }

        node = ModelGraphDatabaseNode.model_validate(data)

        assert node.id == "123"
        assert node.labels == ["Person"]
