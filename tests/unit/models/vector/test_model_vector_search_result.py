# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelVectorSearchResult."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.vector import ModelVectorSearchResult


@pytest.mark.unit
class TestModelVectorSearchResultInstantiation:
    """Tests for ModelVectorSearchResult instantiation."""

    def test_create_minimal(self):
        """Test creating search result with minimal required fields."""
        result = ModelVectorSearchResult(
            id="doc_123",
            score=0.95,
        )
        assert result.id == "doc_123"
        assert result.score == 0.95
        assert result.metadata == {}
        assert result.vector is None

    def test_create_with_metadata(self):
        """Test creating search result with metadata."""
        metadata = {
            "title": ModelSchemaValue.from_value("Introduction to ML"),
            "author": ModelSchemaValue.from_value("Jane Doe"),
        }
        result = ModelVectorSearchResult(
            id="doc_456",
            score=0.87,
            metadata=metadata,
        )
        assert len(result.metadata) == 2
        assert result.metadata["title"].to_value() == "Introduction to ML"

    def test_create_with_vector(self):
        """Test creating search result with vector."""
        result = ModelVectorSearchResult(
            id="doc_789",
            score=0.92,
            vector=[0.1, 0.2, 0.3],
        )
        assert result.vector == [0.1, 0.2, 0.3]

    def test_create_full(self):
        """Test creating search result with all fields."""
        metadata = {"key": ModelSchemaValue.from_value("value")}
        result = ModelVectorSearchResult(
            id="doc_full",
            score=0.99,
            metadata=metadata,
            vector=[0.5, 0.6],
        )
        assert result.id == "doc_full"
        assert result.score == 0.99
        assert len(result.metadata) == 1
        assert result.vector == [0.5, 0.6]


@pytest.mark.unit
class TestModelVectorSearchResultValidation:
    """Tests for ModelVectorSearchResult validation."""

    def test_empty_id_raises(self):
        """Test that empty ID raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorSearchResult(id="", score=0.5)

    def test_missing_id_raises(self):
        """Test that missing ID raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorSearchResult(score=0.5)  # type: ignore[call-arg]

    def test_missing_score_raises(self):
        """Test that missing score raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorSearchResult(id="doc")  # type: ignore[call-arg]

    def test_extra_fields_forbidden(self):
        """Test that extra fields raise validation error."""
        with pytest.raises(ValidationError):
            ModelVectorSearchResult(
                id="doc",
                score=0.5,
                extra_field="not_allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelVectorSearchResultImmutability:
    """Tests for ModelVectorSearchResult immutability."""

    def test_frozen_model(self):
        """Test that the model is frozen (immutable)."""
        result = ModelVectorSearchResult(id="doc", score=0.5)
        with pytest.raises(ValidationError):
            result.id = "new_id"  # type: ignore[misc]

    def test_score_modification_blocked(self):
        """Test that score field cannot be reassigned."""
        result = ModelVectorSearchResult(id="doc", score=0.5)
        with pytest.raises(ValidationError):
            result.score = 0.9  # type: ignore[misc]


@pytest.mark.unit
class TestModelVectorSearchResultSerialization:
    """Tests for ModelVectorSearchResult serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        result = ModelVectorSearchResult(
            id="doc_123",
            score=0.95,
        )
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "doc_123"
        assert data["score"] == 0.95

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "doc_from_dict",
            "score": 0.88,
        }
        result = ModelVectorSearchResult.model_validate(data)
        assert result.id == "doc_from_dict"
        assert result.score == 0.88


@pytest.mark.unit
class TestModelVectorSearchResultEdgeCases:
    """Tests for ModelVectorSearchResult edge cases."""

    def test_zero_score(self):
        """Test search result with zero score."""
        result = ModelVectorSearchResult(id="doc", score=0.0)
        assert result.score == 0.0

    def test_negative_score(self):
        """Test search result with negative score (valid for some metrics)."""
        result = ModelVectorSearchResult(id="doc", score=-0.5)
        assert result.score == -0.5

    def test_score_greater_than_one(self):
        """Test search result with score > 1 (valid for cosine distance)."""
        result = ModelVectorSearchResult(id="doc", score=1.5)
        assert result.score == 1.5

    def test_very_high_score(self):
        """Test search result with very high score (for dot product)."""
        result = ModelVectorSearchResult(id="doc", score=1000.0)
        assert result.score == 1000.0

    def test_empty_vector(self):
        """Test search result with empty vector."""
        result = ModelVectorSearchResult(id="doc", score=0.5, vector=[])
        assert result.vector == []
