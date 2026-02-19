# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelGraphHandlerMetadata."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_handler_metadata import (
    ModelGraphHandlerMetadata,
)


@pytest.mark.unit
class TestModelGraphHandlerMetadataBasics:
    """Test basic ModelGraphHandlerMetadata functionality."""

    def test_basic_initialization(self):
        """Test basic initialization with required fields."""
        metadata = ModelGraphHandlerMetadata(
            handler_type="neo4j",
            database_type="property_graph",
        )

        assert metadata.handler_type == "neo4j"
        assert metadata.database_type == "property_graph"
        assert metadata.capabilities == []
        assert metadata.supports_transactions is True

    def test_full_initialization(self):
        """Test initialization with all fields."""
        metadata = ModelGraphHandlerMetadata(
            handler_type="neo4j",
            capabilities=["cypher", "apoc", "gds"],
            database_type="property_graph",
            supports_transactions=True,
        )

        assert metadata.handler_type == "neo4j"
        assert len(metadata.capabilities) == 3
        assert "cypher" in metadata.capabilities
        assert "apoc" in metadata.capabilities
        assert metadata.database_type == "property_graph"
        assert metadata.supports_transactions is True

    def test_memgraph_handler(self):
        """Test initialization for Memgraph handler."""
        metadata = ModelGraphHandlerMetadata(
            handler_type="memgraph",
            capabilities=["cypher", "mage"],
            database_type="property_graph",
            supports_transactions=True,
        )

        assert metadata.handler_type == "memgraph"
        assert "mage" in metadata.capabilities

    def test_no_transaction_support(self):
        """Test initialization without transaction support."""
        metadata = ModelGraphHandlerMetadata(
            handler_type="simple_graph",
            database_type="memory",
            supports_transactions=False,
        )

        assert metadata.supports_transactions is False


@pytest.mark.unit
class TestModelGraphHandlerMetadataValidation:
    """Test ModelGraphHandlerMetadata validation."""

    def test_missing_required_handler_type(self):
        """Test that handler_type is required."""
        with pytest.raises(ValidationError):
            ModelGraphHandlerMetadata(database_type="property_graph")

    def test_missing_required_database_type(self):
        """Test that database_type is required."""
        with pytest.raises(ValidationError):
            ModelGraphHandlerMetadata(handler_type="neo4j")

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphHandlerMetadata(
                handler_type="neo4j",
                database_type="property_graph",
                unknown_field="value",
            )


@pytest.mark.unit
class TestModelGraphHandlerMetadataImmutability:
    """Test ModelGraphHandlerMetadata immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        metadata = ModelGraphHandlerMetadata(
            handler_type="neo4j",
            database_type="property_graph",
        )

        with pytest.raises(ValidationError):
            metadata.handler_type = "memgraph"


@pytest.mark.unit
class TestModelGraphHandlerMetadataSerialization:
    """Test ModelGraphHandlerMetadata serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        metadata = ModelGraphHandlerMetadata(
            handler_type="neo4j",
            capabilities=["cypher", "apoc"],
            database_type="property_graph",
            supports_transactions=True,
        )

        data = metadata.model_dump()

        assert data["handler_type"] == "neo4j"
        assert data["capabilities"] == ["cypher", "apoc"]
        assert data["database_type"] == "property_graph"
        assert data["supports_transactions"] is True
