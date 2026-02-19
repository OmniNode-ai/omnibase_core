# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for vector result models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.vector import (
    EnumVectorDistanceMetric,
    ModelVectorBatchStoreResult,
    ModelVectorDeleteResult,
    ModelVectorIndexResult,
    ModelVectorSearchResult,
    ModelVectorSearchResults,
    ModelVectorStoreResult,
)


@pytest.mark.unit
class TestModelVectorStoreResult:
    """Tests for ModelVectorStoreResult."""

    def test_create_success(self):
        """Test creating successful store result."""
        result = ModelVectorStoreResult(
            success=True,
            embedding_id="doc_123",
            index_name="documents",
            timestamp=datetime.now(UTC),
        )
        assert result.success is True
        assert result.embedding_id == "doc_123"
        assert result.index_name == "documents"
        assert result.timestamp is not None

    def test_create_failure(self):
        """Test creating failed store result."""
        result = ModelVectorStoreResult(
            success=False,
            embedding_id="doc_456",
            index_name="documents",
        )
        assert result.success is False
        assert result.timestamp is None

    def test_validation_empty_embedding_id(self):
        """Test that empty embedding_id raises error."""
        with pytest.raises(ValidationError):
            ModelVectorStoreResult(
                success=True,
                embedding_id="",
                index_name="documents",
            )

    def test_validation_empty_index_name(self):
        """Test that empty index_name raises error."""
        with pytest.raises(ValidationError):
            ModelVectorStoreResult(
                success=True,
                embedding_id="doc_123",
                index_name="",
            )

    def test_frozen(self):
        """Test that model is frozen."""
        result = ModelVectorStoreResult(
            success=True,
            embedding_id="doc",
            index_name="idx",
        )
        with pytest.raises(ValidationError):
            result.success = False  # type: ignore[misc]


@pytest.mark.unit
class TestModelVectorBatchStoreResult:
    """Tests for ModelVectorBatchStoreResult."""

    def test_create_full_success(self):
        """Test creating fully successful batch result."""
        result = ModelVectorBatchStoreResult(
            success=True,
            total_stored=100,
            failed_ids=[],
            execution_time_ms=250,
        )
        assert result.success is True
        assert result.total_stored == 100
        assert result.failed_ids == []
        assert result.execution_time_ms == 250

    def test_create_partial_failure(self):
        """Test creating partial failure batch result."""
        result = ModelVectorBatchStoreResult(
            success=False,
            total_stored=95,
            failed_ids=["doc_5", "doc_23", "doc_67", "doc_89", "doc_100"],
            execution_time_ms=500,
        )
        assert result.success is False
        assert result.total_stored == 95
        assert len(result.failed_ids) == 5

    def test_validation_negative_stored(self):
        """Test that negative total_stored raises error."""
        with pytest.raises(ValidationError):
            ModelVectorBatchStoreResult(
                success=True,
                total_stored=-1,
                execution_time_ms=100,
            )

    def test_validation_negative_time(self):
        """Test that negative execution_time_ms raises error."""
        with pytest.raises(ValidationError):
            ModelVectorBatchStoreResult(
                success=True,
                total_stored=10,
                execution_time_ms=-1,
            )


@pytest.mark.unit
class TestModelVectorSearchResults:
    """Tests for ModelVectorSearchResults."""

    def test_create_with_results(self):
        """Test creating search results container."""
        results = ModelVectorSearchResults(
            results=[
                ModelVectorSearchResult(id="doc_1", score=0.95),
                ModelVectorSearchResult(id="doc_2", score=0.87),
            ],
            total_results=2,
            query_time_ms=15,
        )
        assert len(results.results) == 2
        assert results.total_results == 2
        assert results.query_time_ms == 15

    def test_create_empty(self):
        """Test creating empty search results."""
        results = ModelVectorSearchResults(
            results=[],
            total_results=0,
            query_time_ms=5,
        )
        assert len(results.results) == 0
        assert results.total_results == 0

    def test_validation_negative_total(self):
        """Test that negative total_results raises error."""
        with pytest.raises(ValidationError):
            ModelVectorSearchResults(
                results=[],
                total_results=-1,
                query_time_ms=10,
            )


@pytest.mark.unit
class TestModelVectorDeleteResult:
    """Tests for ModelVectorDeleteResult."""

    def test_create_deleted(self):
        """Test creating result for deleted embedding."""
        result = ModelVectorDeleteResult(
            success=True,
            embedding_id="doc_123",
            deleted=True,
        )
        assert result.success is True
        assert result.deleted is True

    def test_create_not_found(self):
        """Test creating result for non-existent embedding."""
        result = ModelVectorDeleteResult(
            success=True,
            embedding_id="doc_456",
            deleted=False,
        )
        assert result.success is True
        assert result.deleted is False

    def test_create_failed(self):
        """Test creating result for failed deletion."""
        result = ModelVectorDeleteResult(
            success=False,
            embedding_id="doc_789",
            deleted=False,
        )
        assert result.success is False

    def test_validation_empty_id(self):
        """Test that empty embedding_id raises error."""
        with pytest.raises(ValidationError):
            ModelVectorDeleteResult(
                success=True,
                embedding_id="",
                deleted=True,
            )


@pytest.mark.unit
class TestModelVectorIndexResult:
    """Tests for ModelVectorIndexResult."""

    def test_create_success(self):
        """Test creating successful index result."""
        result = ModelVectorIndexResult(
            success=True,
            index_name="documents",
            dimension=1536,
            metric=EnumVectorDistanceMetric.COSINE,
            created_at=datetime.now(UTC),
        )
        assert result.success is True
        assert result.index_name == "documents"
        assert result.dimension == 1536
        assert result.metric == EnumVectorDistanceMetric.COSINE

    def test_create_failure(self):
        """Test creating failed index result."""
        result = ModelVectorIndexResult(
            success=False,
            index_name="documents",
            dimension=1536,
            metric=EnumVectorDistanceMetric.EUCLIDEAN,
        )
        assert result.success is False
        assert result.created_at is None

    def test_validation_empty_index_name(self):
        """Test that empty index_name raises error."""
        with pytest.raises(ValidationError):
            ModelVectorIndexResult(
                success=True,
                index_name="",
                dimension=512,
                metric=EnumVectorDistanceMetric.COSINE,
            )

    def test_validation_invalid_dimension(self):
        """Test that invalid dimension raises error."""
        with pytest.raises(ValidationError):
            ModelVectorIndexResult(
                success=True,
                index_name="idx",
                dimension=0,
                metric=EnumVectorDistanceMetric.COSINE,
            )

    def test_serialization(self):
        """Test model serialization."""
        result = ModelVectorIndexResult(
            success=True,
            index_name="test_idx",
            dimension=768,
            metric=EnumVectorDistanceMetric.DOT_PRODUCT,
        )
        data = result.model_dump()
        assert data["metric"] == "dot_product"
        assert data["dimension"] == 768
