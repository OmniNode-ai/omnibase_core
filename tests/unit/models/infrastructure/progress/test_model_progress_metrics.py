"""Tests for ModelProgressMetrics."""

from datetime import UTC, datetime

import pytest

from omnibase_core.models.infrastructure.progress.model_progress_metrics import (
    ModelProgressMetrics,
)
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue


class TestModelProgressMetricsInstantiation:
    """Tests for ModelProgressMetrics instantiation."""

    def test_default_initialization(self):
        """Test default initialization."""
        metrics = ModelProgressMetrics()
        assert metrics.custom_metrics is not None
        assert len(metrics.tags) == 0
        assert isinstance(metrics.metrics_last_updated, datetime)

    def test_create_with_tags(self):
        """Test creating with initial tags."""
        metrics = ModelProgressMetrics(tags=["test", "important"])
        assert "test" in metrics.tags
        assert "important" in metrics.tags


class TestModelProgressMetricsCustomMetrics:
    """Tests for ModelProgressMetrics custom metrics management."""

    def test_add_custom_metric(self):
        """Test add_custom_metric method."""
        metrics = ModelProgressMetrics()
        # add_custom_metric accepts plain values
        metrics.add_custom_metric("test_key", "test_value")
        retrieved = metrics.get_custom_metric("test_key")
        assert retrieved is not None

    def test_add_custom_metric_updates_timestamp(self):
        """Test that add_custom_metric updates timestamp."""
        metrics = ModelProgressMetrics()
        old_timestamp = metrics.metrics_last_updated
        # add_custom_metric accepts plain values
        metrics.add_custom_metric("key", "test")
        assert metrics.metrics_last_updated >= old_timestamp

    def test_get_custom_metric_nonexistent(self):
        """Test get_custom_metric for nonexistent key."""
        metrics = ModelProgressMetrics()
        result = metrics.get_custom_metric("nonexistent")
        assert result is None

    def test_remove_custom_metric(self):
        """Test remove_custom_metric method."""
        metrics = ModelProgressMetrics()
        # add_custom_metric accepts plain values
        metrics.add_custom_metric("key", "test")
        result = metrics.remove_custom_metric("key")
        assert result is True
        assert metrics.get_custom_metric("key") is None

    def test_remove_custom_metric_nonexistent(self):
        """Test remove_custom_metric for nonexistent key."""
        metrics = ModelProgressMetrics()
        result = metrics.remove_custom_metric("nonexistent")
        assert result is False


class TestModelProgressMetricsTags:
    """Tests for ModelProgressMetrics tag management."""

    def test_add_tag(self):
        """Test add_tag method."""
        metrics = ModelProgressMetrics()
        metrics.add_tag("important")
        assert "important" in metrics.tags

    def test_add_tag_duplicate(self):
        """Test add_tag doesn't add duplicates."""
        metrics = ModelProgressMetrics()
        metrics.add_tag("test")
        metrics.add_tag("test")
        assert metrics.tags.count("test") == 1

    def test_add_tag_updates_timestamp(self):
        """Test that add_tag updates timestamp."""
        metrics = ModelProgressMetrics()
        old_timestamp = metrics.metrics_last_updated
        metrics.add_tag("new_tag")
        assert metrics.metrics_last_updated >= old_timestamp

    def test_remove_tag(self):
        """Test remove_tag method."""
        metrics = ModelProgressMetrics()
        metrics.add_tag("test")
        result = metrics.remove_tag("test")
        assert result is True
        assert "test" not in metrics.tags

    def test_remove_tag_nonexistent(self):
        """Test remove_tag for nonexistent tag."""
        metrics = ModelProgressMetrics()
        result = metrics.remove_tag("nonexistent")
        assert result is False

    def test_has_tag(self):
        """Test has_tag method."""
        metrics = ModelProgressMetrics()
        metrics.add_tag("test")
        assert metrics.has_tag("test") is True
        assert metrics.has_tag("nonexistent") is False

    def test_add_tags_multiple(self):
        """Test add_tags method with multiple tags."""
        metrics = ModelProgressMetrics()
        metrics.add_tags(["tag1", "tag2", "tag3"])
        assert "tag1" in metrics.tags
        assert "tag2" in metrics.tags
        assert "tag3" in metrics.tags

    def test_remove_tags_multiple(self):
        """Test remove_tags method with multiple tags."""
        metrics = ModelProgressMetrics()
        metrics.add_tags(["tag1", "tag2", "tag3"])
        removed = metrics.remove_tags(["tag1", "tag3"])
        assert "tag1" in removed
        assert "tag3" in removed
        assert len(removed) == 2
        assert "tag2" in metrics.tags

    def test_clear_tags(self):
        """Test clear_tags method."""
        metrics = ModelProgressMetrics()
        metrics.add_tags(["tag1", "tag2", "tag3"])
        metrics.clear_tags()
        assert len(metrics.tags) == 0

    def test_clear_tags_empty(self):
        """Test clear_tags when already empty."""
        metrics = ModelProgressMetrics()
        metrics.clear_tags()
        assert len(metrics.tags) == 0

    def test_get_tags_count(self):
        """Test get_tags_count method."""
        metrics = ModelProgressMetrics()
        assert metrics.get_tags_count() == 0
        metrics.add_tags(["tag1", "tag2"])
        assert metrics.get_tags_count() == 2


