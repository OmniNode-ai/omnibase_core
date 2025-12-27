"""Tests for ModelGraphHealthStatus."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_health_status import ModelGraphHealthStatus


@pytest.mark.unit
class TestModelGraphHealthStatusBasics:
    """Test basic ModelGraphHealthStatus functionality."""

    def test_default_initialization(self):
        """Test default initialization with default values."""
        status = ModelGraphHealthStatus()

        assert status.healthy is False
        assert status.latency_ms == 0.0
        assert status.database_version is None
        assert status.connection_count == 0

    def test_initialization_healthy(self):
        """Test initialization for healthy status."""
        status = ModelGraphHealthStatus(
            healthy=True,
            latency_ms=5.2,
            database_version="5.15.0",
            connection_count=10,
        )

        assert status.healthy is True
        assert status.latency_ms == 5.2
        assert status.database_version == "5.15.0"
        assert status.connection_count == 10

    def test_initialization_unhealthy(self):
        """Test initialization for unhealthy status."""
        status = ModelGraphHealthStatus(
            healthy=False,
            latency_ms=0.0,
            database_version=None,
            connection_count=0,
        )

        assert status.healthy is False
        assert status.database_version is None


@pytest.mark.unit
class TestModelGraphHealthStatusValidation:
    """Test ModelGraphHealthStatus validation."""

    def test_negative_latency_invalid(self):
        """Test that negative latency is invalid."""
        with pytest.raises(ValidationError):
            ModelGraphHealthStatus(latency_ms=-1.0)

    def test_negative_connection_count_invalid(self):
        """Test that negative connection count is invalid."""
        with pytest.raises(ValidationError):
            ModelGraphHealthStatus(connection_count=-1)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphHealthStatus(unknown_field="value")


@pytest.mark.unit
class TestModelGraphHealthStatusImmutability:
    """Test ModelGraphHealthStatus immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        status = ModelGraphHealthStatus(healthy=True)

        with pytest.raises(ValidationError):
            status.healthy = False


@pytest.mark.unit
class TestModelGraphHealthStatusSerialization:
    """Test ModelGraphHealthStatus serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        status = ModelGraphHealthStatus(
            healthy=True,
            latency_ms=10.0,
            database_version="5.15.0",
            connection_count=5,
        )

        data = status.model_dump()

        assert data["healthy"] is True
        assert data["latency_ms"] == 10.0
        assert data["database_version"] == "5.15.0"
        assert data["connection_count"] == 5
