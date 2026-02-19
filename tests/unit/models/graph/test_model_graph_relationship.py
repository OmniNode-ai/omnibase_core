# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelGraphRelationship."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_relationship import ModelGraphRelationship


@pytest.mark.unit
class TestModelGraphRelationshipBasics:
    """Test basic ModelGraphRelationship functionality."""

    def test_basic_initialization(self):
        """Test basic relationship initialization with required fields."""
        rel = ModelGraphRelationship(
            id="rel-123",
            element_id="5:abc:123",
            type="KNOWS",
            start_node_id="4:abc:1",
            end_node_id="4:abc:2",
        )

        assert rel.id == "rel-123"
        assert rel.element_id == "5:abc:123"
        assert rel.type == "KNOWS"
        assert rel.start_node_id == "4:abc:1"
        assert rel.end_node_id == "4:abc:2"
        assert rel.properties == {}

    def test_initialization_with_properties(self):
        """Test initialization with properties."""
        rel = ModelGraphRelationship(
            id="rel-123",
            element_id="5:abc:123",
            type="WORKS_FOR",
            start_node_id="4:abc:1",
            end_node_id="4:abc:2",
            properties={"since": "2020-01-01", "role": "Engineer"},
        )

        assert rel.properties["since"] == "2020-01-01"
        assert rel.properties["role"] == "Engineer"


@pytest.mark.unit
class TestModelGraphRelationshipValidation:
    """Test ModelGraphRelationship validation."""

    def test_missing_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            ModelGraphRelationship(id="rel-123", element_id="5:abc:123")

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphRelationship(
                id="rel-123",
                element_id="5:abc:123",
                type="KNOWS",
                start_node_id="4:abc:1",
                end_node_id="4:abc:2",
                unknown_field="value",
            )


@pytest.mark.unit
class TestModelGraphRelationshipImmutability:
    """Test ModelGraphRelationship immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        rel = ModelGraphRelationship(
            id="rel-123",
            element_id="5:abc:123",
            type="KNOWS",
            start_node_id="4:abc:1",
            end_node_id="4:abc:2",
        )

        with pytest.raises(ValidationError):
            rel.type = "FRIENDS"


@pytest.mark.unit
class TestModelGraphRelationshipSerialization:
    """Test ModelGraphRelationship serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        rel = ModelGraphRelationship(
            id="rel-123",
            element_id="5:abc:123",
            type="KNOWS",
            start_node_id="4:abc:1",
            end_node_id="4:abc:2",
            properties={"weight": 0.5},
        )

        data = rel.model_dump()

        assert data["type"] == "KNOWS"
        assert data["start_node_id"] == "4:abc:1"
        assert data["end_node_id"] == "4:abc:2"
        assert data["properties"] == {"weight": 0.5}
