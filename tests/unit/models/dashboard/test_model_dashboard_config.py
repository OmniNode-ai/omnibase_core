# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelDashboardConfig."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumDashboardStatus, EnumDashboardTheme
from omnibase_core.models.dashboard import (
    ModelChartSeriesConfig,
    ModelDashboardConfig,
    ModelDashboardLayoutConfig,
    ModelWidgetConfigChart,
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


class TestModelDashboardLayoutConfig:
    """Tests for ModelDashboardLayoutConfig."""

    def test_default_values(self) -> None:
        """Test default layout values."""
        layout = ModelDashboardLayoutConfig()
        assert layout.columns == 12
        assert layout.row_height == 100
        assert layout.gap == 16
        assert layout.responsive is True

    def test_custom_values(self) -> None:
        """Test custom layout values."""
        layout = ModelDashboardLayoutConfig(
            columns=24, row_height=150, gap=8, responsive=False
        )
        assert layout.columns == 24
        assert layout.row_height == 150
        assert layout.gap == 8
        assert layout.responsive is False

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        layout = ModelDashboardLayoutConfig(columns=16)
        data = layout.model_dump()
        restored = ModelDashboardLayoutConfig.model_validate(data)
        assert restored == layout


class TestModelDashboardConfig:
    """Tests for ModelDashboardConfig."""

    def test_minimal_creation(self) -> None:
        """Test creating dashboard with minimal fields."""
        dashboard_id = uuid4()
        dashboard = ModelDashboardConfig(
            dashboard_id=dashboard_id,
            name="Test Dashboard",
        )
        assert dashboard.dashboard_id == dashboard_id
        assert dashboard.name == "Test Dashboard"
        assert dashboard.widgets == ()
        assert dashboard.refresh_interval_seconds is None

    def test_default_values(self) -> None:
        """Test default values."""
        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="Test",
        )
        assert dashboard.theme == "system"
        assert dashboard.initial_status == EnumDashboardStatus.INITIALIZING
        assert dashboard.description is None
        assert dashboard.layout.columns == 12

    def test_with_widgets(self) -> None:
        """Test creating dashboard with widgets."""
        widget_id = uuid4()
        widget = ModelWidgetDefinition(
            widget_id=widget_id,
            title="Chart",
            config=_make_line_chart_config(),
        )
        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="Test",
            widgets=(widget,),
        )
        assert len(dashboard.widgets) == 1
        assert dashboard.widgets[0].widget_id == widget_id

    def test_refresh_interval(self) -> None:
        """Test refresh interval configuration."""
        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="Test",
            refresh_interval_seconds=30,
        )
        assert dashboard.refresh_interval_seconds == 30

    def test_refresh_interval_none_is_disabled(self) -> None:
        """Test that None means refresh is disabled."""
        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="Test",
            refresh_interval_seconds=None,
        )
        assert dashboard.refresh_interval_seconds is None

    def test_roundtrip_serialization(self) -> None:
        """Test full roundtrip serialization."""
        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Chart",
            config=_make_line_chart_config(),
        )
        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="Production Dashboard",
            description="Main monitoring dashboard",
            widgets=(widget,),
            refresh_interval_seconds=60,
            theme=EnumDashboardTheme.DARK,
        )
        data = dashboard.model_dump()
        restored = ModelDashboardConfig.model_validate(data)
        assert restored == dashboard
        assert restored.widgets[0].config.config_kind == "chart"

    def test_frozen_model(self) -> None:
        """Test that model is frozen."""
        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="Test",
        )
        # Pydantic frozen models raise ValidationError on mutation in v2,
        # but may raise TypeError in some edge cases or implementations
        with pytest.raises((ValidationError, TypeError)):
            dashboard.name = "New Name"  # type: ignore[misc]

    def test_invalid_dashboard_id_raises(self) -> None:
        """Test that invalid dashboard_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelDashboardConfig(
                dashboard_id="not-a-uuid",
                name="Test",
            )

    def test_invalid_refresh_interval_raises(self) -> None:
        """Test that invalid refresh interval raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelDashboardConfig(
                dashboard_id=uuid4(),
                name="Test",
                refresh_interval_seconds=0,  # Must be >= 1
            )

    def test_theme_values(self) -> None:
        """Test theme enum values."""
        for theme in EnumDashboardTheme:
            dashboard = ModelDashboardConfig(
                dashboard_id=uuid4(),
                name="Test",
                theme=theme,
            )
            assert dashboard.theme == theme

    def test_status_enum_values(self) -> None:
        """Test initial_status enum values."""
        for status in EnumDashboardStatus:
            dashboard = ModelDashboardConfig(
                dashboard_id=uuid4(),
                name="Test",
                initial_status=status,
            )
            assert dashboard.initial_status == status

    def test_uuid_from_string(self) -> None:
        """Test that UUID can be created from valid string."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        dashboard = ModelDashboardConfig(
            dashboard_id=UUID(uuid_str),
            name="Test",
        )
        assert str(dashboard.dashboard_id) == uuid_str

    def test_widget_uuid_from_string(self) -> None:
        """Test that widget UUID can be created from valid string."""
        uuid_str = "abcdef12-3456-7890-abcd-ef1234567890"
        widget = ModelWidgetDefinition(
            widget_id=UUID(uuid_str),
            title="Chart",
            config=_make_pie_chart_config(),
        )
        assert str(widget.widget_id) == uuid_str
