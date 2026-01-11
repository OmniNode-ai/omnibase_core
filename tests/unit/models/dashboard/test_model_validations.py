# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for dashboard model validations (PR #363 feedback)."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard import (
    ModelChartAxisConfig,
    ModelChartSeriesConfig,
    ModelStatusItemConfig,
    ModelTableColumnConfig,
    ModelWidgetConfigChart,
    ModelWidgetConfigEventFeed,
    ModelWidgetConfigMetricCard,
    ModelWidgetConfigStatusGrid,
    ModelWidgetConfigTable,
)


@pytest.mark.unit
class TestModelChartAxisConfigValidation:
    """Tests for ModelChartAxisConfig min_value < max_value validation."""

    def test_min_less_than_max_valid(self) -> None:
        """Test that min_value < max_value is valid."""
        config = ModelChartAxisConfig(min_value=0.0, max_value=100.0)
        assert config.min_value == 0.0
        assert config.max_value == 100.0

    def test_min_none_max_set_valid(self) -> None:
        """Test that None min_value with set max_value is valid."""
        config = ModelChartAxisConfig(min_value=None, max_value=100.0)
        assert config.min_value is None
        assert config.max_value == 100.0

    def test_min_set_max_none_valid(self) -> None:
        """Test that set min_value with None max_value is valid."""
        config = ModelChartAxisConfig(min_value=0.0, max_value=None)
        assert config.min_value == 0.0
        assert config.max_value is None

    def test_both_none_valid(self) -> None:
        """Test that both None is valid."""
        config = ModelChartAxisConfig(min_value=None, max_value=None)
        assert config.min_value is None
        assert config.max_value is None

    def test_negative_values_valid(self) -> None:
        """Test that negative values work when min < max."""
        config = ModelChartAxisConfig(min_value=-100.0, max_value=-50.0)
        assert config.min_value == -100.0
        assert config.max_value == -50.0

    def test_min_greater_than_max_invalid(self) -> None:
        """Test that min_value > max_value raises ValidationError."""
        with pytest.raises(ValidationError, match="must be less than max_value"):
            ModelChartAxisConfig(min_value=100.0, max_value=50.0)

    def test_min_equal_to_max_invalid(self) -> None:
        """Test that min_value == max_value raises ValidationError."""
        with pytest.raises(ValidationError, match="must be less than max_value"):
            ModelChartAxisConfig(min_value=50.0, max_value=50.0)

    def test_zero_range_invalid(self) -> None:
        """Test that zero range (min == max at 0) raises ValidationError."""
        with pytest.raises(ValidationError, match="must be less than max_value"):
            ModelChartAxisConfig(min_value=0.0, max_value=0.0)


@pytest.mark.unit
class TestModelChartSeriesConfigColorValidation:
    """Tests for ModelChartSeriesConfig hex color validation."""

    def test_none_color_valid(self) -> None:
        """Test that None color is valid."""
        config = ModelChartSeriesConfig(name="Test", data_key="value", color=None)
        assert config.color is None

    def test_valid_hex_6_digits(self) -> None:
        """Test valid 6-digit hex color."""
        config = ModelChartSeriesConfig(name="Test", data_key="value", color="#FF0000")
        assert config.color == "#FF0000"

    def test_valid_hex_3_digits(self) -> None:
        """Test valid 3-digit hex color."""
        config = ModelChartSeriesConfig(name="Test", data_key="value", color="#F00")
        assert config.color == "#F00"

    def test_valid_hex_8_digits_rgba(self) -> None:
        """Test valid 8-digit hex color (RRGGBBAA)."""
        config = ModelChartSeriesConfig(
            name="Test", data_key="value", color="#FF0000FF"
        )
        assert config.color == "#FF0000FF"

    def test_valid_hex_4_digits_rgba(self) -> None:
        """Test valid 4-digit hex color (RGBA)."""
        config = ModelChartSeriesConfig(name="Test", data_key="value", color="#F00F")
        assert config.color == "#F00F"

    def test_lowercase_hex_valid(self) -> None:
        """Test lowercase hex is valid."""
        config = ModelChartSeriesConfig(name="Test", data_key="value", color="#abcdef")
        assert config.color == "#abcdef"

    def test_mixed_case_hex_valid(self) -> None:
        """Test mixed case hex is valid."""
        config = ModelChartSeriesConfig(name="Test", data_key="value", color="#AbCdEf")
        assert config.color == "#AbCdEf"

    def test_invalid_hex_missing_hash(self) -> None:
        """Test that hex without # is invalid."""
        with pytest.raises(ValidationError, match="Invalid hex color format"):
            ModelChartSeriesConfig(name="Test", data_key="value", color="FF0000")

    def test_invalid_hex_wrong_length(self) -> None:
        """Test that hex with wrong length is invalid."""
        with pytest.raises(ValidationError, match="Invalid hex color format"):
            ModelChartSeriesConfig(
                name="Test", data_key="value", color="#FF000"
            )  # 5 digits

    def test_invalid_hex_non_hex_chars(self) -> None:
        """Test that non-hex characters are invalid."""
        with pytest.raises(ValidationError, match="Invalid hex color format"):
            ModelChartSeriesConfig(name="Test", data_key="value", color="#GGGGGG")

    def test_invalid_hex_empty(self) -> None:
        """Test that empty color is invalid."""
        with pytest.raises(ValidationError, match="Invalid hex color format"):
            ModelChartSeriesConfig(name="Test", data_key="value", color="")


