# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelWidgetDefinition."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard import (
    ModelChartSeriesConfig,
    ModelWidgetConfigChart,
    ModelWidgetConfigEventFeed,
    ModelWidgetConfigMetricCard,
    ModelWidgetConfigStatusGrid,
    ModelWidgetConfigTable,
    ModelWidgetDefinition,
)


def _make_pie_chart_config() -> ModelWidgetConfigChart:
    """Create a pie chart config (no series required)."""
    return ModelWidgetConfigChart(chart_type="pie")


def _make_line_chart_config() -> ModelWidgetConfigChart:
    """Create a line chart config with required series."""
    return ModelWidgetConfigChart(
        chart_type="line",
        series=(ModelChartSeriesConfig(name="Series 1", data_key="value"),),
    )


@pytest.mark.unit
class TestModelWidgetDefinition:
    """Tests for ModelWidgetDefinition model."""

    def test_create_with_chart_config(self) -> None:
        """Test creating widget with chart config."""
        widget_id = uuid4()
        config = _make_line_chart_config()
        widget = ModelWidgetDefinition(
            widget_id=widget_id,
            title="Test Chart",
            config=config,
        )
        assert widget.widget_id == widget_id
        assert widget.title == "Test Chart"
        assert widget.config.config_kind == "chart"
        assert widget.config.widget_type == EnumWidgetType.CHART

    def test_create_with_table_config(self) -> None:
        """Test creating widget with table config."""
        config = ModelWidgetConfigTable()
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test Table",
            config=config,
        )
        assert widget.config.config_kind == "table"
        assert widget.config.widget_type == EnumWidgetType.TABLE

    def test_create_with_metric_card_config(self) -> None:
        """Test creating widget with metric card config."""
        config = ModelWidgetConfigMetricCard(metric_key="cpu_usage", label="CPU")
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="CPU Usage",
            config=config,
        )
        assert widget.config.config_kind == "metric_card"
        assert widget.config.metric_key == "cpu_usage"

    def test_create_with_status_grid_config(self) -> None:
        """Test creating widget with status grid config."""
        config = ModelWidgetConfigStatusGrid()
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Service Status",
            config=config,
        )
        assert widget.config.config_kind == "status_grid"

    def test_create_with_event_feed_config(self) -> None:
        """Test creating widget with event feed config."""
        config = ModelWidgetConfigEventFeed()
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Event Feed",
            config=config,
        )
        assert widget.config.config_kind == "event_feed"

    def test_roundtrip_serialization(self) -> None:
        """Test model_dump and model_validate roundtrip."""
        config = _make_line_chart_config()
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test Chart",
            config=config,
            row=1,
            col=2,
            width=6,
            height=3,
        )
        data = widget.model_dump()
        restored = ModelWidgetDefinition.model_validate(data)
        assert restored == widget
        assert restored.config.config_kind == "chart"

    def test_discriminated_union_from_dict(self) -> None:
        """Test discriminated union works from dict."""
        data = {
            "widget_id": "12345678-1234-5678-1234-567812345678",
            "title": "Chart",
            "config": {
                "config_kind": "chart",
                "chart_type": "bar",
                "series": [{"name": "Data", "data_key": "value"}],
            },
        }
        widget = ModelWidgetDefinition.model_validate(data)
        assert widget.config.config_kind == "chart"
        assert widget.config.chart_type == "bar"

    def test_discriminated_union_table_from_dict(self) -> None:
        """Test discriminated union works for table from dict."""
        data = {
            "widget_id": "22345678-1234-5678-1234-567812345678",
            "title": "Table",
            "config": {
                "config_kind": "table",
                "page_size": 20,
            },
        }
        widget = ModelWidgetDefinition.model_validate(data)
        assert widget.config.config_kind == "table"
        assert widget.config.page_size == 20

    def test_discriminated_union_metric_card_from_dict(self) -> None:
        """Test discriminated union works for metric card from dict."""
        data = {
            "widget_id": "32345678-1234-5678-1234-567812345678",
            "title": "Metric Card",
            "config": {
                "config_kind": "metric_card",
                "metric_key": "memory_usage",
                "label": "Memory",
            },
        }
        widget = ModelWidgetDefinition.model_validate(data)
        assert widget.config.config_kind == "metric_card"
        assert widget.config.metric_key == "memory_usage"

    def test_discriminated_union_status_grid_from_dict(self) -> None:
        """Test discriminated union works for status grid from dict."""
        data = {
            "widget_id": "42345678-1234-5678-1234-567812345678",
            "title": "Status Grid",
            "config": {
                "config_kind": "status_grid",
                "columns": 4,
            },
        }
        widget = ModelWidgetDefinition.model_validate(data)
        assert widget.config.config_kind == "status_grid"
        assert widget.config.columns == 4

    def test_discriminated_union_event_feed_from_dict(self) -> None:
        """Test discriminated union works for event feed from dict."""
        data = {
            "widget_id": "52345678-1234-5678-1234-567812345678",
            "title": "Event Feed",
            "config": {
                "config_kind": "event_feed",
                "max_items": 100,
            },
        }
        widget = ModelWidgetDefinition.model_validate(data)
        assert widget.config.config_kind == "event_feed"
        assert widget.config.max_items == 100

    def test_frozen_model(self) -> None:
        """Test that model is frozen."""
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test",
            config=_make_pie_chart_config(),
        )
        # Pydantic frozen models raise ValidationError on attribute mutation
        with pytest.raises((ValidationError, TypeError)):
            widget.title = "New Title"  # type: ignore[misc]

    def test_default_layout_values(self) -> None:
        """Test default layout values."""
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test",
            config=_make_pie_chart_config(),
        )
        assert widget.row == 0
        assert widget.col == 0
        assert widget.width == 1
        assert widget.height == 1

    def test_extra_config_field(self) -> None:
        """Test extra_config field for extension."""
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test",
            config=_make_pie_chart_config(),
            extra_config={"custom_key": "custom_value"},
        )
        assert widget.extra_config == {"custom_key": "custom_value"}

    def test_invalid_widget_id_raises(self) -> None:
        """Test that invalid widget_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelWidgetDefinition(
                widget_id="not-a-uuid",  # type: ignore[arg-type]
                title="Test",
                config=_make_pie_chart_config(),
            )

    def test_invalid_title_raises(self) -> None:
        """Test that empty title raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelWidgetDefinition(
                widget_id=uuid4(),
                title="",
                config=_make_pie_chart_config(),
            )

    def test_layout_constraints(self) -> None:
        """Test layout field constraints."""
        pie_config = _make_pie_chart_config()
        # Test row and col must be >= 0
        with pytest.raises(ValidationError):
            ModelWidgetDefinition(
                widget_id=uuid4(),
                title="Test",
                config=pie_config,
                row=-1,
            )
        with pytest.raises(ValidationError):
            ModelWidgetDefinition(
                widget_id=uuid4(),
                title="Test",
                config=pie_config,
                col=-1,
            )
        # Test width must be >= 1 and <= 12
        with pytest.raises(ValidationError):
            ModelWidgetDefinition(
                widget_id=uuid4(),
                title="Test",
                config=pie_config,
                width=0,
            )
        with pytest.raises(ValidationError):
            ModelWidgetDefinition(
                widget_id=uuid4(),
                title="Test",
                config=pie_config,
                width=13,
            )
        # Test height must be >= 1
        with pytest.raises(ValidationError):
            ModelWidgetDefinition(
                widget_id=uuid4(),
                title="Test",
                config=pie_config,
                height=0,
            )

    def test_optional_description(self) -> None:
        """Test optional description field."""
        widget_no_desc = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test",
            config=_make_pie_chart_config(),
        )
        assert widget_no_desc.description is None

        widget_with_desc = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test",
            config=_make_pie_chart_config(),
            description="A test widget",
        )
        assert widget_with_desc.description == "A test widget"

    def test_optional_data_source(self) -> None:
        """Test optional data_source field."""
        widget_no_source = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test",
            config=_make_pie_chart_config(),
        )
        assert widget_no_source.data_source is None

        widget_with_source = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Test",
            config=_make_pie_chart_config(),
            data_source="metrics-api",
        )
        assert widget_with_source.data_source == "metrics-api"

    def test_full_roundtrip_with_all_fields(self) -> None:
        """Test roundtrip with all optional fields populated."""
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Full Widget",
            config=ModelWidgetConfigMetricCard(metric_key="latency", label="P99"),
            row=2,
            col=3,
            width=4,
            height=2,
            description="Latency metric widget",
            data_source="prometheus",
            extra_config={"refresh": "30s"},
        )
        data = widget.model_dump()
        restored = ModelWidgetDefinition.model_validate(data)
        assert restored == widget
        assert restored.description == "Latency metric widget"
        assert restored.data_source == "prometheus"
        assert restored.extra_config == {"refresh": "30s"}

    def test_config_kind_discriminator_missing_raises(self) -> None:
        """Test that missing config_kind raises ValidationError."""
        data = {
            "widget_id": "12345678-1234-5678-1234-567812345678",
            "title": "Test",
            "config": {
                "chart_type": "bar",  # Missing config_kind
            },
        }
        with pytest.raises(ValidationError):
            ModelWidgetDefinition.model_validate(data)

    def test_invalid_config_kind_raises(self) -> None:
        """Test that invalid config_kind raises ValidationError."""
        data = {
            "widget_id": "12345678-1234-5678-1234-567812345678",
            "title": "Test",
            "config": {
                "config_kind": "invalid_type",
            },
        }
        with pytest.raises(ValidationError):
            ModelWidgetDefinition.model_validate(data)

    def test_uuid_from_string(self) -> None:
        """Test that UUID can be created from valid string."""
        uuid_str = "abcdef12-3456-7890-abcd-ef1234567890"
        widget = ModelWidgetDefinition(
            widget_id=UUID(uuid_str),
            title="Test",
            config=_make_pie_chart_config(),
        )
        assert str(widget.widget_id) == uuid_str

    def test_chart_validation_line_requires_series(self) -> None:
        """Test that line chart type requires at least one series."""
        with pytest.raises(ValidationError, match="requires at least one series"):
            ModelWidgetConfigChart(chart_type="line", series=())

    def test_chart_validation_bar_requires_series(self) -> None:
        """Test that bar chart type requires at least one series."""
        with pytest.raises(ValidationError, match="requires at least one series"):
            ModelWidgetConfigChart(chart_type="bar", series=())

    def test_chart_validation_area_requires_series(self) -> None:
        """Test that area chart type requires at least one series."""
        with pytest.raises(ValidationError, match="requires at least one series"):
            ModelWidgetConfigChart(chart_type="area", series=())

    def test_chart_validation_scatter_requires_series(self) -> None:
        """Test that scatter chart type requires at least one series."""
        with pytest.raises(ValidationError, match="requires at least one series"):
            ModelWidgetConfigChart(chart_type="scatter", series=())

    def test_chart_validation_pie_allows_empty_series(self) -> None:
        """Test that pie chart type allows empty series."""
        config = ModelWidgetConfigChart(chart_type="pie", series=())
        assert config.chart_type == "pie"
        assert config.series == ()

    def test_chart_validation_line_with_series_succeeds(self) -> None:
        """Test that line chart with series is valid."""
        series = (ModelChartSeriesConfig(name="Test", data_key="value"),)
        config = ModelWidgetConfigChart(chart_type="line", series=series)
        assert config.chart_type == "line"
        assert len(config.series) == 1

    def test_metric_card_validation_show_trend_requires_trend_key(self) -> None:
        """Test that show_trend=True requires trend_key to be set."""
        with pytest.raises(ValidationError, match="trend_key must be set"):
            ModelWidgetConfigMetricCard(
                metric_key="cpu_usage",
                label="CPU",
                show_trend=True,
                trend_key=None,
            )

    def test_metric_card_validation_no_trend_allows_empty_key(self) -> None:
        """Test that show_trend=False allows empty trend_key."""
        config = ModelWidgetConfigMetricCard(
            metric_key="cpu_usage",
            label="CPU",
            show_trend=False,
            trend_key=None,
        )
        assert config.show_trend is False
        assert config.trend_key is None

    def test_metric_card_validation_show_trend_with_key_succeeds(self) -> None:
        """Test that show_trend=True with trend_key is valid."""
        config = ModelWidgetConfigMetricCard(
            metric_key="cpu_usage",
            label="CPU",
            show_trend=True,
            trend_key="cpu_trend",
        )
        assert config.show_trend is True
        assert config.trend_key == "cpu_trend"
