# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dashboard models and widget configurations for OMN-1284."""

from omnibase_core.models.dashboard.model_capability_view import ModelCapabilityView
from omnibase_core.models.dashboard.model_chart_axis_config import ModelChartAxisConfig
from omnibase_core.models.dashboard.model_chart_series_config import (
    ModelChartSeriesConfig,
)
from omnibase_core.models.dashboard.model_dashboard_config import ModelDashboardConfig
from omnibase_core.models.dashboard.model_dashboard_layout_config import (
    ModelDashboardLayoutConfig,
)
from omnibase_core.models.dashboard.model_event_filter import ModelEventFilter
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold
from omnibase_core.models.dashboard.model_node_view import ModelNodeView
from omnibase_core.models.dashboard.model_status_item_config import (
    ModelStatusItemConfig,
)
from omnibase_core.models.dashboard.model_table_column_config import (
    ModelTableColumnConfig,
)
from omnibase_core.models.dashboard.model_widget_config_chart import (
    ModelWidgetConfigChart,
)
from omnibase_core.models.dashboard.model_widget_config_event_feed import (
    ModelWidgetConfigEventFeed,
)
from omnibase_core.models.dashboard.model_widget_config_metric_card import (
    ModelWidgetConfigMetricCard,
)
from omnibase_core.models.dashboard.model_widget_config_status_grid import (
    ModelWidgetConfigStatusGrid,
)
from omnibase_core.models.dashboard.model_widget_config_table import (
    ModelWidgetConfigTable,
)
from omnibase_core.models.dashboard.model_widget_definition import (
    ModelWidgetConfig,
    ModelWidgetDefinition,
)

__all__: tuple[str, ...] = (
    # Dashboard Configuration
    "ModelDashboardConfig",
    "ModelDashboardLayoutConfig",
    # Widget Definition
    "ModelWidgetConfig",
    "ModelWidgetDefinition",
    # View Models
    "ModelCapabilityView",
    "ModelNodeView",
    # Chart Widget
    "ModelChartAxisConfig",
    "ModelChartSeriesConfig",
    "ModelWidgetConfigChart",
    # Table Widget
    "ModelTableColumnConfig",
    "ModelWidgetConfigTable",
    # Metric Card Widget
    "ModelMetricThreshold",
    "ModelWidgetConfigMetricCard",
    # Status Grid Widget
    "ModelStatusItemConfig",
    "ModelWidgetConfigStatusGrid",
    # Event Feed Widget
    "ModelEventFilter",
    "ModelWidgetConfigEventFeed",
)