class TestModelProgressMetricsCounters:
    """Tests for ModelProgressMetrics counter methods."""

    def test_get_metrics_count(self):
        """Test get_metrics_count method."""
        metrics = ModelProgressMetrics()
        assert metrics.get_metrics_count() == 0

    def test_has_custom_metrics_false(self):
        """Test has_custom_metrics when no metrics exist."""
        metrics = ModelProgressMetrics()
        assert metrics.has_custom_metrics() is False


class TestModelProgressMetricsSummary:
    """Tests for ModelProgressMetrics summary methods."""

    def test_get_metrics_summary_empty(self):
        """Test get_metrics_summary when no metrics."""
        metrics = ModelProgressMetrics()
        summary = metrics.get_metrics_summary()
        assert len(summary) == 0


class TestModelProgressMetricsStandardMetrics:
    """Tests for ModelProgressMetrics standard metrics update."""

    def test_update_standard_metrics(self):
        """Test update_standard_metrics method."""
        metrics = ModelProgressMetrics()
        metrics.update_standard_metrics(
            percentage=75.0,
            current_step=7,
            total_steps=10,
            is_completed=False,
            elapsed_seconds=30.5,
        )
        summary = metrics.get_metrics_summary()
        assert "percentage" in summary
        assert "current_step" in summary
        assert "total_steps" in summary
        assert "is_completed" in summary
        assert "elapsed_seconds" in summary


class TestModelProgressMetricsReset:
    """Tests for ModelProgressMetrics reset functionality."""

    def test_reset(self):
        """Test reset method."""
        metrics = ModelProgressMetrics()
        metrics.add_tags(["tag1", "tag2"])
        metrics.reset()
        assert metrics.get_metrics_count() == 0
        assert metrics.get_tags_count() == 0

    def test_reset_tags_only(self):
        """Test reset_tags_only method."""
        metrics = ModelProgressMetrics()
        metrics.add_tags(["tag1", "tag2"])
        metrics.reset_tags_only()
        assert metrics.get_tags_count() == 0


class TestModelProgressMetricsFactoryMethods:
    """Tests for ModelProgressMetrics factory methods."""

    def test_create_with_tags_factory(self):
        """Test create_with_tags factory method."""
        tags = ["tag1", "tag2", "tag3"]
        metrics = ModelProgressMetrics.create_with_tags(tags)
        assert metrics.get_tags_count() == 3
        assert "tag1" in metrics.tags

    def test_create_with_metrics_factory(self):
        """Test create_with_metrics factory method."""
        # create_with_metrics accepts plain values
        initial_metrics = {
            "key1": "value1",
            "key2": 42,
        }
        metrics = ModelProgressMetrics.create_with_metrics(initial_metrics)
        assert metrics.get_metrics_count() == 2
        assert metrics.get_custom_metric("key1") is not None


class TestModelProgressMetricsProtocols:
    """Tests for ModelProgressMetrics protocol implementations."""

    def test_execute_protocol(self):
        """Test execute method."""
        metrics = ModelProgressMetrics()
        result = metrics.execute()
        assert result is True

    def test_configure_protocol(self):
        """Test configure method."""
        metrics = ModelProgressMetrics()
        result = metrics.configure()
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize method."""
        metrics = ModelProgressMetrics()
        metrics.add_tag("test")
        data = metrics.serialize()
        assert isinstance(data, dict)
        assert "tags" in data


class TestModelProgressMetricsEdgeCases:
    """Tests for ModelProgressMetrics edge cases."""

    def test_add_same_tag_multiple_times(self):
        """Test adding same tag multiple times."""
        metrics = ModelProgressMetrics()
        metrics.add_tag("duplicate")
        metrics.add_tag("duplicate")
        metrics.add_tag("duplicate")
        assert metrics.get_tags_count() == 1

    def test_timestamp_updates_on_changes(self):
        """Test that timestamp updates on various changes."""
        metrics = ModelProgressMetrics()
        initial_time = metrics.metrics_last_updated

        metrics.add_tag("test")
        time_after_tag = metrics.metrics_last_updated
        assert time_after_tag >= initial_time

        metrics.remove_tag("test")
        time_after_remove = metrics.metrics_last_updated
        assert time_after_remove >= time_after_tag
