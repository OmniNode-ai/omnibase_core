# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelVectorHealthStatus and ModelVectorHandlerMetadata."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.vector import (
    EnumVectorDistanceMetric,
    ModelVectorHandlerMetadata,
    ModelVectorHealthStatus,
)


@pytest.mark.unit
class TestModelVectorHealthStatus:
    """Tests for ModelVectorHealthStatus."""

    def test_create_healthy(self):
        """Test creating healthy status."""
        status = ModelVectorHealthStatus(
            healthy=True,
            latency_ms=15,
            details={
                "version": ModelSchemaValue.from_value("1.8.0"),
                "disk_usage": ModelSchemaValue.from_value("45%"),
            },
            indices=["documents", "images", "products"],
        )
        assert status.healthy is True
        assert status.latency_ms == 15
        assert len(status.details) == 2
        assert len(status.indices) == 3
        assert status.last_error is None

    def test_create_unhealthy(self):
        """Test creating unhealthy status."""
        status = ModelVectorHealthStatus(
            healthy=False,
            latency_ms=5000,
            details={},
            indices=[],
            last_error="Connection timeout after 5000ms",
        )
        assert status.healthy is False
        assert status.last_error == "Connection timeout after 5000ms"

    def test_create_minimal(self):
        """Test creating status with minimal fields."""
        status = ModelVectorHealthStatus(
            healthy=True,
            latency_ms=10,
        )
        assert status.healthy is True
        assert status.details == {}
        assert status.indices == []
        assert status.last_error is None

    def test_validation_negative_latency(self):
        """Test that negative latency raises error."""
        with pytest.raises(ValidationError):
            ModelVectorHealthStatus(
                healthy=True,
                latency_ms=-1,
            )

    def test_frozen(self):
        """Test that model is frozen."""
        status = ModelVectorHealthStatus(
            healthy=True,
            latency_ms=10,
        )
        with pytest.raises(ValidationError):
            status.healthy = False  # type: ignore[misc]

    def test_serialization(self):
        """Test model serialization."""
        status = ModelVectorHealthStatus(
            healthy=True,
            latency_ms=20,
            indices=["idx1", "idx2"],
        )
        data = status.model_dump()
        assert data["healthy"] is True
        assert data["latency_ms"] == 20
        assert data["indices"] == ["idx1", "idx2"]

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "healthy": False,
            "latency_ms": 100,
            "last_error": "Test error",
        }
        status = ModelVectorHealthStatus.model_validate(data)
        assert status.healthy is False
        assert status.last_error == "Test error"


@pytest.mark.unit
class TestModelVectorHandlerMetadata:
    """Tests for ModelVectorHandlerMetadata."""

    def test_create_full(self):
        """Test creating handler metadata with all fields."""
        metadata = ModelVectorHandlerMetadata(
            handler_type="qdrant",
            capabilities=[
                "store",
                "batch_store",
                "search",
                "filter",
                "delete",
                "upsert",
            ],
            supported_metrics=[
                EnumVectorDistanceMetric.COSINE,
                EnumVectorDistanceMetric.EUCLIDEAN,
                EnumVectorDistanceMetric.DOT_PRODUCT,
            ],
        )
        assert metadata.handler_type == "qdrant"
        assert len(metadata.capabilities) == 6
        assert len(metadata.supported_metrics) == 3

    def test_create_minimal(self):
        """Test creating handler metadata with minimal fields."""
        metadata = ModelVectorHandlerMetadata(
            handler_type="simple",
        )
        assert metadata.handler_type == "simple"
        assert metadata.capabilities == []
        assert metadata.supported_metrics == []

    def test_validation_empty_handler_type(self):
        """Test that empty handler_type raises error."""
        with pytest.raises(ValidationError):
            ModelVectorHandlerMetadata(handler_type="")

    def test_validation_missing_handler_type(self):
        """Test that missing handler_type raises error."""
        with pytest.raises(ValidationError):
            ModelVectorHandlerMetadata(
                capabilities=["store"],
            )  # type: ignore[call-arg]

    def test_frozen(self):
        """Test that model is frozen."""
        metadata = ModelVectorHandlerMetadata(handler_type="test")
        with pytest.raises(ValidationError):
            metadata.handler_type = "other"  # type: ignore[misc]

    def test_serialization(self):
        """Test model serialization."""
        metadata = ModelVectorHandlerMetadata(
            handler_type="pinecone",
            capabilities=["store", "search"],
            supported_metrics=[
                EnumVectorDistanceMetric.COSINE,
                EnumVectorDistanceMetric.DOT_PRODUCT,
            ],
        )
        data = metadata.model_dump()
        assert data["handler_type"] == "pinecone"
        assert "cosine" in data["supported_metrics"]
        assert "dot_product" in data["supported_metrics"]

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "handler_type": "milvus",
            "capabilities": ["store", "batch_store", "search"],
            "supported_metrics": ["euclidean", "manhattan"],
        }
        metadata = ModelVectorHandlerMetadata.model_validate(data)
        assert metadata.handler_type == "milvus"
        assert len(metadata.capabilities) == 3
        assert EnumVectorDistanceMetric.EUCLIDEAN in metadata.supported_metrics


@pytest.mark.unit
class TestModelVectorHealthAndMetadataEdgeCases:
    """Edge case tests for health and metadata models."""

    def test_health_zero_latency(self):
        """Test health status with zero latency."""
        status = ModelVectorHealthStatus(
            healthy=True,
            latency_ms=0,
        )
        assert status.latency_ms == 0

    def test_health_high_latency(self):
        """Test health status with very high latency."""
        status = ModelVectorHealthStatus(
            healthy=False,
            latency_ms=30000,  # 30 seconds
            last_error="Slow response",
        )
        assert status.latency_ms == 30000

    def test_metadata_empty_capabilities(self):
        """Test handler metadata with empty capabilities."""
        metadata = ModelVectorHandlerMetadata(
            handler_type="readonly",
            capabilities=[],
            supported_metrics=[EnumVectorDistanceMetric.COSINE],
        )
        assert metadata.capabilities == []

    def test_metadata_single_metric(self):
        """Test handler metadata with single supported metric."""
        metadata = ModelVectorHandlerMetadata(
            handler_type="basic",
            capabilities=["search"],
            supported_metrics=[EnumVectorDistanceMetric.EUCLIDEAN],
        )
        assert len(metadata.supported_metrics) == 1

    def test_health_unicode_indices(self):
        """Test health status with unicode index names."""
        status = ModelVectorHealthStatus(
            healthy=True,
            latency_ms=10,
            indices=["", "test-", "index_123"],
        )
        assert "" in status.indices

    def test_metadata_unicode_handler_type(self):
        """Test handler metadata with unicode handler type."""
        metadata = ModelVectorHandlerMetadata(
            handler_type="vector-db-",
        )
        assert "" in metadata.handler_type
