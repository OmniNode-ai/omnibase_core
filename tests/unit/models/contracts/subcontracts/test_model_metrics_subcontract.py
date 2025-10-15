"""
Tests for ModelMetricsSubcontract.

Comprehensive tests for metrics subcontract configuration and validation.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_metrics_subcontract import (
    ModelMetricsSubcontract,
)
from omnibase_core.primitives.model_semver import ModelSemVer


class TestModelMetricsSubcontractInitialization:
    """Test ModelMetricsSubcontract initialization."""

    def test_create_default_metrics_subcontract(self):
        """Test creating metrics subcontract with default values."""
        metrics = ModelMetricsSubcontract()
        assert metrics is not None
        assert isinstance(metrics, ModelMetricsSubcontract)
        assert metrics.metrics_enabled is True
        assert metrics.metrics_backend == "prometheus"
        assert metrics.enable_histograms is True
        assert metrics.enable_counters is True
        assert metrics.enable_gauges is True
        assert metrics.enable_summaries is False

    def test_metrics_subcontract_with_custom_values(self):
        """Test creating metrics subcontract with custom values."""
        metrics = ModelMetricsSubcontract(
            metrics_enabled=False,
            metrics_backend="statsd",
            collection_interval_seconds=120,
            export_interval_seconds=30,
        )
        assert metrics.metrics_enabled is False
        assert metrics.metrics_backend == "statsd"
        assert metrics.collection_interval_seconds == 120
        assert metrics.export_interval_seconds == 30

    def test_metrics_subcontract_inheritance(self):
        """Test that ModelMetricsSubcontract inherits from BaseModel."""
        from pydantic import BaseModel

        metrics = ModelMetricsSubcontract()
        assert isinstance(metrics, BaseModel)

    def test_interface_version_present(self):
        """Test that INTERFACE_VERSION is present and correct."""
        assert hasattr(ModelMetricsSubcontract, "INTERFACE_VERSION")
        assert isinstance(ModelMetricsSubcontract.INTERFACE_VERSION, ModelSemVer)
        assert ModelMetricsSubcontract.INTERFACE_VERSION.major == 1
        assert ModelMetricsSubcontract.INTERFACE_VERSION.minor == 0
        assert ModelMetricsSubcontract.INTERFACE_VERSION.patch == 0


class TestModelMetricsSubcontractValidation:
    """Test ModelMetricsSubcontract field validation."""

    def test_metrics_backend_validation_prometheus(self):
        """Test metrics_backend accepts prometheus."""
        metrics = ModelMetricsSubcontract(metrics_backend="prometheus")
        assert metrics.metrics_backend == "prometheus"

    def test_metrics_backend_validation_statsd(self):
        """Test metrics_backend accepts statsd."""
        metrics = ModelMetricsSubcontract(metrics_backend="statsd")
        assert metrics.metrics_backend == "statsd"

    def test_metrics_backend_validation_none(self):
        """Test metrics_backend accepts none."""
        metrics = ModelMetricsSubcontract(metrics_backend="none")
        assert metrics.metrics_backend == "none"

    def test_metrics_backend_validation_invalid(self):
        """Test metrics_backend rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMetricsSubcontract(metrics_backend="invalid_backend")
        assert "must be one of" in str(exc_info.value)

    def test_collection_interval_validation_min(self):
        """Test collection_interval_seconds minimum constraint."""
        metrics = ModelMetricsSubcontract(
            collection_interval_seconds=1,
            export_interval_seconds=1,
        )
        assert metrics.collection_interval_seconds == 1

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(
                collection_interval_seconds=0,
                export_interval_seconds=1,
            )

    def test_collection_interval_validation_max(self):
        """Test collection_interval_seconds maximum constraint."""
        metrics = ModelMetricsSubcontract(collection_interval_seconds=3600)
        assert metrics.collection_interval_seconds == 3600

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(collection_interval_seconds=3601)

    def test_export_interval_validation_min(self):
        """Test export_interval_seconds minimum constraint."""
        metrics = ModelMetricsSubcontract(export_interval_seconds=1)
        assert metrics.export_interval_seconds == 1

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(export_interval_seconds=0)

    def test_export_interval_validation_max(self):
        """Test export_interval_seconds maximum constraint."""
        # Must set collection_interval high enough to allow max export_interval
        metrics = ModelMetricsSubcontract(
            collection_interval_seconds=300,
            export_interval_seconds=300,
        )
        assert metrics.export_interval_seconds == 300

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(
                collection_interval_seconds=3600,
                export_interval_seconds=301,
            )

    def test_export_interval_exceeds_collection_interval(self):
        """Test that export interval cannot exceed collection interval."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMetricsSubcontract(
                collection_interval_seconds=60,
                export_interval_seconds=120,
            )
        assert "cannot exceed collection_interval_seconds" in str(exc_info.value)

    def test_export_interval_equals_collection_interval(self):
        """Test that export interval can equal collection interval."""
        metrics = ModelMetricsSubcontract(
            collection_interval_seconds=60,
            export_interval_seconds=60,
        )
        assert metrics.export_interval_seconds == 60

    def test_max_label_cardinality_validation(self):
        """Test max_label_cardinality field constraints."""
        metrics = ModelMetricsSubcontract(max_label_cardinality=1)
        assert metrics.max_label_cardinality == 1

        metrics = ModelMetricsSubcontract(max_label_cardinality=100000)
        assert metrics.max_label_cardinality == 100000

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(max_label_cardinality=0)

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(max_label_cardinality=100001)

    def test_aggregation_window_validation(self):
        """Test aggregation_window_seconds field constraints."""
        metrics = ModelMetricsSubcontract(aggregation_window_seconds=1)
        assert metrics.aggregation_window_seconds == 1

        metrics = ModelMetricsSubcontract(aggregation_window_seconds=86400)
        assert metrics.aggregation_window_seconds == 86400

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(aggregation_window_seconds=0)

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(aggregation_window_seconds=86401)

    def test_retention_period_validation(self):
        """Test retention_period_hours field constraints."""
        metrics = ModelMetricsSubcontract(retention_period_hours=1)
        assert metrics.retention_period_hours == 1

        metrics = ModelMetricsSubcontract(retention_period_hours=8760)
        assert metrics.retention_period_hours == 8760

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(retention_period_hours=0)

        with pytest.raises(ValidationError):
            ModelMetricsSubcontract(retention_period_hours=8761)


class TestModelMetricsSubcontractSerialization:
    """Test ModelMetricsSubcontract serialization."""

    def test_metrics_subcontract_serialization(self):
        """Test metrics subcontract model_dump."""
        metrics = ModelMetricsSubcontract(
            metrics_backend="statsd",
            collection_interval_seconds=120,
        )
        data = metrics.model_dump()
        assert isinstance(data, dict)
        assert data["metrics_backend"] == "statsd"
        assert data["collection_interval_seconds"] == 120
        assert data["metrics_enabled"] is True

    def test_metrics_subcontract_deserialization(self):
        """Test metrics subcontract model_validate."""
        data = {
            "metrics_backend": "prometheus",
            "collection_interval_seconds": 90,
            "export_interval_seconds": 15,
        }
        metrics = ModelMetricsSubcontract.model_validate(data)
        assert metrics.metrics_backend == "prometheus"
        assert metrics.collection_interval_seconds == 90
        assert metrics.export_interval_seconds == 15

    def test_metrics_subcontract_json_serialization(self):
        """Test metrics subcontract JSON serialization."""
        metrics = ModelMetricsSubcontract()
        json_data = metrics.model_dump_json()
        assert isinstance(json_data, str)
        assert "metrics_backend" in json_data
        assert "collection_interval_seconds" in json_data

    def test_metrics_subcontract_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelMetricsSubcontract(
            metrics_enabled=False,
            metrics_backend="statsd",
            enable_histograms=False,
            enable_summaries=True,
            collection_interval_seconds=180,
        )
        data = original.model_dump()
        restored = ModelMetricsSubcontract.model_validate(data)
        assert restored.metrics_enabled == original.metrics_enabled
        assert restored.metrics_backend == original.metrics_backend
        assert restored.enable_histograms == original.enable_histograms
        assert restored.enable_summaries == original.enable_summaries
        assert (
            restored.collection_interval_seconds == original.collection_interval_seconds
        )


class TestModelMetricsSubcontractMetricTypes:
    """Test metric type enablement flags."""

    def test_all_metric_types_enabled(self):
        """Test enabling all metric types."""
        metrics = ModelMetricsSubcontract(
            enable_histograms=True,
            enable_counters=True,
            enable_gauges=True,
            enable_summaries=True,
        )
        assert metrics.enable_histograms is True
        assert metrics.enable_counters is True
        assert metrics.enable_gauges is True
        assert metrics.enable_summaries is True

    def test_all_metric_types_disabled(self):
        """Test disabling all metric types."""
        metrics = ModelMetricsSubcontract(
            enable_histograms=False,
            enable_counters=False,
            enable_gauges=False,
            enable_summaries=False,
        )
        assert metrics.enable_histograms is False
        assert metrics.enable_counters is False
        assert metrics.enable_gauges is False
        assert metrics.enable_summaries is False

    def test_selective_metric_types(self):
        """Test selective metric type enablement."""
        metrics = ModelMetricsSubcontract(
            enable_histograms=True,
            enable_counters=True,
            enable_gauges=False,
            enable_summaries=False,
        )
        assert metrics.enable_histograms is True
        assert metrics.enable_counters is True
        assert metrics.enable_gauges is False
        assert metrics.enable_summaries is False


class TestModelMetricsSubcontractPerformanceMonitoring:
    """Test performance monitoring configuration."""

    def test_all_performance_metrics_enabled(self):
        """Test enabling all performance metrics."""
        metrics = ModelMetricsSubcontract(
            enable_performance_metrics=True,
            track_response_times=True,
            track_throughput=True,
            track_error_rates=True,
        )
        assert metrics.enable_performance_metrics is True
        assert metrics.track_response_times is True
        assert metrics.track_throughput is True
        assert metrics.track_error_rates is True

    def test_performance_metrics_disabled(self):
        """Test disabling performance metrics."""
        metrics = ModelMetricsSubcontract(
            enable_performance_metrics=False,
            track_response_times=False,
            track_throughput=False,
            track_error_rates=False,
        )
        assert metrics.enable_performance_metrics is False
        assert metrics.track_response_times is False
        assert metrics.track_throughput is False
        assert metrics.track_error_rates is False


class TestModelMetricsSubcontractEdgeCases:
    """Test metrics subcontract edge cases."""

    def test_metrics_disabled_globally(self):
        """Test that metrics can be disabled globally."""
        metrics = ModelMetricsSubcontract(metrics_enabled=False)
        assert metrics.metrics_enabled is False
        # Other settings should still be valid
        assert metrics.metrics_backend == "prometheus"
        assert metrics.collection_interval_seconds == 60

    def test_custom_labels_disabled(self):
        """Test custom labels can be disabled."""
        metrics = ModelMetricsSubcontract(enable_custom_labels=False)
        assert metrics.enable_custom_labels is False

    def test_minimal_intervals(self):
        """Test minimal valid interval values."""
        metrics = ModelMetricsSubcontract(
            collection_interval_seconds=1,
            export_interval_seconds=1,
        )
        assert metrics.collection_interval_seconds == 1
        assert metrics.export_interval_seconds == 1

    def test_maximal_intervals(self):
        """Test maximal valid interval values."""
        metrics = ModelMetricsSubcontract(
            collection_interval_seconds=3600,
            export_interval_seconds=300,
        )
        assert metrics.collection_interval_seconds == 3600
        assert metrics.export_interval_seconds == 300

    def test_none_backend(self):
        """Test using 'none' as metrics backend."""
        metrics = ModelMetricsSubcontract(metrics_backend="none")
        assert metrics.metrics_backend == "none"


class TestModelMetricsSubcontractAttributes:
    """Test metrics subcontract attributes and metadata."""

    def test_metrics_subcontract_attributes(self):
        """Test that metrics subcontract has expected attributes."""
        metrics = ModelMetricsSubcontract()
        assert hasattr(metrics, "model_dump")
        assert callable(metrics.model_dump)
        assert hasattr(ModelMetricsSubcontract, "model_validate")
        assert callable(ModelMetricsSubcontract.model_validate)

    def test_metrics_subcontract_docstring(self):
        """Test metrics subcontract docstring."""
        assert ModelMetricsSubcontract.__doc__ is not None
        assert "metrics" in ModelMetricsSubcontract.__doc__.lower()

    def test_metrics_subcontract_class_name(self):
        """Test metrics subcontract class name."""
        assert ModelMetricsSubcontract.__name__ == "ModelMetricsSubcontract"

    def test_metrics_subcontract_module(self):
        """Test metrics subcontract module."""
        assert (
            ModelMetricsSubcontract.__module__
            == "omnibase_core.models.contracts.subcontracts.model_metrics_subcontract"
        )

    def test_metrics_subcontract_copy(self):
        """Test metrics subcontract copying."""
        metrics = ModelMetricsSubcontract(collection_interval_seconds=120)
        copied = metrics.model_copy()
        assert copied is not None
        assert copied.collection_interval_seconds == 120
        assert copied is not metrics


class TestModelMetricsSubcontractConfigDict:
    """Test metrics subcontract ConfigDict settings."""

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        data = {
            "metrics_backend": "prometheus",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }
        metrics = ModelMetricsSubcontract.model_validate(data)
        assert metrics.metrics_backend == "prometheus"
        assert not hasattr(metrics, "extra_field")
        assert not hasattr(metrics, "another_extra")

    def test_validate_assignment_enabled(self):
        """Test that assignment validation is enabled."""
        metrics = ModelMetricsSubcontract()

        # This should trigger validation
        with pytest.raises(ValidationError):
            metrics.collection_interval_seconds = 0
