# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for dashboard module public import surface."""

import pytest

from omnibase_core.models import dashboard

# All public names that should be exported
EXPECTED_EXPORTS: tuple[str, ...] = (
    "ModelDashboardConfig",
    "ModelDashboardLayoutConfig",
    "ModelWidgetConfig",
    "ModelWidgetDefinition",
    "ModelCapabilityView",
    "ModelNodeView",
    "ModelChartAxisConfig",
    "ModelChartSeriesConfig",
    "ModelWidgetConfigChart",
    "ModelTableColumnConfig",
    "ModelWidgetConfigTable",
    "ModelMetricThreshold",
    "ModelWidgetConfigMetricCard",
    "ModelStatusItemConfig",
    "ModelWidgetConfigStatusGrid",
    "ModelEventFilter",
    "ModelWidgetConfigEventFeed",
)


@pytest.mark.unit
class TestDashboardImports:
    """Tests for dashboard module import surface."""

    def test_all_is_immutable(self) -> None:
        """Test that __all__ is a tuple (immutable)."""
        assert isinstance(dashboard.__all__, tuple)

    @pytest.mark.parametrize("name", EXPECTED_EXPORTS)
    def test_public_export_exists(self, name: str) -> None:
        """Test that expected names are exported."""
        assert hasattr(dashboard, name), f"{name} not exported from dashboard module"
        assert name in dashboard.__all__, f"{name} not in __all__"

    def test_no_unexpected_exports(self) -> None:
        """Test that __all__ contains only expected exports."""
        assert set(dashboard.__all__) == set(EXPECTED_EXPORTS)