@pytest.mark.unit
class TestModelWidgetConfigStatusGridColorValidation:
    """Tests for ModelWidgetConfigStatusGrid status_colors validation."""

    def test_default_colors_valid(self) -> None:
        """Test that default status_colors are valid."""
        config = ModelWidgetConfigStatusGrid()
        assert "healthy" in config.status_colors
        assert config.status_colors["healthy"] == "#22c55e"

    def test_custom_valid_colors(self) -> None:
        """Test custom valid hex colors."""
        custom_colors = {
            "ok": "#00FF00",
            "warn": "#FFFF00",
            "fail": "#FF0000",
        }
        config = ModelWidgetConfigStatusGrid(status_colors=custom_colors)
        assert config.status_colors == custom_colors

    def test_custom_valid_colors_3_digit(self) -> None:
        """Test custom valid 3-digit hex colors."""
        custom_colors = {
            "ok": "#0F0",
            "warn": "#FF0",
            "fail": "#F00",
        }
        config = ModelWidgetConfigStatusGrid(status_colors=custom_colors)
        assert config.status_colors == custom_colors

    def test_custom_valid_colors_with_alpha(self) -> None:
        """Test custom valid hex colors with alpha."""
        custom_colors = {
            "ok": "#00FF00FF",
            "warn": "#FFFF00AA",
        }
        config = ModelWidgetConfigStatusGrid(status_colors=custom_colors)
        assert config.status_colors == custom_colors

    def test_invalid_color_missing_hash(self) -> None:
        """Test that color without # is invalid."""
        with pytest.raises(ValidationError, match="Invalid hex color format"):
            ModelWidgetConfigStatusGrid(
                status_colors={"ok": "00FF00"}  # Missing #
            )

    def test_invalid_color_wrong_length(self) -> None:
        """Test that color with wrong length is invalid."""
        with pytest.raises(ValidationError, match="Invalid hex color format"):
            ModelWidgetConfigStatusGrid(
                status_colors={"ok": "#FF000"}  # 5 digits - invalid length
            )

    def test_invalid_color_non_hex_chars(self) -> None:
        """Test that non-hex characters are invalid."""
        with pytest.raises(ValidationError, match="Invalid hex color format"):
            ModelWidgetConfigStatusGrid(
                status_colors={"ok": "#GGGGGG"}  # Invalid chars
            )

    def test_error_message_includes_status_key(self) -> None:
        """Test that error message includes the status key."""
        with pytest.raises(ValidationError, match="status 'fail'"):
            ModelWidgetConfigStatusGrid(
                status_colors={"ok": "#00FF00", "fail": "invalid"}
            )

    def test_empty_dict_valid(self) -> None:
        """Test that empty status_colors dict is valid."""
        config = ModelWidgetConfigStatusGrid(status_colors={})
        assert config.status_colors == {}


