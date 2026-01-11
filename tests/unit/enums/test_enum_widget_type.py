# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for EnumWidgetType."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_widget_type import EnumWidgetType


@pytest.mark.unit
class TestEnumWidgetType:
    """Tests for EnumWidgetType enum."""

    def test_all_values_exist(self) -> None:
        """Test that all expected widget types exist."""
        assert EnumWidgetType.CHART == "chart"
        assert EnumWidgetType.TABLE == "table"
        assert EnumWidgetType.METRIC_CARD == "metric_card"
        assert EnumWidgetType.STATUS_GRID == "status_grid"
        assert EnumWidgetType.EVENT_FEED == "event_feed"

    def test_value_count(self) -> None:
        """Test expected number of widget types."""
        assert len(EnumWidgetType) == 5

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumWidgetType, str)
        assert issubclass(EnumWidgetType, Enum)

    def test_is_data_bound_property(self) -> None:
        """Test is_data_bound property."""
        assert EnumWidgetType.CHART.is_data_bound is True
        assert EnumWidgetType.TABLE.is_data_bound is True
        assert EnumWidgetType.EVENT_FEED.is_data_bound is True
        assert EnumWidgetType.METRIC_CARD.is_data_bound is False
        assert EnumWidgetType.STATUS_GRID.is_data_bound is False

    def test_is_aggregation_property(self) -> None:
        """Test is_aggregation property."""
        assert EnumWidgetType.METRIC_CARD.is_aggregation is True
        assert EnumWidgetType.STATUS_GRID.is_aggregation is True
        assert EnumWidgetType.CHART.is_aggregation is False
        assert EnumWidgetType.TABLE.is_aggregation is False
        assert EnumWidgetType.EVENT_FEED.is_aggregation is False

    def test_data_bound_and_aggregation_mutually_exclusive(self) -> None:
        """Test that data_bound and aggregation are mutually exclusive."""
        for widget_type in EnumWidgetType:
            # A widget should not be both data_bound and aggregation
            assert not (widget_type.is_data_bound and widget_type.is_aggregation)

    def test_string_conversion(self) -> None:
        """Test string conversion and str enum behavior."""
        # str(enum) returns full representation
        assert "CHART" in str(EnumWidgetType.CHART)
        # But as str subclass, equality with string works
        assert EnumWidgetType.CHART == "chart"
        assert EnumWidgetType.TABLE == "table"
        assert EnumWidgetType.METRIC_CARD == "metric_card"
        assert EnumWidgetType.STATUS_GRID == "status_grid"
        assert EnumWidgetType.EVENT_FEED == "event_feed"

    def test_value_attribute(self) -> None:
        """Test value attribute."""
        assert EnumWidgetType.CHART.value == "chart"
        assert EnumWidgetType.TABLE.value == "table"
        assert EnumWidgetType.METRIC_CARD.value == "metric_card"
        assert EnumWidgetType.STATUS_GRID.value == "status_grid"
        assert EnumWidgetType.EVENT_FEED.value == "event_feed"

    def test_from_string(self) -> None:
        """Test enum creation from string value."""
        assert EnumWidgetType("chart") == EnumWidgetType.CHART
        assert EnumWidgetType("table") == EnumWidgetType.TABLE
        assert EnumWidgetType("metric_card") == EnumWidgetType.METRIC_CARD
        assert EnumWidgetType("status_grid") == EnumWidgetType.STATUS_GRID
        assert EnumWidgetType("event_feed") == EnumWidgetType.EVENT_FEED

    def test_invalid_value_raises(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumWidgetType("invalid")

        with pytest.raises(ValueError):
            EnumWidgetType("")

    def test_enum_iteration(self) -> None:
        """Test that we can iterate over enum values."""
        values = list(EnumWidgetType)
        assert len(values) == 5
        assert EnumWidgetType.CHART in values
        assert EnumWidgetType.TABLE in values
        assert EnumWidgetType.METRIC_CARD in values
        assert EnumWidgetType.STATUS_GRID in values
        assert EnumWidgetType.EVENT_FEED in values

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        # Enum member membership
        assert EnumWidgetType.CHART in EnumWidgetType
        # Value membership - check if string is a valid enum value
        valid_values = {m.value for m in EnumWidgetType}
        assert "chart" in valid_values
        assert "invalid_widget" not in valid_values

    def test_enum_comparison(self) -> None:
        """Test enum comparison."""
        assert EnumWidgetType.CHART == EnumWidgetType.CHART
        assert EnumWidgetType.CHART != EnumWidgetType.TABLE
        assert EnumWidgetType.CHART == "chart"

    def test_all_expected_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {"chart", "table", "metric_card", "status_grid", "event_feed"}
        actual_values = {member.value for member in EnumWidgetType}
        assert actual_values == expected_values

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumWidgetType.__doc__ is not None
        assert "widget" in EnumWidgetType.__doc__.lower()

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip."""
        import json

        for widget_type in EnumWidgetType:
            # Serialize to JSON
            json_str = json.dumps(widget_type.value)
            # Deserialize from JSON
            deserialized = json.loads(json_str)
            # Reconstruct enum
            reconstructed = EnumWidgetType(deserialized)
            assert reconstructed == widget_type
