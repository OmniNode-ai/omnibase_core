"""Dashboard models and widget configuration types.

This module provides Pydantic models for configuring dashboards and their
widgets in the ONEX platform. The dashboard system follows a hierarchical
structure:

- **Dashboard Config**: Top-level container with layout and theme settings
- **Widget Definition**: Individual widget with position, size, and config
- **Widget Config**: Type-specific configuration (chart, table, metric, etc.)
- **View Models**: Lightweight projections for UI rendering (NodeView, CapabilityView)

Widget Types:
    - **Chart**: Line, bar, area, pie, and scatter visualizations
    - **Table**: Paginated, sortable tabular data display
    - **Metric Card**: Single KPI display with trend and thresholds
    - **Status Grid**: Multi-item health/status indicators
    - **Event Feed**: Real-time event stream with filtering

Example:
    Create a simple dashboard with a metric card widget::

        from uuid import uuid4
        from omnibase_core.models.dashboard import (
            ModelDashboardConfig,
            ModelWidgetDefinition,
            ModelWidgetConfigMetricCard,
        )

        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="System Health",
            widgets=(
                ModelWidgetDefinition(
                    widget_id=uuid4(),
                    title="CPU Usage",
                    config=ModelWidgetConfigMetricCard(
                        metric_key="cpu_percent",
                        label="CPU",
                        unit="%",
                        format="number",
                    ),
                ),
            ),
        )

See Also:
    - :class:`~omnibase_core.enums.EnumWidgetType`: Widget type enumeration
    - :class:`~omnibase_core.enums.EnumDashboardTheme`: Theme options
    - :class:`~omnibase_core.enums.EnumDashboardStatus`: Lifecycle states
"""

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