@pytest.mark.unit
class TestModelTableColumnConfigWidthValidation:
    """Tests for ModelTableColumnConfig width minimum constraint."""

    def test_none_width_valid(self) -> None:
        """Test that None width is valid."""
        config = ModelTableColumnConfig(key="id", header="ID", width=None)
        assert config.width is None

    def test_width_1_valid(self) -> None:
        """Test that width=1 is valid (minimum)."""
        config = ModelTableColumnConfig(key="id", header="ID", width=1)
        assert config.width == 1

    def test_width_100_valid(self) -> None:
        """Test that width=100 is valid."""
        config = ModelTableColumnConfig(key="id", header="ID", width=100)
        assert config.width == 100

    def test_width_large_value_valid(self) -> None:
        """Test that large width values are valid."""
        config = ModelTableColumnConfig(key="id", header="ID", width=1000)
        assert config.width == 1000

    def test_width_0_invalid(self) -> None:
        """Test that width=0 is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTableColumnConfig(key="id", header="ID", width=0)
        # Verify it's a constraint violation on the width field
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("width",) for e in errors)

    def test_width_negative_invalid(self) -> None:
        """Test that negative width is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTableColumnConfig(key="id", header="ID", width=-1)
        # Verify it's a constraint violation on the width field
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("width",) for e in errors)

    def test_width_negative_large_invalid(self) -> None:
        """Test that large negative width is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTableColumnConfig(key="id", header="ID", width=-100)
        # Verify it's a constraint violation on the width field
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("width",) for e in errors)

    def test_default_width_is_none(self) -> None:
        """Test that default width is None."""
        config = ModelTableColumnConfig(key="id", header="ID")
        assert config.width is None


@pytest.mark.unit
class TestModelValidationsRoundtrip:
    """Tests for model serialization roundtrip with validations."""

    def test_chart_axis_config_roundtrip(self) -> None:
        """Test ModelChartAxisConfig roundtrip serialization."""
        config = ModelChartAxisConfig(
            label="X-Axis", min_value=0.0, max_value=100.0, show_grid=True
        )
        data = config.model_dump()
        restored = ModelChartAxisConfig.model_validate(data)
        assert restored == config

    def test_chart_series_config_roundtrip(self) -> None:
        """Test ModelChartSeriesConfig roundtrip serialization."""
        config = ModelChartSeriesConfig(
            name="Revenue", data_key="revenue", color="#4CAF50", series_type="bar"
        )
        data = config.model_dump()
        restored = ModelChartSeriesConfig.model_validate(data)
        assert restored == config

    def test_status_grid_config_roundtrip(self) -> None:
        """Test ModelWidgetConfigStatusGrid roundtrip serialization."""
        config = ModelWidgetConfigStatusGrid(
            columns=4,
            status_colors={"up": "#00FF00", "down": "#FF0000"},
        )
        data = config.model_dump()
        restored = ModelWidgetConfigStatusGrid.model_validate(data)
        assert restored == config

    def test_table_column_config_roundtrip(self) -> None:
        """Test ModelTableColumnConfig roundtrip serialization."""
        config = ModelTableColumnConfig(
            key="name", header="Name", width=200, sortable=True, align="left"
        )
        data = config.model_dump()
        restored = ModelTableColumnConfig.model_validate(data)
        assert restored == config


@pytest.mark.unit
class TestWidgetTypeConfigKindConsistency:
    """Tests for widget_type / config_kind consistency validation."""

    def test_chart_valid_defaults(self) -> None:
        """Test that chart config with default widget_type and config_kind is valid."""
        config = ModelWidgetConfigChart(
            chart_type="pie"  # pie doesn't require series
        )
        assert config.widget_type == EnumWidgetType.CHART
        assert config.config_kind == "chart"

    def test_chart_mismatched_widget_type_invalid(self) -> None:
        """Test that chart config with wrong widget_type raises ValidationError."""
        with pytest.raises(ValidationError, match="widget_type must be CHART"):
            ModelWidgetConfigChart(
                chart_type="pie",
                widget_type=EnumWidgetType.TABLE,
            )

    def test_table_valid_defaults(self) -> None:
        """Test that table config with default widget_type and config_kind is valid."""
        config = ModelWidgetConfigTable()
        assert config.widget_type == EnumWidgetType.TABLE
        assert config.config_kind == "table"

    def test_table_mismatched_widget_type_invalid(self) -> None:
        """Test that table config with wrong widget_type raises ValidationError."""
        with pytest.raises(ValidationError, match="widget_type must be TABLE"):
            ModelWidgetConfigTable(
                widget_type=EnumWidgetType.CHART,
            )

    def test_metric_card_valid_defaults(self) -> None:
        """Test that metric_card config with default widget_type and config_kind is valid."""
        config = ModelWidgetConfigMetricCard(
            metric_key="cpu",
            label="CPU Usage",
        )
        assert config.widget_type == EnumWidgetType.METRIC_CARD
        assert config.config_kind == "metric_card"

    def test_metric_card_mismatched_widget_type_invalid(self) -> None:
        """Test that metric_card config with wrong widget_type raises ValidationError."""
        with pytest.raises(ValidationError, match="widget_type must be METRIC_CARD"):
            ModelWidgetConfigMetricCard(
                metric_key="cpu",
                label="CPU Usage",
                widget_type=EnumWidgetType.CHART,
            )

    def test_status_grid_valid_defaults(self) -> None:
        """Test that status_grid config with default widget_type and config_kind is valid."""
        config = ModelWidgetConfigStatusGrid()
        assert config.widget_type == EnumWidgetType.STATUS_GRID
        assert config.config_kind == "status_grid"

    def test_status_grid_mismatched_widget_type_invalid(self) -> None:
        """Test that status_grid config with wrong widget_type raises ValidationError."""
        with pytest.raises(ValidationError, match="widget_type must be STATUS_GRID"):
            ModelWidgetConfigStatusGrid(
                widget_type=EnumWidgetType.TABLE,
            )

    def test_event_feed_valid_defaults(self) -> None:
        """Test that event_feed config with default widget_type and config_kind is valid."""
        config = ModelWidgetConfigEventFeed()
        assert config.widget_type == EnumWidgetType.EVENT_FEED
        assert config.config_kind == "event_feed"

    def test_event_feed_mismatched_widget_type_invalid(self) -> None:
        """Test that event_feed config with wrong widget_type raises ValidationError."""
        with pytest.raises(ValidationError, match="widget_type must be EVENT_FEED"):
            ModelWidgetConfigEventFeed(
                widget_type=EnumWidgetType.CHART,
            )


@pytest.mark.unit
class TestStringMinLengthConstraints:
    """Tests for min_length=1 constraints on required string fields."""

    def test_chart_series_name_empty_invalid(self) -> None:
        """Test that empty name in chart series raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChartSeriesConfig(name="", data_key="value")
        # Verify it's a string_too_short error on the name field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("name",) and e["type"] == "string_too_short" for e in errors
        )

    def test_chart_series_data_key_empty_invalid(self) -> None:
        """Test that empty data_key in chart series raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChartSeriesConfig(name="Test", data_key="")
        # Verify it's a string_too_short error on the data_key field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("data_key",) and e["type"] == "string_too_short"
            for e in errors
        )

    def test_chart_series_valid_fields(self) -> None:
        """Test that non-empty name and data_key are valid."""
        config = ModelChartSeriesConfig(name="X", data_key="y")
        assert config.name == "X"
        assert config.data_key == "y"

    def test_table_column_key_empty_invalid(self) -> None:
        """Test that empty key in table column raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTableColumnConfig(key="", header="Header")
        # Verify it's a string_too_short error on the key field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("key",) and e["type"] == "string_too_short" for e in errors
        )

    def test_table_column_header_empty_invalid(self) -> None:
        """Test that empty header in table column raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTableColumnConfig(key="id", header="")
        # Verify it's a string_too_short error on the header field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("header",) and e["type"] == "string_too_short" for e in errors
        )

    def test_table_column_valid_fields(self) -> None:
        """Test that non-empty key and header are valid."""
        config = ModelTableColumnConfig(key="a", header="b")
        assert config.key == "a"
        assert config.header == "b"

    def test_status_item_key_empty_invalid(self) -> None:
        """Test that empty key in status item raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelStatusItemConfig(key="", label="Label")
        # Verify it's a string_too_short error on the key field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("key",) and e["type"] == "string_too_short" for e in errors
        )

    def test_status_item_label_empty_invalid(self) -> None:
        """Test that empty label in status item raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelStatusItemConfig(key="api", label="")
        # Verify it's a string_too_short error on the label field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("label",) and e["type"] == "string_too_short" for e in errors
        )

    def test_status_item_valid_fields(self) -> None:
        """Test that non-empty key and label are valid."""
        config = ModelStatusItemConfig(key="a", label="b")
        assert config.key == "a"
        assert config.label == "b"

    def test_metric_card_metric_key_empty_invalid(self) -> None:
        """Test that empty metric_key in metric card raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWidgetConfigMetricCard(metric_key="", label="Label")
        # Verify it's a string_too_short error on the metric_key field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("metric_key",) and e["type"] == "string_too_short"
            for e in errors
        )

    def test_metric_card_label_empty_invalid(self) -> None:
        """Test that empty label in metric card raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWidgetConfigMetricCard(metric_key="cpu", label="")
        # Verify it's a string_too_short error on the label field
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("label",) and e["type"] == "string_too_short" for e in errors
        )

    def test_metric_card_valid_fields(self) -> None:
        """Test that non-empty metric_key and label are valid."""
        config = ModelWidgetConfigMetricCard(metric_key="a", label="b")
        assert config.metric_key == "a"
        assert config.label == "b"
