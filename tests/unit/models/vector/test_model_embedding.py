# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelEmbedding."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.vector import ModelEmbedding


@pytest.mark.unit
class TestModelEmbeddingInstantiation:
    """Tests for ModelEmbedding instantiation."""

    def test_create_minimal(self):
        """Test creating embedding with minimal required fields."""
        embedding = ModelEmbedding(
            id="doc_123",
            vector=[0.1, 0.2, 0.3],
        )
        assert embedding.id == "doc_123"
        assert embedding.vector == [0.1, 0.2, 0.3]
        assert embedding.metadata == {}
        assert embedding.namespace is None

    def test_create_with_metadata(self):
        """Test creating embedding with metadata."""
        metadata = {
            "source": ModelSchemaValue.from_value("wikipedia"),
            "category": ModelSchemaValue.from_value("science"),
        }
        embedding = ModelEmbedding(
            id="doc_456",
            vector=[0.5, 0.6, 0.7],
            metadata=metadata,
        )
        assert len(embedding.metadata) == 2
        assert embedding.metadata["source"].to_value() == "wikipedia"

    def test_create_with_namespace(self):
        """Test creating embedding with namespace."""
        embedding = ModelEmbedding(
            id="doc_789",
            vector=[0.1, 0.2],
            namespace="production",
        )
        assert embedding.namespace == "production"

    def test_create_full(self):
        """Test creating embedding with all fields."""
        metadata = {"key": ModelSchemaValue.from_value("value")}
        embedding = ModelEmbedding(
            id="doc_full",
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            metadata=metadata,
            namespace="test_ns",
        )
        assert embedding.id == "doc_full"
        assert len(embedding.vector) == 5
        assert len(embedding.metadata) == 1
        assert embedding.namespace == "test_ns"


@pytest.mark.unit
class TestModelEmbeddingValidation:
    """Tests for ModelEmbedding validation."""

    def test_empty_id_raises(self):
        """Test that empty ID raises validation error."""
        with pytest.raises(ValidationError):
            ModelEmbedding(id="", vector=[0.1, 0.2])

    def test_empty_vector_raises(self):
        """Test that empty vector raises validation error."""
        with pytest.raises(ValidationError):
            ModelEmbedding(id="doc", vector=[])

    def test_missing_id_raises(self):
        """Test that missing ID raises validation error."""
        with pytest.raises(ValidationError):
            ModelEmbedding(vector=[0.1, 0.2])  # type: ignore[call-arg]

    def test_missing_vector_raises(self):
        """Test that missing vector raises validation error."""
        with pytest.raises(ValidationError):
            ModelEmbedding(id="doc")  # type: ignore[call-arg]

    def test_extra_fields_forbidden(self):
        """Test that extra fields raise validation error."""
        with pytest.raises(ValidationError):
            ModelEmbedding(
                id="doc",
                vector=[0.1, 0.2],
                extra_field="not_allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelEmbeddingImmutability:
    """Tests for ModelEmbedding immutability."""

    def test_frozen_model(self):
        """Test that the model is frozen (immutable)."""
        embedding = ModelEmbedding(id="doc", vector=[0.1, 0.2])
        with pytest.raises(ValidationError):
            embedding.id = "new_id"  # type: ignore[misc]

    def test_vector_modification_blocked(self):
        """Test that vector field cannot be reassigned."""
        embedding = ModelEmbedding(id="doc", vector=[0.1, 0.2])
        with pytest.raises(ValidationError):
            embedding.vector = [0.3, 0.4]  # type: ignore[misc]


@pytest.mark.unit
class TestModelEmbeddingSerialization:
    """Tests for ModelEmbedding serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        embedding = ModelEmbedding(
            id="doc_123",
            vector=[0.1, 0.2, 0.3],
            namespace="ns",
        )
        data = embedding.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "doc_123"
        assert data["vector"] == [0.1, 0.2, 0.3]
        assert data["namespace"] == "ns"

    def test_model_dump_json(self):
        """Test model_dump with JSON mode."""
        embedding = ModelEmbedding(id="doc", vector=[0.1, 0.2])
        json_str = embedding.model_dump_json()
        assert isinstance(json_str, str)
        assert "doc" in json_str

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "doc_from_dict",
            "vector": [0.5, 0.6],
        }
        embedding = ModelEmbedding.model_validate(data)
        assert embedding.id == "doc_from_dict"
        assert embedding.vector == [0.5, 0.6]


@pytest.mark.unit
class TestModelEmbeddingEdgeCases:
    """Tests for ModelEmbedding edge cases."""

    def test_single_element_vector(self):
        """Test embedding with single element vector."""
        embedding = ModelEmbedding(id="doc", vector=[0.5])
        assert len(embedding.vector) == 1

    def test_large_vector(self):
        """Test embedding with large vector."""
        vector = [0.1] * 1536  # OpenAI embedding dimension
        embedding = ModelEmbedding(id="doc", vector=vector)
        assert len(embedding.vector) == 1536

    def test_negative_vector_values(self):
        """Test embedding with negative values."""
        embedding = ModelEmbedding(id="doc", vector=[-0.5, 0.0, 0.5])
        assert embedding.vector == [-0.5, 0.0, 0.5]

    def test_unicode_id(self):
        """Test embedding with unicode ID."""
        embedding = ModelEmbedding(id="doc_", vector=[0.1, 0.2])
        assert embedding.id == "doc_"

    def test_whitespace_namespace(self):
        """Test embedding with whitespace in namespace."""
        embedding = ModelEmbedding(
            id="doc",
            vector=[0.1],
            namespace="my namespace",
        )
        assert embedding.namespace == "my namespace"
