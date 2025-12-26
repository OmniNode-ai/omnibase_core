# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelVectorConnectionConfig."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.vector import ModelVectorConnectionConfig


@pytest.mark.unit
class TestModelVectorConnectionConfigInstantiation:
    """Tests for ModelVectorConnectionConfig instantiation."""

    def test_create_minimal(self):
        """Test creating connection config with minimal required fields."""
        config = ModelVectorConnectionConfig(url="http://localhost:6333")
        assert config.url == "http://localhost:6333"
        assert config.api_key is None
        assert config.timeout == 30.0
        assert config.pool_size == 10

    def test_create_with_api_key(self):
        """Test creating connection config with API key."""
        config = ModelVectorConnectionConfig(
            url="https://my-cluster.vectordb.io",
            api_key="sk-xxxxx",
        )
        assert config.api_key == "sk-xxxxx"

    def test_create_with_timeout(self):
        """Test creating connection config with custom timeout."""
        config = ModelVectorConnectionConfig(
            url="http://localhost:6333",
            timeout=60.0,
        )
        assert config.timeout == 60.0

    def test_create_with_pool_size(self):
        """Test creating connection config with custom pool size."""
        config = ModelVectorConnectionConfig(
            url="http://localhost:6333",
            pool_size=20,
        )
        assert config.pool_size == 20

    def test_create_full(self):
        """Test creating connection config with all fields."""
        config = ModelVectorConnectionConfig(
            url="https://api.vectordb.io",
            api_key="secret-key",
            timeout=120.0,
            pool_size=50,
        )
        assert config.url == "https://api.vectordb.io"
        assert config.api_key == "secret-key"
        assert config.timeout == 120.0
        assert config.pool_size == 50


@pytest.mark.unit
class TestModelVectorConnectionConfigValidation:
    """Tests for ModelVectorConnectionConfig validation."""

    def test_url_required(self):
        """Test that URL is required."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig()  # type: ignore[call-arg]

    def test_url_empty_raises(self):
        """Test that empty URL raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(url="")

    def test_url_invalid_scheme_raises(self):
        """Test that URL without http/https raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(url="ftp://localhost:6333")

    def test_url_no_scheme_raises(self):
        """Test that URL without scheme raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(url="localhost:6333")

    def test_timeout_min(self):
        """Test minimum timeout validation."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(url="http://localhost:6333", timeout=0.5)

    def test_timeout_max(self):
        """Test maximum timeout validation."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(url="http://localhost:6333", timeout=700.0)

    def test_pool_size_min(self):
        """Test minimum pool size validation."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(url="http://localhost:6333", pool_size=0)

    def test_pool_size_max(self):
        """Test maximum pool size validation."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(url="http://localhost:6333", pool_size=150)

    def test_extra_fields_forbidden(self):
        """Test that extra fields raise validation error."""
        with pytest.raises(ValidationError):
            ModelVectorConnectionConfig(
                url="http://localhost:6333",
                extra="not_allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelVectorConnectionConfigImmutability:
    """Tests for ModelVectorConnectionConfig immutability."""

    def test_frozen_model(self):
        """Test that the model is frozen."""
        config = ModelVectorConnectionConfig(url="http://localhost:6333")
        with pytest.raises(ValidationError):
            config.url = "http://other:6333"  # type: ignore[misc]


@pytest.mark.unit
class TestModelVectorConnectionConfigSerialization:
    """Tests for ModelVectorConnectionConfig serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        config = ModelVectorConnectionConfig(
            url="http://localhost:6333",
            api_key="test-key",
        )
        data = config.model_dump()
        assert data["url"] == "http://localhost:6333"
        assert data["api_key"] == "test-key"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "url": "https://api.example.com",
            "timeout": 45.0,
        }
        config = ModelVectorConnectionConfig.model_validate(data)
        assert config.url == "https://api.example.com"
        assert config.timeout == 45.0


@pytest.mark.unit
class TestModelVectorConnectionConfigEdgeCases:
    """Tests for ModelVectorConnectionConfig edge cases."""

    def test_url_with_path(self):
        """Test URL with path component."""
        config = ModelVectorConnectionConfig(
            url="http://localhost:6333/api/v1",
        )
        assert config.url == "http://localhost:6333/api/v1"

    def test_url_with_port(self):
        """Test URL with non-standard port."""
        config = ModelVectorConnectionConfig(
            url="https://vectordb.example.com:8443",
        )
        assert config.url == "https://vectordb.example.com:8443"

    def test_url_trimmed(self):
        """Test that URL whitespace is trimmed."""
        config = ModelVectorConnectionConfig(
            url="  http://localhost:6333  ",
        )
        assert config.url == "http://localhost:6333"
