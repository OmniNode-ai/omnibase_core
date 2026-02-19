# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelVectorIndexConfig and related configuration models."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.vector import (
    EnumVectorDistanceMetric,
    ModelHnswConfig,
    ModelQuantizationConfig,
    ModelVectorIndexConfig,
)


@pytest.mark.unit
class TestModelHnswConfig:
    """Tests for ModelHnswConfig."""

    def test_create_default(self):
        """Test creating HNSW config with defaults."""
        config = ModelHnswConfig()
        assert config.m == 16
        assert config.ef_construction == 200
        assert config.ef_search == 100

    def test_create_custom(self):
        """Test creating HNSW config with custom values."""
        config = ModelHnswConfig(m=32, ef_construction=400, ef_search=200)
        assert config.m == 32
        assert config.ef_construction == 400
        assert config.ef_search == 200

    def test_m_validation(self):
        """Test M parameter validation."""
        with pytest.raises(ValidationError):
            ModelHnswConfig(m=2)  # Too low
        with pytest.raises(ValidationError):
            ModelHnswConfig(m=100)  # Too high

    def test_ef_construction_validation(self):
        """Test ef_construction validation."""
        with pytest.raises(ValidationError):
            ModelHnswConfig(ef_construction=5)  # Too low

    def test_frozen(self):
        """Test that config is frozen."""
        config = ModelHnswConfig()
        with pytest.raises(ValidationError):
            config.m = 32  # type: ignore[misc]


@pytest.mark.unit
class TestModelQuantizationConfig:
    """Tests for ModelQuantizationConfig."""

    def test_create_default(self):
        """Test creating quantization config with defaults."""
        config = ModelQuantizationConfig()
        assert config.enabled is False
        assert config.type == "scalar"
        assert config.bits == 8

    def test_create_enabled(self):
        """Test creating enabled quantization config."""
        config = ModelQuantizationConfig(enabled=True, type="product", bits=4)
        assert config.enabled is True
        assert config.type == "product"
        assert config.bits == 4

    def test_bits_validation(self):
        """Test bits parameter validation."""
        with pytest.raises(ValidationError):
            ModelQuantizationConfig(bits=2)  # Too low
        with pytest.raises(ValidationError):
            ModelQuantizationConfig(bits=32)  # Too high

    def test_frozen(self):
        """Test that config is frozen."""
        config = ModelQuantizationConfig()
        with pytest.raises(ValidationError):
            config.enabled = True  # type: ignore[misc]


@pytest.mark.unit
class TestModelVectorIndexConfigInstantiation:
    """Tests for ModelVectorIndexConfig instantiation."""

    def test_create_minimal(self):
        """Test creating index config with minimal required fields."""
        config = ModelVectorIndexConfig(dimension=1536)
        assert config.dimension == 1536
        assert config.metric == EnumVectorDistanceMetric.COSINE
        assert config.shards == 1
        assert config.replicas == 1
        assert config.quantization is None
        assert config.hnsw_config is None

    def test_create_with_metric(self):
        """Test creating index config with custom metric."""
        config = ModelVectorIndexConfig(
            dimension=768,
            metric=EnumVectorDistanceMetric.DOT_PRODUCT,
        )
        assert config.metric == EnumVectorDistanceMetric.DOT_PRODUCT

    def test_create_with_shards_and_replicas(self):
        """Test creating index config with sharding."""
        config = ModelVectorIndexConfig(
            dimension=512,
            shards=3,
            replicas=2,
        )
        assert config.shards == 3
        assert config.replicas == 2

    def test_create_with_hnsw(self):
        """Test creating index config with HNSW configuration."""
        hnsw = ModelHnswConfig(m=32, ef_construction=400)
        config = ModelVectorIndexConfig(
            dimension=1024,
            hnsw_config=hnsw,
        )
        assert config.hnsw_config is not None
        assert config.hnsw_config.m == 32

    def test_create_with_quantization(self):
        """Test creating index config with quantization."""
        quant = ModelQuantizationConfig(enabled=True, bits=4)
        config = ModelVectorIndexConfig(
            dimension=1536,
            quantization=quant,
        )
        assert config.quantization is not None
        assert config.quantization.enabled is True


@pytest.mark.unit
class TestModelVectorIndexConfigValidation:
    """Tests for ModelVectorIndexConfig validation."""

    def test_dimension_required(self):
        """Test that dimension is required."""
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig()  # type: ignore[call-arg]

    def test_dimension_min(self):
        """Test minimum dimension validation."""
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig(dimension=0)

    def test_dimension_max(self):
        """Test maximum dimension validation."""
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig(dimension=100000)  # Too large

    def test_shards_validation(self):
        """Test shards parameter validation."""
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig(dimension=512, shards=0)
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig(dimension=512, shards=200)

    def test_replicas_validation(self):
        """Test replicas parameter validation."""
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig(dimension=512, replicas=-1)
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig(dimension=512, replicas=20)

    def test_extra_fields_forbidden(self):
        """Test that extra fields raise validation error."""
        with pytest.raises(ValidationError):
            ModelVectorIndexConfig(
                dimension=512,
                extra="not_allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelVectorIndexConfigImmutability:
    """Tests for ModelVectorIndexConfig immutability."""

    def test_frozen_model(self):
        """Test that the model is frozen."""
        config = ModelVectorIndexConfig(dimension=512)
        with pytest.raises(ValidationError):
            config.dimension = 1024  # type: ignore[misc]


@pytest.mark.unit
class TestModelVectorIndexConfigSerialization:
    """Tests for ModelVectorIndexConfig serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        config = ModelVectorIndexConfig(
            dimension=1536,
            metric=EnumVectorDistanceMetric.EUCLIDEAN,
        )
        data = config.model_dump()
        assert data["dimension"] == 1536
        assert data["metric"] == "euclidean"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "dimension": 768,
            "metric": "cosine",
            "shards": 2,
        }
        config = ModelVectorIndexConfig.model_validate(data)
        assert config.dimension == 768
        assert config.shards == 2
